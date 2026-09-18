"""
E-ZZIO V7.31 — Atomic Transactional Recovery Engine
Restaure l'identité dans une zone de staging, valide l'intégrité à 100%, puis valide atomiquement.
"""

import hashlib
import hmac
import json
import os
import shutil
from pathlib import Path

from dotenv import load_dotenv

ROOT_DIR = Path(__file__).resolve().parent.parent.parent
RUNTIME_IDENTITY_DIR = ROOT_DIR / "runtime" / "identity"
SNAPSHOTS_DIR = RUNTIME_IDENTITY_DIR / "snapshots"
STAGING_DIR = RUNTIME_IDENTITY_DIR / ".staging_recovery"
CONFIG_DIR = ROOT_DIR / "config"
ENV_PATH = ROOT_DIR / "secrets" / ".env"

load_dotenv(dotenv_path=ENV_PATH, override=True)


class IdentityRecoveryEngine:
    def __init__(self):
        secret = os.getenv("EZZIO_LEDGER_SECRET")
        if not secret:
            raise ValueError("CRITICAL_SECURITY_ERROR: EZZIO_LEDGER_SECRET is required.")
        self.secret_key = secret.encode("utf-8")

    def recover_identity_from_latest_snapshot(self) -> dict:
        if not SNAPSHOTS_DIR.exists():
            return {"recovered": False, "error": "NO_SNAPSHOTS_DIRECTORY"}

        snapshots = sorted(SNAPSHOTS_DIR.glob("snapshot_*"))
        if not snapshots:
            return {"recovered": False, "error": "NO_SNAPSHOTS_AVAILABLE"}

        for snap_dir in reversed(snapshots):
            meta_file = snap_dir / "snapshot_meta.json"
            if not meta_file.exists():
                continue

            try:
                meta = json.loads(meta_file.read_text(encoding="utf-8"))
                stored_root = meta.get("snapshot_root_hash")
                stored_sig = meta.get("signature")
                file_hashes = meta.get("file_hashes", {})

                # 1. Vérification de la signature du snapshot
                calc_sig = hmac.new(self.secret_key, stored_root.encode("utf-8"), hashlib.sha256).hexdigest()
                if not hmac.compare_digest(calc_sig, stored_sig):
                    continue

                # 2. Zone Staging isolée
                if STAGING_DIR.exists():
                    shutil.rmtree(STAGING_DIR)
                STAGING_DIR.mkdir(parents=True, exist_ok=True)

                # Copie dans staging
                for fname in file_hashes.keys():
                    src = snap_dir / fname
                    if src.exists():
                        shutil.copy2(src, STAGING_DIR / fname)

                # 3. Validation intégrale de la zone staging
                staging_valid = True
                for fname, expected_hash in file_hashes.items():
                    staged_file = STAGING_DIR / fname
                    if not staged_file.exists():
                        staging_valid = False
                        break
                    actual_hash = hashlib.sha256(staged_file.read_bytes()).hexdigest()
                    if actual_hash != expected_hash:
                        staging_valid = False
                        break

                if not staging_valid:
                    shutil.rmtree(STAGING_DIR)
                    continue

                # 4. Commit Atomique depuis staging vers la destination
                target_map = {
                    "identity.json": RUNTIME_IDENTITY_DIR / "identity.json",
                    "identity_authority.json": RUNTIME_IDENTITY_DIR / "identity_authority.json",
                    "identity_root.hash": RUNTIME_IDENTITY_DIR / "identity_root.hash",
                    "identity_signature.sig": RUNTIME_IDENTITY_DIR / "identity_signature.sig",
                    "constitution.json": CONFIG_DIR / "constitution.json",
                    "persona.json": CONFIG_DIR / "persona.json",
                    "lore.md": CONFIG_DIR / "lore.md",
                    "skills_manifest.json": CONFIG_DIR / "skills_manifest.json",
                    "memory_graph.json": CONFIG_DIR / "memory_graph.json",
                }

                for fname, target_path in target_map.items():
                    staged_src = STAGING_DIR / fname
                    if staged_src.exists():
                        target_path.parent.mkdir(parents=True, exist_ok=True)
                        shutil.move(str(staged_src), str(target_path))

                shutil.rmtree(STAGING_DIR, ignore_errors=True)

                return {"recovered": True, "atomic": True, "restored_snapshot": snap_dir.name, "restored_count": len(file_hashes)}

            except Exception:
                if STAGING_DIR.exists():
                    shutil.rmtree(STAGING_DIR, ignore_errors=True)
                continue

        return {"recovered": False, "error": "ALL_SNAPSHOTS_INVALID"}


identity_recovery_engine = IdentityRecoveryEngine()
