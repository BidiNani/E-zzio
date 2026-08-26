"""
E-ZZIO V7.28.6 — Archive Lineage Validator
Audite rétroactivement l'intégrité de la chaîne d'archives pour détecter
la moindre altération historique (tampering) dans les blocs scellés.
"""

import json
import hashlib
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent.parent
ARCHIVE_DIR = ROOT_DIR / "runtime" / "decisions" / "archive"


class ArchiveLineageValidator:
    @staticmethod
    def verify_archive_lineage() -> dict:
        if not ARCHIVE_DIR.exists():
            return {"valid": True, "archives_count": 0, "error": None}

        metas = sorted(ARCHIVE_DIR.glob("ledger_*.meta.json"))
        jsonls = sorted(ARCHIVE_DIR.glob("ledger_*.jsonl"))

        if len(metas) != len(jsonls):
            return {"valid": False, "error": "Incohérence structurelle : nombre de fichiers .jsonl et .meta.json discordants."}

        expected_prev_root = "0" * 64

        for idx, (meta_path, jsonl_path) in enumerate(zip(metas, jsonls)):
            try:
                meta = json.loads(meta_path.read_text(encoding="utf-8"))
                lines = jsonl_path.read_text(encoding="utf-8").strip().splitlines()
            except Exception as e:
                return {"valid": False, "compromised_archive": meta_path.name, "error": f"Erreur de lecture : {e}"}

            if not lines:
                return {"valid": False, "compromised_archive": meta_path.name, "error": "Archive vide."}

            # 1. Vérification du previous_archive_root_hash
            if meta.get("previous_archive_root_hash") != expected_prev_root:
                return {
                    "valid": False,
                    "compromised_archive": meta_path.name,
                    "error": f"RUPTURE DE LIGNÉE INTER-ARCHIVES : Le previous_root ne correspond pas dans {meta_path.name}",
                }

            # 2. Recalcul strict du content_hash (SHA-256 de toutes les lignes)
            hasher = hashlib.sha256()
            for line in lines:
                hasher.update(line.encode("utf-8"))
            recalculated_content_hash = hasher.hexdigest()

            if recalculated_content_hash != meta.get("content_hash"):
                return {
                    "valid": False,
                    "compromised_archive": meta_path.name,
                    "error": f"ALTÉRATION HISTORIQUE DÉTECTÉE : Le content_hash de l'archive {meta_path.name} a été modifié (falsification rétroactive).",
                }

            # 3. Recalcul et vérification de l'archive_root_hash
            first_rec = json.loads(lines[0])
            last_rec = json.loads(lines[-1])
            root_payload = f"{recalculated_content_hash}:{expected_prev_root}:{first_rec['sequence']}:{last_rec['sequence']}".encode(
                "utf-8"
            )
            recalculated_root_hash = hashlib.sha256(root_payload).hexdigest()

            if recalculated_root_hash != meta.get("archive_root_hash"):
                return {
                    "valid": False,
                    "compromised_archive": meta_path.name,
                    "error": f"ROOT HASH CORROMPU : L'archive_root_hash de {meta_path.name} ne correspond pas aux données.",
                }

            expected_prev_root = recalculated_root_hash

        return {"valid": True, "archives_verified": len(metas), "error": None}


archive_validator = ArchiveLineageValidator()
