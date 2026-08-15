"""
E-ZZIO V7.31 — Full Snapshot Engine
Capture l'ensemble des 9 artefacts fondamentaux d'identité sous contrôle secret strict.
"""
import os
import json
import shutil
import hashlib
import hmac
from pathlib import Path
from datetime import datetime, timezone
from dotenv import load_dotenv

ROOT_DIR = Path(__file__).resolve().parent.parent.parent
RUNTIME_IDENTITY_DIR = ROOT_DIR / "runtime" / "identity"
SNAPSHOTS_DIR = RUNTIME_IDENTITY_DIR / "snapshots"
CONFIG_DIR = ROOT_DIR / "config"
ENV_PATH = ROOT_DIR / "secrets" / ".env"

load_dotenv(dotenv_path=ENV_PATH, override=True)

class IdentitySnapshotEngine:
    def __init__(self):
        secret = os.getenv("EZZIO_LEDGER_SECRET")
        if not secret:
            raise ValueError("CRITICAL_SECURITY_ERROR: EZZIO_LEDGER_SECRET is required.")
        self.secret_key = secret.encode("utf-8")
        SNAPSHOTS_DIR.mkdir(parents=True, exist_ok=True)

    def _get_next_snapshot_index(self) -> int:
        existing = sorted(SNAPSHOTS_DIR.glob("snapshot_*"))
        if not existing:
            return 1
        last_name = existing[-1].name
        try:
            return int(last_name.split("_")[1]) + 1
        except Exception:
            return len(existing) + 1

    def create_snapshot(self) -> dict:
        idx = self._get_next_snapshot_index()
        snap_dir = SNAPSHOTS_DIR / f"snapshot_{idx:04d}"
        snap_dir.mkdir(parents=True, exist_ok=True)

        # Les 9 artefacts constituant l'identité intégrale
        files_to_backup = [
            (RUNTIME_IDENTITY_DIR / "identity.json", snap_dir / "identity.json"),
            (RUNTIME_IDENTITY_DIR / "identity_authority.json", snap_dir / "identity_authority.json"),
            (RUNTIME_IDENTITY_DIR / "identity_root.hash", snap_dir / "identity_root.hash"),
            (RUNTIME_IDENTITY_DIR / "identity_signature.sig", snap_dir / "identity_signature.sig"),
            (CONFIG_DIR / "constitution.json", snap_dir / "constitution.json"),
            (CONFIG_DIR / "persona.json", snap_dir / "persona.json"),
            (CONFIG_DIR / "lore.md", snap_dir / "lore.md"),
            (CONFIG_DIR / "skills_manifest.json", snap_dir / "skills_manifest.json"),
            (CONFIG_DIR / "memory_graph.json", snap_dir / "memory_graph.json")
        ]

        hashes = {}
        for src, dst in files_to_backup:
            if src.exists():
                shutil.copy2(src, dst)
                hashes[src.name] = hashlib.sha256(src.read_bytes()).hexdigest()

        hasher = hashlib.sha256()
        for k in sorted(hashes.keys()):
            hasher.update(hashes[k].encode("utf-8"))
        snapshot_root_hash = hasher.hexdigest()

        signature = hmac.new(self.secret_key, snapshot_root_hash.encode("utf-8"), hashlib.sha256).hexdigest()

        metadata = {
            "snapshot_index": idx,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "backed_up_count": len(hashes),
            "file_hashes": hashes,
            "snapshot_root_hash": snapshot_root_hash,
            "signature": signature
        }

        (snap_dir / "snapshot_meta.json").write_text(json.dumps(metadata, indent=2), encoding="utf-8")
        return metadata

identity_snapshot_engine = IdentitySnapshotEngine()
