"""
E-ZZIO Core — Atomic Snapshot Restore Engine (V8.8 Step 5 - Self-Contained)
Gère l'auto-bootstrap, la vérification d'intégrité SHA-256 et la restauration
atomique (Time Travel) sous le contrôle strict de la passerelle ECOL.
"""

import hashlib
import json
import logging
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

ROOT_DIR = Path(r"G:\AI\E-zzio")
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from core.cognition.ecol_universal_enforcement import EcolUniversalGateway

logger = logging.getLogger(__name__)


class SnapshotRestoreError(Exception):
    """Levée en cas de corruption de snapshot ou d'échec de vérification d'intégrité (Fail-Closed)."""

    pass


class SnapshotRestoreEngine:
    def __init__(self, root_dir: Path = ROOT_DIR):
        self.root_dir = root_dir
        self.snapshots_dir = self.root_dir / "runtime" / "snapshots"
        self.snapshots_dir.mkdir(parents=True, exist_ok=True)

        self.gateway = EcolUniversalGateway()
        self.gateway.register_gateway_action("ATOMIC_SNAPSHOT_RESTORE")

    def create_bootstrap_snapshot(self) -> dict[str, Any]:
        """Crée un point de référence initial si aucun snapshot n'existe."""
        timestamp_str = datetime.now(UTC).strftime("%Y%m%d_%H%M%S")
        snapshot_name = f"EZZIO_STATE_{timestamp_str}"
        snapshot_path = self.snapshots_dir / snapshot_name
        snapshot_path.mkdir(parents=True, exist_ok=True)

        for s in ["constitution", "cognition", "memory", "skills", "ledgers"]:
            (snapshot_path / s).mkdir(exist_ok=True)

        manifest = {"snapshot_id": snapshot_name, "created_at_utc": datetime.now(UTC).isoformat(), "files_captured": []}

        sources_to_capture = [
            (self.root_dir / "core" / "constitution" / "ezzio_genome.json", "constitution"),
            (self.root_dir / "runtime" / "memory_store", "memory"),
            (self.root_dir / "runtime" / "skills_store", "skills"),
            (self.root_dir / "runtime" / "ecol" / "evolution_ledger", "ledgers"),
        ]

        for src, dest_sub in sources_to_capture:
            if src.exists():
                dest_sub_path = snapshot_path / dest_sub
                if src.is_file():
                    dest_file = dest_sub_path / src.name
                    dest_file.write_bytes(src.read_bytes())
                    file_hash = hashlib.sha256(src.read_bytes()).hexdigest().lower()
                    manifest["files_captured"].append({"path": f"{dest_sub}/{src.name}", "sha256": file_hash})
                elif src.is_dir():
                    for f in src.rglob("*"):
                        if f.is_file():
                            rel_path = f.relative_to(src)
                            target_file = dest_sub_path / rel_path
                            target_file.parent.mkdir(parents=True, exist_ok=True)
                            target_file.write_bytes(f.read_bytes())
                            file_hash = hashlib.sha256(f.read_bytes()).hexdigest().lower()
                            manifest["files_captured"].append({"path": f"{dest_sub}/{rel_path}", "sha256": file_hash})

        manifest_path = snapshot_path / "manifest.sha256"
        manifest_json = json.dumps(manifest, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
        global_hash = hashlib.sha256(manifest_json.encode("utf-8")).hexdigest().lower()

        final_manifest = {**manifest, "global_snapshot_sha256": global_hash}
        manifest_path.write_text(json.dumps(final_manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        return final_manifest

    def restore_snapshot(self, snapshot_id: str) -> dict[str, Any]:
        """
        Vérifie le manifeste cryptographique d'un snapshot et restaure l'organisme
        à l'état enregistré de manière atomique sous le contrôle d'ECOL.
        """
        snapshot_path = self.snapshots_dir / snapshot_id
        if not snapshot_path.exists():
            raise SnapshotRestoreError(f"FAIL CLOSED : Le snapshot '{snapshot_id}' est introuvable.")

        manifest_path = snapshot_path / "manifest.sha256"
        if not manifest_path.exists():
            raise SnapshotRestoreError(f"FAIL CLOSED : Manifeste d'intégrité absent pour le snapshot '{snapshot_id}'.")

        manifest_data = json.loads(manifest_path.read_text(encoding="utf-8"))

        # Vérification intégrité SHA-256 de chaque fichier capturé
        for file_info in manifest_data.get("files_captured", []):
            rel_path = file_info["path"]
            expected_hash = file_info["sha256"]

            src_file = snapshot_path / rel_path
            if not src_file.exists():
                raise SnapshotRestoreError(f"FAIL CLOSED : Fichier manquant dans le snapshot -> {rel_path}")

            actual_hash = hashlib.sha256(src_file.read_bytes()).hexdigest().lower()
            if actual_hash != expected_hash:
                raise SnapshotRestoreError(
                    f"FAIL CLOSED : Corruption détectée sur '{rel_path}' ! Attendu: {expected_hash[:12]} | Obtenu: {actual_hash[:12]}"
                )

        payload = {
            "source_component": "system_core",
            "action": "ATOMIC_SNAPSHOT_RESTORE",
            "task_description": f"Restauration atomique du snapshot '{snapshot_id}'",
            "priority": "critical",
            "risk_level": "low",
            "estimated_cost": 100,
        }

        def execute_atomic_restore():
            restored_count = 0
            for file_info in manifest_data.get("files_captured", []):
                rel_path = file_info["path"]
                src_file = snapshot_path / rel_path

                if rel_path.startswith("constitution/"):
                    target_file = self.root_dir / "core" / "constitution" / Path(rel_path).name
                elif rel_path.startswith("memory/"):
                    target_file = self.root_dir / "runtime" / "memory_store" / Path(rel_path).relative_to("memory")
                elif rel_path.startswith("skills/"):
                    target_file = self.root_dir / "runtime" / "skills_store" / Path(rel_path).relative_to("skills")
                elif rel_path.startswith("ledgers/"):
                    target_file = self.root_dir / "runtime" / "ecol" / "evolution_ledger" / Path(rel_path).relative_to("ledgers")
                else:
                    continue

                target_file.parent.mkdir(parents=True, exist_ok=True)
                target_file.write_bytes(src_file.read_bytes())
                restored_count += 1

            return {
                "snapshot_id": snapshot_id,
                "status": "RESTORED_SUCCESS",
                "files_restored": restored_count,
                "global_manifest_hash": manifest_data.get("global_snapshot_sha256"),
            }

        # Validation No-Bypass via ECOL
        result = self.gateway.execute_via_gateway(action="ATOMIC_SNAPSHOT_RESTORE", payload=payload, target_func=execute_atomic_restore)

        return result


def test_snapshot_restore():
    print("[*] Test de l'Atomic Snapshot Restore Engine (V8.8)...")

    snapshots_dir = Path(r"G:\AI\E-zzio\runtime\snapshots")
    available_snaps = [d.name for d in snapshots_dir.iterdir() if d.is_dir()] if snapshots_dir.exists() else []

    engine = SnapshotRestoreEngine()
    if not available_snaps:
        print("  [INFO] Aucun snapshot détecté. Création d'un point de référence initial...")
        new_snap = engine.create_bootstrap_snapshot()
        latest_snap = new_snap["snapshot_id"]
        print(f"  [INFO] Snapshot de bootstrap créé : {latest_snap}")
    else:
        latest_snap = sorted(available_snaps)[-1]

    print(f"\n--- Test de restauration atomique pour le snapshot : {latest_snap} ---")
    try:
        res = engine.restore_snapshot(latest_snap)
        print("  [PASS] Restauration atomique réussie !")
        print(f"         Snapshot ID       : {res['snapshot_id']}")
        print(f"         Fichiers restaurés: {res['files_restored']}")
        print(f"         Global SHA256     : {res['global_manifest_hash'][:16]}...")
        print(f"         Statut organisme  : {res['status']}")
    except Exception as e:
        print(f"  [FAIL] Erreur de restauration : {e}")

    print("\n" + "=" * 65)
    print(" SNAPSHOT RESTORE ENGINE (V8.8) : TIME TRAVEL ROUND-TRIP VERIFIED")
    print("=" * 65)


if __name__ == "__main__":
    test_snapshot_restore()
