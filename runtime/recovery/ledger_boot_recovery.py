"""
E-ZZIO V7.28.4 — Ledger Boot Recovery (Forensic Hardened)
Réalise un snapshot forensic avant tout rollback de queue tronquée, 
et applique un contrôle rigoureux et dissocié entre intégrité SHA-256 et signature HMAC.
"""
import os
import json
import hashlib
import hmac
from pathlib import Path
from datetime import datetime, timezone
from dotenv import load_dotenv

ROOT_DIR = Path(__file__).resolve().parent.parent.parent
LEDGER_PATH = ROOT_DIR / "runtime" / "decisions" / "router_decisions.jsonl"
INCIDENT_PATH = ROOT_DIR / "runtime" / "security" / "incidents.jsonl"
FORENSIC_DIR = ROOT_DIR / "runtime" / "security" / "forensic"
ENV_PATH = ROOT_DIR / "secrets" / ".env"

load_dotenv(dotenv_path=ENV_PATH, override=True)

class LedgerBootRecovery:
    def __init__(self):
        self.secret_key = os.getenv("EZZIO_LEDGER_SECRET", "").encode("utf-8")

    def _log_incident(self, reason: str, details: dict):
        INCIDENT_PATH.parent.mkdir(parents=True, exist_ok=True)
        incident = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "event": "LEDGER_SECURITY_ALERT",
            "reason": reason,
            "details": details
        }
        with open(INCIDENT_PATH, "a", encoding="utf-8") as f:
            f.write(json.dumps(incident, ensure_ascii=False) + "\n")

    def _create_forensic_snapshot(self):
        """Sauvegarde une copie forensic exacte du ledger avant toute altération ou purge."""
        if not LEDGER_PATH.exists():
            return
        FORENSIC_DIR.mkdir(parents=True, exist_ok=True)
        timestamp_str = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S_%f")
        snapshot_path = FORENSIC_DIR / f"ledger_forensic_backup_{timestamp_str}.jsonl"
        try:
            snapshot_path.write_bytes(LEDGER_PATH.read_bytes())
        except Exception as e:
            self._log_incident("FORENSIC_BACKUP_FAILED", {"error": str(e)})

    def verify_and_heal_ledger(self) -> dict:
        if not LEDGER_PATH.exists():
            return {"status": "NO_LEDGER", "mode": "NORMAL"}

        try:
            raw_text = LEDGER_PATH.read_text(encoding="utf-8")
        except Exception as e:
            self._log_incident("READ_ERROR", {"error": str(e)})
            return {"status": "ERROR", "mode": "FAIL_CLOSED"}

        lines = raw_text.strip().splitlines()
        if not lines:
            return {"status": "EMPTY", "mode": "NORMAL"}

        valid_lines = []
        expected_sequence = 1
        expected_previous_hash = "0" * 64

        for idx, line in enumerate(lines):
            line_num = idx + 1
            if not line.strip():
                continue

            try:
                record = json.loads(line)
            except json.JSONDecodeError:
                if idx == len(lines) - 1:
                    # Capture forensic avant la purge de la queue tronquée
                    self._create_forensic_snapshot()
                    self._log_incident("RECOVERABLE_TAIL_TRUNCATION", {"broken_at_line": line_num})
                    break
                else:
                    self._log_incident("FATAL_JSON_CORRUPTION", {"broken_at_line": line_num})
                    return {"status": "FATAL_CORRUPTION", "mode": "FAIL_CLOSED"}

            seq = record.get("sequence")
            stored_hash = record.get("hash")
            stored_previous = record.get("previous_hash")
            stored_sig = record.get("signature")

            if seq != expected_sequence or stored_previous != expected_previous_hash:
                self._log_incident("FAIL_CLOSED_CHAIN_BREAK", {"line": line_num, "seq": seq})
                return {"status": "CHAIN_BROKEN", "mode": "FAIL_CLOSED"}

            # 1. Vérification du SHA-256 du payload (intégrité structurelle)
            temp_record = dict(record)
            temp_record.pop("hash", None)
            temp_record.pop("signature", None)
            raw_string = json.dumps(temp_record, sort_keys=True, ensure_ascii=False)
            calculated_hash = hashlib.sha256(raw_string.encode("utf-8")).hexdigest()

            if calculated_hash != stored_hash:
                self._log_incident("FAIL_CLOSED_HASH_TAMPER", {"line": line_num})
                return {"status": "TAMPER_DETECTED", "mode": "FAIL_CLOSED"}

            # 2. Vérification stricte du HMAC (authenticité cryptographique pure)
            if self.secret_key:
                if not stored_sig:
                    self._log_incident("FAIL_CLOSED_MISSING_SIGNATURE", {"line": line_num})
                    return {"status": "SIGNATURE_MISSING", "mode": "FAIL_CLOSED"}

                hmac_payload = f"{seq}:{stored_previous}:{stored_hash}".encode("utf-8")
                calculated_sig = hmac.new(self.secret_key, hmac_payload, hashlib.sha256).hexdigest()
                if not hmac.compare_digest(calculated_sig, stored_sig):
                    self._log_incident("FAIL_CLOSED_HMAC_FORGE", {"line": line_num})
                    return {"status": "HMAC_INVALID", "mode": "FAIL_CLOSED"}
            else:
                # Si aucun secret n'est configuré alors que le fichier possède des signatures signées -> Fail-Closed
                if stored_sig:
                    return {"status": "SECRET_MISSING_FOR_SIGNED_LEDGER", "mode": "FAIL_CLOSED"}

            valid_lines.append(line)
            expected_sequence += 1
            expected_previous_hash = stored_hash

        if len(valid_lines) < len(lines):
            cleaned_content = "\n".join(valid_lines) + ("\n" if valid_lines else "")
            temp_path = LEDGER_PATH.with_suffix(".recovery.tmp")
            try:
                with open(temp_path, "w", encoding="utf-8") as f:
                    f.write(cleaned_content)
                    f.flush()
                    os.fsync(f.fileno())
                os.replace(temp_path, LEDGER_PATH)
                print(f"[Boot Recovery] FORENSIC SNAPSHOT & TAIL ROLLBACK RÉUSSIS : Queue tronquée purgée. {len(valid_lines)} transactions sécurisées.")
            except Exception as e:
                self._log_incident("ATOMIC_SWAP_ERROR", {"error": str(e)})
                return {"status": "ERROR", "mode": "FAIL_CLOSED"}

        return {"status": "HEALTHY", "mode": "NORMAL"}

ledger_recovery = LedgerBootRecovery()
