import json
import hashlib
from pathlib import Path
from typing import Tuple


class HashChainedLedger:
    def __init__(self, ledger_file: Path):
        self.ledger_file = ledger_file
        self.ledger_file.parent.mkdir(parents=True, exist_ok=True)

    def get_last_hash_and_sequence(self) -> Tuple[str, int]:
        """Lit le dernier reçu de la chaîne pour récupérer son hash et son numéro de séquence."""
        if not self.ledger_file.exists():
            return "0" * 64, 0

        last_line = None
        count = 0
        with open(self.ledger_file, "r", encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    last_line = line.strip()
                    count += 1

        if not last_line:
            return "0" * 64, 0

        try:
            record = json.loads(last_line)
            # Calcul du SHA-256 du record complet comme hash de référence pour le suivant
            record_encoded = json.dumps(record, sort_keys=True).encode("utf-8")
            current_hash = hashlib.sha256(record_encoded).hexdigest()
            return current_hash, count
        except (json.JSONDecodeError, Exception):
            return "0" * 64, count

    def append_receipt(self, receipt_dict: dict) -> str:
        """Ajoute un reçu au ledger en le liant cryptographiquement au précédent."""
        prev_hash, seq_id = self.get_last_hash_and_sequence()

        receipt_dict["sequence_id"] = seq_id + 1
        receipt_dict["previous_receipt_hash"] = prev_hash

        # Sérialisation et écriture immuable
        line = json.dumps(receipt_dict, sort_keys=True, ensure_ascii=False)
        with open(self.ledger_file, "a", encoding="utf-8") as f:
            f.write(line + "\n")

        # Retourne le hash de ce nouveau reçu
        return hashlib.sha256(line.encode("utf-8")).hexdigest()

    def verify_integrity(self) -> Tuple[bool, str]:
        """Vérifie l'intégrité globale de la chaîne de hachage du ledger (Détection de falsification)."""
        if not self.ledger_file.exists():
            return True, "LEDGER_EMPTY"

        expected_prev_hash = "0" * 64
        lines = self.ledger_file.read_text(encoding="utf-8").splitlines()

        for idx, line in enumerate(lines):
            if not line.strip():
                continue
            try:
                record = json.loads(line)
            except json.JSONDecodeError:
                return False, f"CORRUPTED_JSON_AT_LINE_{idx + 1}"

            if record.get("previous_receipt_hash") != expected_prev_hash:
                return False, f"HASH_CHAIN_BROKEN_AT_SEQUENCE_{record.get('sequence_id')}"

            # Calcul du hash pour la ligne suivante
            expected_prev_hash = hashlib.sha256(line.strip().encode("utf-8")).hexdigest()

        return True, "LEDGER_INTEGRITY_VERIFIED"
