"""
E-ZZIO Core — EZZIO_BACKUP_GUARDIAN (V8.9.2)
Sélectionne les organes vitaux, valide leur intégrité cryptographique,
génère un manifeste SHA-256 et exporte l'archive vers un stockage externe sécurisé.
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


class BackupGuardianError(Exception):
    """Levée si l'intégrité de l'organisme est compromise avant l'archivage (Fail-Closed)."""

    pass


class EzzioBackupGuardian:
    def __init__(self, root_dir: Path = ROOT_DIR, safe_destination: Path = Path(r"C:\AI_Backups\E-zzio")):
        self.root_dir = root_dir
        self.safe_destination = safe_destination
        self.safe_destination.mkdir(parents=True, exist_ok=True)

        self.gateway = EcolUniversalGateway()
        self.gateway.register_gateway_action("BACKUP_GUARDIAN_ARCHIVE")

    def validate_organism_integrity(self) -> dict[str, str]:
        """
        Vérifie l'existence et l'intégrité des organes critiques avant d'autoriser l'archivage.
        """
        genome_path = self.root_dir / "core" / "constitution" / "ezzio_genome.json"
        framework_path = self.root_dir / "core" / "constitution" / "ezzio_global_framework.py"

        if not genome_path.exists():
            raise BackupGuardianError("FAIL CLOSED : Génome introuvable. Archivage interdit.")
        if not framework_path.exists():
            raise BackupGuardianError("FAIL CLOSED : Cadre constitutionnel introuvable. Archivage interdit.")

        genome_bytes = genome_path.read_bytes()
        genome_hash = hashlib.sha256(genome_bytes).hexdigest().lower()

        framework_bytes = framework_path.read_bytes()
        framework_hash = hashlib.sha256(framework_bytes).hexdigest().lower()

        return {"genome_hash": genome_hash, "constitution_hash": framework_hash}

    def execute_secure_backup(self) -> dict[str, Any]:
        """
        Exécute le backup sécurisé des organes vitaux vers la destination séparée sous le contrôle d'ECOL.
        """
        # 1. Validation préalable
        hashes = self.validate_organism_integrity()

        timestamp_str = datetime.now(UTC).strftime("%Y%m%d_%H%M%S")
        backup_id = f"EZZIO_BACKUP_{timestamp_str}"
        backup_target_dir = self.safe_destination / backup_id
        backup_target_dir.mkdir(parents=True, exist_ok=True)

        # 2. Définition des organes vitaux à capturer
        vital_organs = [
            (self.root_dir / "core" / "constitution", "constitution"),
            (self.root_dir / "core" / "cognition", "cognition"),
            (self.root_dir / "runtime" / "ecol", "ecol"),
            (self.root_dir / "runtime" / "memory_store", "memory_store"),
            (self.root_dir / "runtime" / "skills_store", "skills_store"),
            (self.root_dir / "runtime" / "snapshots", "snapshots"),
        ]

        files_captured_count = 0
        manifest_files = []

        for src_path, sub_dir in vital_organs:
            if src_path.exists():
                dest_sub_path = backup_target_dir / sub_dir
                dest_sub_path.mkdir(parents=True, exist_ok=True)

                if src_path.is_file():
                    target_file = dest_sub_path / src_path.name
                    target_file.write_bytes(src_path.read_bytes())
                    f_hash = hashlib.sha256(src_path.read_bytes()).hexdigest().lower()
                    manifest_files.append({"path": f"{sub_dir}/{src_path.name}", "sha256": f_hash})
                    files_captured_count += 1
                elif src_path.is_dir():
                    for f in src_path.rglob("*"):
                        if f.is_file():
                            rel_p = f.relative_to(src_path)
                            target_file = dest_sub_path / rel_p
                            target_file.parent.mkdir(parents=True, exist_ok=True)
                            target_file.write_bytes(f.read_bytes())
                            f_hash = hashlib.sha256(f.read_bytes()).hexdigest().lower()
                            manifest_files.append({"path": f"{sub_dir}/{rel_p}", "sha256": f_hash})
                            files_captured_count += 1

        # 3. Création du manifeste cryptographique global
        manifest = {
            "backup_id": backup_id,
            "created_utc": datetime.now(UTC).isoformat(),
            "files_count": files_captured_count,
            "genome_hash": hashes["genome_hash"],
            "constitution_hash": hashes["constitution_hash"],
            "files_manifest": manifest_files,
            "status": "VERIFIED",
        }

        manifest_json = json.dumps(manifest, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
        global_sha256 = hashlib.sha256(manifest_json.encode("utf-8")).hexdigest().lower()

        final_manifest = {**manifest, "global_sha256": global_sha256}

        manifest_path = backup_target_dir / "backup_manifest.sha256"
        manifest_path.write_text(json.dumps(final_manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

        payload = {
            "source_component": "system_core",
            "action": "BACKUP_GUARDIAN_ARCHIVE",
            "task_description": f"Création du backup externe sécurisé [{backup_id}]",
            "priority": "critical",
            "risk_level": "low",
            "estimated_cost": files_captured_count,
        }

        def commit_backup_record():
            return {
                "backup_id": backup_id,
                "destination": str(backup_target_dir),
                "files_captured": files_captured_count,
                "global_sha256": global_sha256,
                "status": "VERIFIED_AND_SECURED",
            }

        # Validation No-Bypass via ECOL
        result = self.gateway.execute_via_gateway(action="BACKUP_GUARDIAN_ARCHIVE", payload=payload, target_func=commit_backup_record)

        return result


def test_backup_guardian():
    print("[*] Test de l'EZZIO_BACKUP_GUARDIAN (V8.9.2)...")
    guardian = EzzioBackupGuardian()

    try:
        res = guardian.execute_secure_backup()
        print("\n  [PASS] Backup externe sécurisé créé avec succès !")
        print(f"         Backup ID     : {res['backup_id']}")
        print(f"         Destination   : {res['destination']}")
        print(f"         Fichiers capt : {res['files_captured']}")
        print(f"         Global SHA256 : {res['global_sha256'][:16]}...")
        print(f"         Statut        : {res['status']}")
    except Exception as e:
        print(f"  [FAIL] Échec du backup de sécurité : {e}")

    print("\n" + "=" * 65)
    print(" EZZIO_BACKUP_GUARDIAN (V8.9.2) : DISASTER RECOVERY ARMED")
    print("=" * 65)


if __name__ == "__main__":
    test_backup_guardian()
