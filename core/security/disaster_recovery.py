"""
E-ZZIO V7.28.7.1 — Disaster Recovery Engine
Permet de reconstruire l'état intègre du système et de certifier le dernier état connu
en cas de destruction totale ou d'effacement du ledger actif (router_decisions.jsonl).
"""

import json
from pathlib import Path
from core.security.archive_validator import archive_validator

ROOT_DIR = Path(__file__).resolve().parent.parent.parent
LEDGER_PATH = ROOT_DIR / "runtime" / "decisions" / "router_decisions.jsonl"
ARCHIVE_DIR = ROOT_DIR / "runtime" / "decisions" / "archive"
STATE_PATH = ROOT_DIR / "runtime" / "state" / "ledger_chain_state.json"


class DisasterRecoveryEngine:
    @staticmethod
    def reconstruct_state_from_archives() -> dict:
        """
        Reconstruit l'état de référence du système à partir des archives scellées
        si le ledger actif est détruit ou manquant.
        """
        # 1. Audit complet préalable des archives
        lineage_audit = archive_validator.verify_archive_lineage()
        if not lineage_audit.get("valid", False):
            return {"recovered": False, "error": f"Impossible de restaurer : Ligne d'archives compromise -> {lineage_audit.get('error')}"}

        metas = sorted(ARCHIVE_DIR.glob("ledger_*.meta.json"))
        jsonls = sorted(ARCHIVE_DIR.glob("ledger_*.jsonl"))

        if not metas or not jsonls:
            return {
                "recovered": True,
                "mode": "EMPTY_STATE",
                "last_sequence": 0,
                "last_hash": "0" * 64,
                "message": "Aucune archive trouvée. État initial vide.",
            }

        # 2. Extraction du dernier état de la dernière archive valide
        try:
            last_meta = json.loads(metas[-1].read_text(encoding="utf-8"))
            last_jsonl_lines = jsonls[-1].read_text(encoding="utf-8").strip().splitlines()
            last_record = json.loads(last_jsonl_lines[-1])

            recovered_sequence = last_record.get("sequence")
            recovered_hash = last_record.get("hash")
            recovered_root_hash = last_meta.get("archive_root_hash")

            # 3. Restauration de l'ancre d'état globale (ledger_chain_state.json)
            state_data = {
                "last_sequence": recovered_sequence,
                "last_hash": recovered_hash,
                "last_archive_root_hash": recovered_root_hash,
                "restored_from_disaster": True,
                "restored_at": last_meta.get("archived_at"),
            }
            STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
            STATE_PATH.write_text(json.dumps(state_data, indent=2), encoding="utf-8")

            # 4. Si le ledger actif est absent, recréation d'un ledger actif propre
            if not LEDGER_PATH.exists():
                LEDGER_PATH.parent.mkdir(parents=True, exist_ok=True)
                LEDGER_PATH.write_text("", encoding="utf-8")

            return {
                "recovered": True,
                "mode": "ARCHIVE_RESTORED",
                "last_sequence": recovered_sequence,
                "last_hash": recovered_hash,
                "root_hash": recovered_root_hash,
                "archives_processed": len(metas),
            }

        except Exception as e:
            return {"recovered": False, "error": f"Erreur lors du parsing des archives pour reconstruction : {e}"}


disaster_recovery = DisasterRecoveryEngine()
