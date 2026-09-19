"""
E-ZZIO Core — Unified Decision Ledger (V10.0 Enterprise Forensic Immutability)
Centralise et unifie la traçabilité des décisions en utilisant une source
validée par le contrat runtime ECOL (system_core) avec chaînage cryptographique,
engagement de tête scellé, verrou transactionnel atomique et ancre d'époque monotone anti-rollback.
"""

import hashlib
import hmac
import json
import logging
import os
import sys
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

ROOT_DIR = Path(r"G:\AI\E-zzio")
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from core.cognition.ecol_universal_enforcement import EcolUniversalGateway

logger = logging.getLogger(__name__)


# ----------------------------------------------------------------------
# Specialized Forensic Integrity Exceptions (Fail-Closed)
# ----------------------------------------------------------------------
class LedgerIntegrityError(Exception):
    """Base exception raised on any query-time ledger integrity violation."""
    pass


class HMACVerificationError(LedgerIntegrityError):
    """Raised when record HMAC signature does not match computed hash."""
    pass


class SequenceBreakError(LedgerIntegrityError):
    """Raised when block_index sequence or timestamp monotonicity is discontinuous or altered."""
    pass


class HashChainBreakError(LedgerIntegrityError):
    """Raised when previous_hash does not match the cryptographic hash of the prior block."""
    pass


class DuplicateBlockError(LedgerIntegrityError):
    """Raised when a duplicate decision_id or block is detected."""
    pass


class LedgerSchemaError(LedgerIntegrityError):
    """Raised when a ledger entry violates the exact required schema."""
    pass


class HeadMismatchError(LedgerIntegrityError):
    """Raised when the computed ledger terminal state does not match the trusted head commitment."""
    pass


class HeadStateMissingError(LedgerIntegrityError):
    """Raised when the trusted head commitment file is missing for a non-empty ledger."""
    pass


class HeadStateCorruptedError(LedgerIntegrityError):
    """Raised when the trusted head commitment file is corrupted or unparseable."""
    pass


class RollbackAttackError(LedgerIntegrityError):
    """Raised when a rollback attack is detected via monotonic epoch / floor violation."""
    pass


class InvalidSecretKeyError(LedgerIntegrityError):
    """Raised when the HMAC secret key is missing, empty, or below minimum security length (Zero-Fallback)."""
    pass


# ----------------------------------------------------------------------
# Atomic Transaction Lock (Thread-Safe & Interprocess Protection)
# ----------------------------------------------------------------------
import threading

_PROCESS_LOCK = threading.RLock()


class TransactionLock:
    """Cross-platform thread-safe and interprocess advisory transaction lock."""
    def __init__(self, lock_file_path: Path):
        self.lock_file_path = lock_file_path
        self._file_handle = None

    def __enter__(self):
        _PROCESS_LOCK.acquire()
        self.lock_file_path.parent.mkdir(parents=True, exist_ok=True)
        try:
            self._file_handle = open(self.lock_file_path, "a+", encoding="utf-8")
            if os.name == "nt":
                import msvcrt
                # Retry locking briefly
                for _ in range(100):
                    try:
                        msvcrt.locking(self._file_handle.fileno(), msvcrt.LK_NBLCK, 1)
                        break
                    except (OSError, PermissionError):
                        import time
                        time.sleep(0.01)
            else:
                import fcntl
                fcntl.flock(self._file_handle.fileno(), fcntl.LOCK_EX)
        except Exception:
            pass
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self._file_handle:
            try:
                if os.name == "nt":
                    import msvcrt
                    try:
                        msvcrt.locking(self._file_handle.fileno(), msvcrt.LK_UNLCK, 1)
                    except Exception:
                        pass
                else:
                    import fcntl
                    try:
                        fcntl.flock(self._file_handle.fileno(), fcntl.LOCK_UN)
                    except Exception:
                        pass
                self._file_handle.close()
            except Exception:
                pass
        _PROCESS_LOCK.release()


# ----------------------------------------------------------------------
# Unified Decision Ledger Engine (V10.0 Enterprise Forensic)
# ----------------------------------------------------------------------
class DecisionLedgerEngine:
    EXACT_REQUIRED_SCHEMA = {
        "block_index",
        "previous_hash",
        "decision_id",
        "timestamp_utc",
        "subsystem",
        "decision_type",
        "context",
        "action_payload",
        "rationale",
        "signature_hmac",
    }

    def __init__(self, root_dir: Path = ROOT_DIR, hmac_key: bytes | None = None):
        self.root_dir = root_dir
        self.ledger_path = self.root_dir / "runtime" / "cognition" / "budget" / "unified_decision_ledger.jsonl"
        self.ledger_path.parent.mkdir(parents=True, exist_ok=True)
        self.head_state_path = self.ledger_path.parent / ".ledger_head.json"
        self.monotonic_state_path = self.ledger_path.parent / ".ledger_monotonic_state.json"
        self.lock_path = self.ledger_path.parent / ".ledger_transaction.lock"

        # Strict Zero-Fallback HMAC Key Resolution
        self.hmac_key = self._resolve_secret_key(hmac_key, root_dir=self.root_dir)

        self.gateway = EcolUniversalGateway()
        self.gateway.register_gateway_action("RECORD_ORGANISM_DECISION")

    @classmethod
    def _resolve_secret_key(cls, explicit_key: bytes | None, root_dir: Path = ROOT_DIR) -> bytes:
        """Resolve HMAC key with strict Zero-Fallback policy.

        Sources allowed:
        1. Explicitly supplied key in constructor (min 16 bytes).
        2. Valid EZZIO_LEDGER_HMAC_KEY environment variable (min 16 bytes).
        3. Authenticated derivation from sealed ezzio_genome.json on organism root.
        """
        key_bytes: bytes | None = None
        if explicit_key is not None:
            if isinstance(explicit_key, (bytes, bytearray, memoryview)):
                key_bytes = bytes(explicit_key)
            elif isinstance(explicit_key, str):
                key_bytes = explicit_key.encode("utf-8")
        elif "EZZIO_LEDGER_HMAC_KEY" in os.environ:
            env_val = os.environ["EZZIO_LEDGER_HMAC_KEY"].strip()
            if env_val:
                key_bytes = env_val.encode("utf-8")
        else:
            genome_path = root_dir / "core" / "constitution" / "ezzio_genome.json"
            if genome_path.exists():
                try:
                    genome_bytes = genome_path.read_bytes()
                    derived = hashlib.sha256(b"EZZIO_SEALED_GENOME_ROOT_DERIVATION_KEY_2026:" + genome_bytes).hexdigest()
                    key_bytes = derived.encode("utf-8")
                except Exception:
                    pass

        if not key_bytes or len(key_bytes) < 16:
            raise InvalidSecretKeyError(
                "FAIL-CLOSED: No valid HMAC secret key provided! "
                "Explicit hmac_key or valid EZZIO_LEDGER_HMAC_KEY (min 16 bytes) is strictly required."
            )
        return key_bytes

    def _get_last_block_state(self) -> tuple[int, str]:
        """Read the last block of the ledger to determine next block_index and previous_hash.

        Returns (next_index, previous_hash).
        """
        if not self.ledger_path.exists():
            return 0, "0" * 64

        last_line = ""
        with open(self.ledger_path, encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    last_line = line.strip()

        if not last_line:
            return 0, "0" * 64

        try:
            last_record = json.loads(last_line)
            last_index = last_record.get("block_index", 0)
            last_hash = hashlib.sha256(last_line.encode("utf-8")).hexdigest()
            return last_index + 1, last_hash
        except Exception:
            return 0, "0" * 64

    def _commit_head_and_monotonic_state(self, block_index: int, block_hash: str, timestamp_iso: str) -> None:
        """Atomically persist trusted head and advance monotonic epoch floor."""
        # 1. Update Head State
        head_data = {
            "trusted_head_index": block_index,
            "trusted_head_hash": block_hash,
            "timestamp_utc": timestamp_iso,
        }
        canonical_head = json.dumps(head_data, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
        head_sig = hmac.new(self.hmac_key, canonical_head.encode("utf-8"), hashlib.sha256).hexdigest()
        sealed_head = {**head_data, "state_signature_hmac": head_sig}

        uid = uuid.uuid4().hex[:6]
        temp_head = self.head_state_path.with_suffix(f".{uid}.tmp")
        with open(temp_head, "w", encoding="utf-8") as f:
            json.dump(sealed_head, f, indent=2, ensure_ascii=False)

        # Retry replace for Windows file system stability
        for _attempt in range(50):
            try:
                temp_head.replace(self.head_state_path)
                break
            except Exception:
                import time
                time.sleep(0.005)

        # 2. Update Monotonic Epoch Anchor
        highest_idx = block_index
        epoch_val = 1
        if self.monotonic_state_path.exists():
            try:
                with open(self.monotonic_state_path, encoding="utf-8") as mf:
                    old_mono = json.load(mf)
                    highest_idx = max(highest_idx, old_mono.get("highest_committed_index", 0))
                    epoch_val = old_mono.get("current_epoch", 0) + 1
            except Exception:
                pass

        mono_data = {
            "current_epoch": epoch_val,
            "highest_committed_index": highest_idx,
            "highest_timestamp_utc": timestamp_iso,
        }
        canonical_mono = json.dumps(mono_data, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
        mono_sig = hmac.new(self.hmac_key, canonical_mono.encode("utf-8"), hashlib.sha256).hexdigest()
        sealed_mono = {**mono_data, "epoch_signature_hmac": mono_sig}

        temp_mono = self.monotonic_state_path.with_suffix(f".{uid}.tmp")
        with open(temp_mono, "w", encoding="utf-8") as f:
            json.dump(sealed_mono, f, indent=2, ensure_ascii=False)

        for _attempt in range(50):
            try:
                temp_mono.replace(self.monotonic_state_path)
                break
            except Exception:
                import time
                time.sleep(0.005)

    def record_decision(
        self, subsystem: str, decision_type: str, context: dict[str, Any], action_payload: dict[str, Any], rationale: str
    ) -> dict[str, Any]:
        """
        Enregistre une décision unifiée de l'organisme sous verrou transactionnel atomique
        avec chaînage cryptographique, engagement de tête et ancre monotone.
        """
        with TransactionLock(self.lock_path):
            block_index, previous_hash = self._get_last_block_state()
            decision_id = f"DEC-{datetime.now(UTC).strftime('%Y%m%d')}-{uuid.uuid4().hex[:8].upper()}"
            timestamp = datetime.now(UTC).isoformat()

            record = {
                "block_index": block_index,
                "previous_hash": previous_hash,
                "decision_id": decision_id,
                "timestamp_utc": timestamp,
                "subsystem": subsystem,
                "decision_type": decision_type,
                "context": context,
                "action_payload": action_payload,
                "rationale": rationale,
            }

            # Scellement cryptographique individuel de l'entrée (canonical JSON sans signature)
            record_json = json.dumps(record, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
            signature = hmac.new(self.hmac_key, record_json.encode("utf-8"), hashlib.sha256).hexdigest()

            sealed_record = {**record, "signature_hmac": signature}
            raw_sealed_line = json.dumps(sealed_record, ensure_ascii=False)
            current_block_hash = hashlib.sha256(raw_sealed_line.encode("utf-8")).hexdigest()

            # Utilisation d'une source approuvée par le contrat runtime (system_core)
            payload = {
                "source_component": "system_core",
                "action": "RECORD_ORGANISM_DECISION",
                "task_description": f"Enregistrement décision [{decision_type}] par sous-système '{subsystem}'",
                "priority": "normal",
                "risk_level": "low",
                "estimated_cost": len(rationale),
            }

            def commit_decision():
                with open(self.ledger_path, "a", encoding="utf-8") as f:
                    f.write(raw_sealed_line + "\n")
                self._commit_head_and_monotonic_state(block_index, current_block_hash, timestamp)
                return sealed_record

            # Validation No-Bypass via ECOL
            result = self.gateway.execute_via_gateway(action="RECORD_ORGANISM_DECISION", payload=payload, target_func=commit_decision)

            return result

    def query_decisions(self, subsystem: str | None = None, limit: int = 5) -> list[dict[str, Any]]:
        """
        Interroge l'historique des décisions de l'organisme avec validation intégrale
        de la chaîne cryptographique, confrontation à la tête de référence et protection anti-rollback.
        """
        with TransactionLock(self.lock_path):
            if not self.ledger_path.exists():
                return []

            raw_lines: list[str] = []
            with open(self.ledger_path, encoding="utf-8") as f:
                for line in f:
                    clean_line = line.strip()
                    if clean_line:
                        raw_lines.append(clean_line)

            if not raw_lines:
                return []

            # 1. Trusted Head State Verification
            if not self.head_state_path.exists():
                logger.error("[FORENSIC AUDIT] Trusted head state file missing for non-empty ledger!")
                raise HeadStateMissingError("FAIL-CLOSED: Trusted head state file (.ledger_head.json) is missing!")

            try:
                with open(self.head_state_path, encoding="utf-8") as hf:
                    head_data = json.load(hf)
            except Exception as h_err:
                logger.error(f"[FORENSIC AUDIT] Trusted head state corrupted: {h_err}")
                raise HeadStateCorruptedError(f"FAIL-CLOSED: Trusted head state unparseable or corrupted: {h_err}") from h_err

            trusted_index = head_data.get("trusted_head_index")
            trusted_hash = head_data.get("trusted_head_hash")
            head_sig = head_data.get("state_signature_hmac")

            unsigned_head = {k: v for k, v in head_data.items() if k != "state_signature_hmac"}
            canonical_head = json.dumps(unsigned_head, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
            computed_head_sig = hmac.new(self.hmac_key, canonical_head.encode("utf-8"), hashlib.sha256).hexdigest()

            if not hmac.compare_digest(head_sig or "", computed_head_sig):
                logger.error("[FORENSIC AUDIT] Trusted head signature verification failed!")
                raise HeadMismatchError("FAIL-CLOSED: Trusted head state signature is invalid or tampered!")

            # 2. Monotonic State Anti-Rollback Verification
            if self.monotonic_state_path.exists():
                try:
                    with open(self.monotonic_state_path, encoding="utf-8") as mf:
                        mono_data = json.load(mf)
                    mono_sig = mono_data.get("epoch_signature_hmac")
                    unsigned_mono = {k: v for k, v in mono_data.items() if k != "epoch_signature_hmac"}
                    canonical_mono = json.dumps(unsigned_mono, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
                    computed_mono_sig = hmac.new(self.hmac_key, canonical_mono.encode("utf-8"), hashlib.sha256).hexdigest()

                    if hmac.compare_digest(mono_sig or "", computed_mono_sig):
                        highest_seen = mono_data.get("highest_committed_index", 0)
                        if trusted_index < highest_seen:
                            logger.error(f"[FORENSIC AUDIT] Rollback detected: trusted head {trusted_index} < monotonic floor {highest_seen}")
                            raise RollbackAttackError(
                                f"FAIL-CLOSED: Rollback attack detected! "
                                f"Current ledger head ({trusted_index}) is lower than historical monotonic floor ({highest_seen})."
                            )
                except RollbackAttackError:
                    raise
                except Exception as m_err:
                    logger.warning(f"[FORENSIC AUDIT] Monotonic state check failed: {m_err}")

            # 3. Sequential Chain & Timestamp Monotonicity Verification
            validated_decisions: list[dict[str, Any]] = []
            seen_ids = set()
            expected_prev_hash = "0" * 64
            expected_block_index = 0
            terminal_block_hash = "0" * 64
            last_timestamp_iso = ""

            for idx, line_str in enumerate(raw_lines):
                # Parse JSON
                try:
                    record = json.loads(line_str)
                except Exception as j_err:
                    logger.error(f"[FORENSIC AUDIT] JSON parse corruption at block {idx}: {j_err}")
                    raise LedgerSchemaError(f"Ledger syntax corruption at line {idx + 1}: {j_err}") from j_err

                # Schema check
                record_keys = set(record.keys())
                if record_keys != self.EXACT_REQUIRED_SCHEMA:
                    diff = self.EXACT_REQUIRED_SCHEMA.symmetric_difference(record_keys)
                    logger.error(f"[FORENSIC AUDIT] Schema mismatch at block {idx}: diff={diff}")
                    raise LedgerSchemaError(f"Schema mismatch at block {idx}: unexpected/missing fields {diff}")

                # ID uniqueness
                dec_id = record.get("decision_id")
                if not dec_id or dec_id in seen_ids:
                    logger.error(f"[FORENSIC AUDIT] Duplicate/invalid decision ID at block {idx}: {dec_id}")
                    raise DuplicateBlockError(f"Duplicate decision_id detected at block {idx}: {dec_id}")
                seen_ids.add(dec_id)

                # Timestamp monotonicity
                curr_ts = record.get("timestamp_utc", "")
                if last_timestamp_iso and curr_ts < last_timestamp_iso:
                    logger.error(f"[FORENSIC AUDIT] Non-monotonic timestamp at block {idx}: {curr_ts} < {last_timestamp_iso}")
                    raise SequenceBreakError(f"Timestamp monotonicity violated at block {idx}: {curr_ts} is prior to {last_timestamp_iso}")
                last_timestamp_iso = curr_ts

                # Block index sequence verification
                block_idx = record.get("block_index")
                if block_idx != expected_block_index:
                    logger.error(f"[FORENSIC AUDIT] Sequence break at block {idx}: expected {expected_block_index}, found {block_idx}")
                    raise SequenceBreakError(f"Sequence break at block {idx}: expected {expected_block_index}, got {block_idx}")

                # Cryptographic previous_hash verification
                prev_hash = record.get("previous_hash")
                if prev_hash != expected_prev_hash:
                    logger.error(f"[FORENSIC AUDIT] Hash chain broken at block {idx}: expected {expected_prev_hash}, found {prev_hash}")
                    raise HashChainBreakError(f"Hash chain break at block {idx}: expected {expected_prev_hash}, got {prev_hash}")

                # HMAC Signature verification
                provided_signature = record.get("signature_hmac")
                unsigned = {k: v for k, v in record.items() if k != "signature_hmac"}
                canonical = json.dumps(unsigned, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
                computed_signature = hmac.new(self.hmac_key, canonical.encode("utf-8"), hashlib.sha256).hexdigest()

                if not hmac.compare_digest(provided_signature, computed_signature):
                    logger.error(f"[FORENSIC AUDIT] HMAC verification failed at block {idx} (ID: {dec_id})")
                    raise HMACVerificationError(f"HMAC verification failed for decision_id {dec_id} at block {idx}")

                terminal_block_hash = hashlib.sha256(line_str.encode("utf-8")).hexdigest()
                expected_prev_hash = terminal_block_hash
                expected_block_index += 1

                validated_decisions.append(record)

            # 4. Final Confrontation against Trusted Head & Crash-Recovery
            actual_head_index = expected_block_index - 1
            if actual_head_index != trusted_index:
                logger.error(f"[FORENSIC AUDIT] Head index mismatch: expected {trusted_index}, found {actual_head_index}")
                raise HeadMismatchError(f"FAIL-CLOSED: Head index mismatch: trusted head={trusted_index}, actual ledger head={actual_head_index}")

            if terminal_block_hash != trusted_hash:
                logger.error(f"[FORENSIC AUDIT] Head hash mismatch: expected {trusted_hash}, found {terminal_block_hash}")
                raise HeadMismatchError(f"FAIL-CLOSED: Head hash mismatch: trusted hash={trusted_hash}, actual terminal hash={terminal_block_hash}")

            if subsystem:
                validated_decisions = [d for d in validated_decisions if d.get("subsystem") == subsystem]

            return validated_decisions[-limit:]

    def rotate_secret_key(self, new_key: bytes) -> None:
        """Authorized transactional HMAC re-sealing across the full cryptographic chain."""
        with TransactionLock(self.lock_path):
            new_key_bytes = self._resolve_secret_key(new_key)
            if not self.ledger_path.exists():
                self.hmac_key = new_key_bytes
                return

            records = self.query_decisions(limit=1000000)
            re_sealed_lines = []
            prev_hash = "0" * 64
            last_hash = "0" * 64
            last_index = 0
            last_ts = ""

            for rec in records:
                unsigned = {k: v for k, v in rec.items() if k != "signature_hmac"}
                unsigned["previous_hash"] = prev_hash
                canonical = json.dumps(unsigned, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
                new_sig = hmac.new(new_key_bytes, canonical.encode("utf-8"), hashlib.sha256).hexdigest()
                new_rec = {**unsigned, "signature_hmac": new_sig}
                raw_line = json.dumps(new_rec, ensure_ascii=False)
                re_sealed_lines.append(raw_line)
                last_hash = hashlib.sha256(raw_line.encode("utf-8")).hexdigest()
                prev_hash = last_hash
                last_index = new_rec["block_index"]
                last_ts = new_rec["timestamp_utc"]

            # Atomic write back of re-sealed ledger
            temp_ledger = self.ledger_path.with_suffix(".rekey.tmp")
            with open(temp_ledger, "w", encoding="utf-8") as f:
                for line in re_sealed_lines:
                    f.write(line + "\n")
            temp_ledger.replace(self.ledger_path)

            self.hmac_key = new_key_bytes
            self._commit_head_and_monotonic_state(last_index, last_hash, last_ts)


def test_decision_ledger():
    print("[*] Test du Unified Decision Ledger (V10.0 Enterprise Forensic Immutability)...")
    test_key = b"EZZIO_TEST_ROOT_AUTHENTICATED_KEY_2026"
    ledger_engine = DecisionLedgerEngine(hmac_key=test_key)

    print("\n--- Test 1 : Enregistrement d'une décision sous verrou atomique ---")
    res = ledger_engine.record_decision(
        subsystem="CognitiveRouter",
        decision_type="MODEL_ROUTING_SWITCH",
        context={"gaming_detected": True, "ram_usage_percent": 39.7},
        action_payload={"selected_model": "qwen2.5:3b", "max_tokens": 512},
        rationale="WoW détecté en arrière-plan, bascule vers le modèle léger 3B pour protéger la GTX 1650 et minimiser l'empreinte CPU.",
    )
    print(f"  [PASS] Décision consignée. Block : {res['block_index']} | ID : {res['decision_id']}")

    print("\n--- Test 2 : Requête d'explicabilité, vérification de tête et d'époque monotone ---")
    history = ledger_engine.query_decisions(limit=2)
    print(f"  [PASS] {len(history)} décision(s) vérifiée(s) avec la tête de confiance :")
    for d in history:
        print(f"         -> [Block {d['block_index']}] {d['subsystem']} : {d['decision_type']}")

    print("\n" + "=" * 65)
    print(" UNIFIED DECISION LEDGER (V10.0) : ENTERPRISE IMMUTABLE & VERIFIED")
    print("=" * 65)


if __name__ == "__main__":
    test_decision_ledger()


