"""
E-ZZIO Core — Human Override Ledger (V8.9.4.2)
Consigne, protège et applique les directives permanentes du mentor (BidiNani),
garantissant qu'aucune décision autonome ne puisse contourner les règles humaines.
"""

import argparse
import hashlib
import hmac
import json
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

ROOT_DIR = Path(r"G:\AI\E-zzio")
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))


class HumanOverrideLedger:
    def __init__(self, root_dir: Path = ROOT_DIR):
        self.root_dir = root_dir
        self.ledger_path = self.root_dir / "runtime" / "cognition" / "budget" / "human_override_ledger.jsonl"
        self.ledger_path.parent.mkdir(parents=True, exist_ok=True)
        self._ensure_default_overrides()

    def _ensure_default_overrides(self):
        """Injecte les règles immuables du mentor si le ledger est vide."""
        if not self.ledger_path.exists() or self.ledger_path.stat().st_size == 0:
            default_rule = {
                "rule_id": "HW-001",
                "directive": "GTX1650_RESERVED_FOR_GAMING",
                "source": "BidiNani",
                "priority": "IMMUTABLE",
                "reason": "Priorité absolue au jeu World of Warcraft, interdiction d'utiliser le GPU pour l'IA.",
                "created_utc": datetime.now(UTC).isoformat(),
                "permanent": True,
            }
            self.register_override(
                rule_id=default_rule["rule_id"],
                directive=default_rule["directive"],
                reason=default_rule["reason"],
                priority=default_rule["priority"],
            )

    def register_override(self, rule_id: str, directive: str, reason: str, priority: str = "IMMUTABLE") -> dict[str, Any]:
        """Enregistre une directive humaine dans le registre avec scellement HMAC."""
        timestamp = datetime.now(UTC).isoformat()
        record = {
            "rule_id": rule_id,
            "directive": directive,
            "source": "BidiNani",
            "priority": priority,
            "reason": reason,
            "created_utc": timestamp,
            "permanent": True,
        }

        record_json = json.dumps(record, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
        sig = hmac.new(b"EZZIO_OVERRIDE_KEY_2026", record_json.encode("utf-8"), hashlib.sha256).hexdigest()
        sealed_record = {**record, "signature_hmac": sig}

        with open(self.ledger_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(sealed_record, ensure_ascii=False) + "\n")

        return sealed_record

    def get_all_overrides(self) -> list[dict[str, Any]]:
        """Lit et retourne l'ensemble des règles humaines enregistrées."""
        if not self.ledger_path.exists():
            return []

        overrides = []
        with open(self.ledger_path, encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    overrides.append(json.loads(line))
        return overrides


def main():
    parser = argparse.ArgumentParser(description="E-ZZIO Human Override Ledger (V8.9.4.2)")
    parser.add_argument("--list", action="store_true", help="Affiche les directives humaines enregistrées")
    parser.parse_args()

    ledger = HumanOverrideLedger()
    overrides = ledger.get_all_overrides()

    print("\n" + "=" * 70)
    print(" E-ZZIO HUMAN OVERRIDE LEDGER (V8.9.4.2)")
    print("=" * 70)
    print(f" Nombre de directives actives : {len(overrides)}")
    print("-" * 70)
    for o in overrides:
        print(f" 🛡️  [{o['rule_id']}] {o['directive']}")
        print(f"     Source   : {o['source']} (Priorité : {o['priority']})")
        print(f"     Raison   : {o['reason']}")
        print(f"     Date UTC : {o['created_utc']}")
        print("-" * 70)
    print("=" * 70 + "\n")


if __name__ == "__main__":
    main()
