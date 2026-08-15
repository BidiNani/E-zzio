"""
E-ZZIO V7.28.5.1 — Ledger Archive Engine (With Cryptographic Anchor)
Gère la rotation et injecte une transaction d'ancrage (ARCHIVE_ANCHOR) 
pour lier mathématiquement le nouveau ledger actif aux archives scellées.
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
ARCHIVE_DIR = ROOT_DIR / "runtime" / "decisions" / "archive"
STATE_PATH = ROOT_DIR / "runtime" / "state" / "ledger_chain_state.json"
ENV_PATH = ROOT_DIR / "secrets" / ".env"

load_dotenv(dotenv_path=ENV_PATH, override=True)

class LedgerArchiveEngine:
    def __init__(self, rotation_threshold: int = 5000):
        self.rotation_threshold = rotation_threshold
        self.secret_key = os.getenv("EZZIO_LEDGER_SECRET", "").encode("utf-8")

    def _get_last_archive_root_hash(self) -> str:
        if not ARCHIVE_DIR.exists():
            return "0" * 64
        metas = sorted(ARCHIVE_DIR.glob("ledger_*.meta.json"))
        if not metas:
            return "0" * 64
        try:
            last_meta = json.loads(metas[-1].read_text(encoding="utf-8"))
            return last_meta.get("archive_root_hash", "0" * 64)
        except Exception:
            return "0" * 64

    def check_and_rotate(self) -> bool:
        """Vérifie si le ledger actif dépasse le seuil et exécute la rotation sécurisée."""
        if not LEDGER_PATH.exists():
            return False

        try:
            lines = LEDGER_PATH.read_text(encoding="utf-8").strip().splitlines()
            if len(lines) < self.rotation_threshold:
                return False

            ARCHIVE_DIR.mkdir(parents=True, exist_ok=True)
            
            existing_archives = list(ARCHIVE_DIR.glob("ledger_*.jsonl"))
            archive_index = len(existing_archives) + 1
            archive_name_base = f"ledger_{archive_index:06d}"

            archive_file_path = ARCHIVE_DIR / f"{archive_name_base}.jsonl"
            meta_file_path = ARCHIVE_DIR / f"{archive_name_base}.meta.json"

            # 1. Écriture de l'archive brute
            archive_file_path.write_text("\n".join(lines) + "\n", encoding="utf-8")

            first_record = json.loads(lines[0])
            last_record = json.loads(lines[-1])
            
            hasher = hashlib.sha256()
            for line in lines:
                hasher.update(line.encode("utf-8"))
            content_sha256 = hasher.hexdigest()

            prev_root = self._get_last_archive_root_hash()
            
            root_payload = f"{content_sha256}:{prev_root}:{first_record['sequence']}:{last_record['sequence']}".encode("utf-8")
            archive_root_hash = hashlib.sha256(root_payload).hexdigest()

            metadata = {
                "archive_index": archive_index,
                "first_sequence": first_record.get("sequence"),
                "last_sequence": last_record.get("sequence"),
                "record_count": len(lines),
                "content_hash": content_sha256,
                "previous_archive_root_hash": prev_root,
                "archive_root_hash": archive_root_hash,
                "archived_at": datetime.now(timezone.utc).isoformat()
            }
            meta_file_path.write_text(json.dumps(metadata, indent=2, ensure_ascii=False), encoding="utf-8")

            # 2. Continuité Cryptographique : Génération d'une transaction d'ancrage (ARCHIVE_ANCHOR)
            last_seq = last_record.get("sequence", 0)
            last_hash = last_record.get("hash", "0" * 64)
            anchor_seq = last_seq + 1

            anchor_payload = {
                "sequence": anchor_seq,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "request_id": f"system-anchor-{archive_index}",
                "intent": "ARCHIVE_ANCHOR",
                "candidates": [],
                "selected": "system-kernel",
                "transaction_state": "ARCHIVED_AND_ANCHORED",
                "execution_details": {
                    "archived_file": archive_file_path.name,
                    "archive_root_hash": archive_root_hash
                },
                "previous_hash": last_hash
            }

            # Calcul SHA-256 et HMAC de l'ancre
            temp_payload = dict(anchor_payload)
            raw_string = json.dumps(temp_payload, sort_keys=True, ensure_ascii=False)
            anchor_hash = hashlib.sha256(raw_string.encode("utf-8")).hexdigest()
            anchor_payload["hash"] = anchor_hash

            if self.secret_key:
                hmac_payload = f"{anchor_seq}:{last_hash}:{anchor_hash}".encode("utf-8")
                anchor_signature = hmac.new(self.secret_key, hmac_payload, hashlib.sha256).hexdigest()
                anchor_payload["signature"] = anchor_signature

            anchor_line = json.dumps(anchor_payload, ensure_ascii=False) + "\n"

            # 3. Réinitialisation propre du ledger actif avec uniquement l'ancre de transition
            LEDGER_PATH.write_text(anchor_line, encoding="utf-8")

            # Mise à jour de l'ancre d'état globale
            self._update_anchor_state(anchor_seq, anchor_hash, archive_root_hash)

            print(f"[Archive Engine] ROTATION ET ANCRAGE RÉUSSIS : {len(lines)} txs archivées. Nouvelle séquence initialisée à {anchor_seq}.")
            return True

        except Exception as e:
            print(f"[!] Erreur critique lors de la rotation de l'archive : {e}")
            return False

    def _update_anchor_state(self, seq: int, last_hash: str, root_hash: str):
        STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
        state = {
            "last_sequence": seq,
            "last_hash": last_hash,
            "last_archive_root_hash": root_hash,
            "updated_at": datetime.now(timezone.utc).isoformat()
        }
        STATE_PATH.write_text(json.dumps(state, indent=2), encoding="utf-8")

ledger_archiver = LedgerArchiveEngine(rotation_threshold=5000)
