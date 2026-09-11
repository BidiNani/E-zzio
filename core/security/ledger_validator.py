"""
E-ZZIO V7.29.1 — Ledger Validator (Identity Seal Verification)
Vérifie l'intégrité de la chaîne et la validité des sceaux d'identité embarqués.
"""

import os
import json
import hashlib
import hmac
from pathlib import Path
from dotenv import load_dotenv

ROOT_DIR = Path(__file__).resolve().parent.parent.parent
LEDGER_PATH = ROOT_DIR / "runtime" / "decisions" / "router_decisions.jsonl"
ENV_PATH = ROOT_DIR / "secrets" / ".env"

load_dotenv(dotenv_path=ENV_PATH, override=True)


class LedgerValidator:
    def __init__(self):
        self.secret_key = os.getenv("EZZIO_LEDGER_SECRET", "").encode("utf-8")

    def verify_ledger_chain(self) -> dict:
        if not LEDGER_PATH.exists():
            return {"valid": True, "total_records": 0, "error": "Ledger absent"}

        try:
            raw_text = LEDGER_PATH.read_text(encoding="utf-8")
        except Exception as e:
            return {"valid": False, "error": f"Erreur de lecture : {e}"}

        lines = raw_text.strip().splitlines()
        if not lines:
            return {"valid": True, "total_records": 0, "error": None}

        expected_sequence = 1
        expected_previous_hash = "0" * 64

        for idx, line in enumerate(lines):
            line_num = idx + 1
            try:
                record = json.loads(line)
            except json.JSONDecodeError:
                return {"valid": False, "broken_at_line": line_num, "error": "JSON malformé"}

            seq = record.get("sequence")
            stored_hash = record.get("hash")
            stored_previous = record.get("previous_hash")
            stored_sig = record.get("signature")
            identity_seal = record.get("identity_seal")

            if seq != expected_sequence:
                return {"valid": False, "broken_at_line": line_num, "error": f"SEQUENCE GAP à la ligne {line_num}"}

            if stored_previous != expected_previous_hash:
                return {"valid": False, "broken_at_line": line_num, "error": f"CHAIN INVALID à la ligne {line_num}"}

            # Vérification de la présence du sceau d'identité V7.29.1
            if not identity_seal:
                return {"valid": False, "broken_at_line": line_num, "error": f"IDENTITY SEAL MISSING à la ligne {line_num}"}

            temp_record = dict(record)
            temp_record.pop("hash", None)
            temp_record.pop("signature", None)
            raw_string = json.dumps(temp_record, sort_keys=True, ensure_ascii=False)
            calculated_hash = hashlib.sha256(raw_string.encode("utf-8")).hexdigest()

            if calculated_hash != stored_hash:
                return {"valid": False, "broken_at_line": line_num, "error": f"HASH INVALID à la ligne {line_num}"}

            if self.secret_key and stored_sig:
                hmac_payload = f"{seq}:{stored_previous}:{stored_hash}".encode("utf-8")
                calculated_sig = hmac.new(self.secret_key, hmac_payload, hashlib.sha256).hexdigest()
                if not hmac.compare_digest(calculated_sig, stored_sig):
                    return {"valid": False, "broken_at_line": line_num, "error": f"HMAC INVALID à la ligne {line_num}"}

            expected_sequence += 1
            expected_previous_hash = stored_hash

        return {"valid": True, "total_records": len(lines), "error": None}


ledger_validator = LedgerValidator()
