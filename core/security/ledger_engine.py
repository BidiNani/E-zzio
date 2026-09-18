"""
E-ZZIO V7.29.1 — Ledger Engine avec Runtime Identity Enforcement
Assure l'injection et la vérification obligatoire du sceau d'identité pour chaque transaction.
"""

import hashlib
import hmac
import json
import os
from datetime import UTC, datetime
from pathlib import Path

from dotenv import load_dotenv

from core.identity.identity_context import ImmutableIdentityContext
from core.security.archive_engine import LedgerArchiveEngine
from core.security.file_lock import ProcessFileLock

ROOT_DIR = Path(__file__).resolve().parent.parent.parent
LEDGER_PATH = ROOT_DIR / "runtime" / "decisions" / "router_decisions.jsonl"
ARCHIVE_DIR = ROOT_DIR / "runtime" / "decisions" / "archive"
LOCK_PATH = ROOT_DIR / "runtime" / "decisions" / "ledger.lock"
ENV_PATH = ROOT_DIR / "secrets" / ".env"

load_dotenv(dotenv_path=ENV_PATH, override=True)


class LedgerEngine:
    def __init__(self, archive_threshold: int = 5000):
        self.secret_key = os.getenv("EZZIO_LEDGER_SECRET", "").encode("utf-8")
        self.archiver = LedgerArchiveEngine(rotation_threshold=archive_threshold)

        # Capture de l'ancre d'identité initiale au boot
        try:
            initial_ctx = ImmutableIdentityContext()
            self.boot_identity_root = initial_ctx.identity_root_hash
        except Exception:
            self.boot_identity_root = None

        if not self.secret_key or not self.boot_identity_root:
            self.system_mode = "FAIL_CLOSED"
        else:
            self.system_mode = "NORMAL"

    def _get_last_sequence_and_hash(self) -> tuple:
        if LEDGER_PATH.exists():
            try:
                lines = LEDGER_PATH.read_text(encoding="utf-8").strip().splitlines()
                if lines:
                    for line in reversed(lines):
                        if line.strip():
                            entry = json.loads(line)
                            return entry.get("sequence", 0), entry.get("hash", "0" * 64)
            except Exception:
                pass
        return 0, "0" * 64

    def commit_transaction(
        self, intent: str, request_id: str, candidates: list, selected: str, state: str, execution_details: dict = None
    ) -> bool:
        # Pre-flight check d'identité : vérification qu'aucune dérive n'a eu lieu depuis le boot
        try:
            current_ctx = ImmutableIdentityContext()
            if current_ctx.identity_root_hash != self.boot_identity_root:
                self.system_mode = "FAIL_CLOSED"
                return False
        except Exception:
            self.system_mode = "FAIL_CLOSED"
            return False

        if self.system_mode == "FAIL_CLOSED" or not self.secret_key:
            return False

        try:
            with ProcessFileLock(LOCK_PATH, timeout=30.0):
                LEDGER_PATH.parent.mkdir(parents=True, exist_ok=True)
                last_seq, last_hash = self._get_last_sequence_and_hash()
                new_seq = last_seq + 1

                payload = {
                    "sequence": new_seq,
                    "timestamp": datetime.now(UTC).isoformat(),
                    "request_id": request_id,
                    "intent": intent,
                    "candidates": candidates,
                    "selected": selected,
                    "transaction_state": state,
                    "execution_details": execution_details or {},
                    "previous_hash": last_hash,
                    "identity_root_hash": current_ctx.identity_root_hash,
                    "identity_seal": current_ctx.signature,
                }

                temp_payload = dict(payload)
                raw_string = json.dumps(temp_payload, sort_keys=True, ensure_ascii=False)
                current_hash = hashlib.sha256(raw_string.encode("utf-8")).hexdigest()
                payload["hash"] = current_hash

                hmac_payload = f"{new_seq}:{last_hash}:{current_hash}".encode()
                signature = hmac.new(self.secret_key, hmac_payload, hashlib.sha256).hexdigest()
                payload["signature"] = signature

                line_data = json.dumps(payload, ensure_ascii=False) + "\n"
                with open(LEDGER_PATH, "a", encoding="utf-8") as f:
                    f.write(line_data)
                    f.flush()
                    os.fsync(f.fileno())

                self.archiver.check_and_rotate()
                return True
        except Exception as e:
            print(f"[!] Erreur critique lors du commit transactionnel : {e}")
            return False


ledger_engine = LedgerEngine(archive_threshold=5000)
