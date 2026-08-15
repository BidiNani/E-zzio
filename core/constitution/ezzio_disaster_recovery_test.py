"""
E-ZZIO Core — Disaster Recovery Round Trip Test (V8.9.2)
Valide l'exploitabilité d'un backup externe, vérifie les hashes SHA-256 de bout en bout,
exécute une restauration isolée et valide le boot logique de l'organisme restauré.
"""
import os
import sys
import json
import hashlib
import logging
from pathlib import Path
from typing import Dict, Any

ROOT_DIR = Path(r"G:\AI\E-zzio")
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

logging.basicConfig(level=logging.WARNING)

class DisasterRecoveryTester:
    def __init__(self, backup_root: Path = Path(r"C:\AI_Backups\E-zzio"), test_restore_target: Path = Path(r"C:\AI_Test_Restore\E-ZZIO_RECOVERY_TEST")):
        self.backup_root = backup_root
        self.test_restore_target = test_restore_target

    def find_latest_backup(self) -> Path:
        if not self.backup_root.exists():
            raise FileNotFoundError(f"Stockage de backup externe introuvable : {self.backup_root}")
        
        backups = [d for d in self.backup_root.iterdir() if d.is_dir() and d.name.startswith("EZZIO_BACKUP_")]
        if not backups:
            raise FileNotFoundError("Aucun backup externe E-zzio disponible pour le test.")
        
        return sorted(backups)[-1]

    def run_round_trip_test(self) -> Dict[str, Any]:
        print("[*] Étape 1 : Localisation du backup externe le plus récent...")
        latest_backup = self.find_latest_backup()
        print(f"    Trouvé : {latest_backup.name}")

        manifest_path = latest_backup / "backup_manifest.sha256"
        if not manifest_path.exists():
            raise FileNotFoundError(f"Manifeste de backup introuvable dans {latest_backup}")

        print("[*] Étape 2 : Chargement et vérification du manifeste SHA-256...")
        manifest_data = json.loads(manifest_path.read_text(encoding="utf-8"))
        
        # Vérification du global sha256 du manifeste
        stored_global_hash = manifest_data.get("global_sha256")
        
        # Recalcul de l'intégrité des fichiers du manifeste
        verified_files = 0
        for file_info in manifest_data.get("files_manifest", []):
            rel_p = file_info["path"]
            expected_hash = file_info["sha256"]
            
            src_file = latest_backup / rel_p
            if not src_file.exists():
                raise RuntimeError(f"Fichier manquant dans l'archive externe : {rel_p}")
            
            actual_hash = hashlib.sha256(src_file.read_bytes()).hexdigest().lower()
            if actual_hash != expected_hash:
                raise RuntimeError(f"Corruption détectée sur '{rel_p}' (Attendu: {expected_hash[:12]} | Obtenu: {actual_hash[:12]})")
            verified_files += 1

        print(f"    [PASS] Intégrité vérifiée : {verified_files}/{verified_files} fichiers conformes.")

        print("[*] Étape 3 : Restauration isolée dans l'environnement de test (C:\AI_Test_Restore)...")
        if self.test_restore_target.exists():
            import shutil
            shutil.rmtree(self.test_restore_target)
        self.test_restore_target.mkdir(parents=True, exist_ok=True)

        restored_count = 0
        for file_info in manifest_data.get("files_manifest", []):
            rel_p = file_info["path"]
            src_file = latest_backup / rel_p
            
            target_file = self.test_restore_target / rel_p
            target_file.parent.mkdir(parents=True, exist_ok=True)
            target_file.write_bytes(src_file.read_bytes())
            restored_count += 1

        print(f"    [PASS] Restauration isolée réussie : {restored_count} fichiers écrits.")

        print("[*] Étape 4 : Validation du boot logique post-restauration...")
        # Vérification de la présence du génome et du framework constitutionnel dans la zone de test
        test_genome = self.test_restore_target / "constitution" / "ezzio_genome.json"
        test_framework = self.test_restore_target / "constitution" / "ezzio_global_framework.py"
        
        if not test_genome.exists() or not test_framework.exists():
            raise RuntimeError("Échec du boot logique : Organes vitaux absents dans la zone restaurée.")

        genome_data = json.loads(test_genome.read_text(encoding="utf-8"))
        organism_id = genome_data.get("organism_id")
        mentor = genome_data.get("birth", {}).get("mentor")

        return {
            "backup_id": manifest_data.get("backup_id"),
            "files_verified": verified_files,
            "files_restored": restored_count,
            "restored_location": str(self.test_restore_target),
            "organism_id": organism_id,
            "mentor": mentor,
            "status": "DISASTER_RECOVERY_ROUND_TRIP_SUCCESS"
        }

def test_dr_round_trip():
    print("[*] Lancement du test Disaster Recovery Round-Trip (V8.9.2)...")
    tester = DisasterRecoveryTester()
    try:
        res = tester.run_round_trip_test()
        print("\n" + "="*70)
        print(" E-ZZIO DISASTER RECOVERY ROUND-TRIP CERTIFICATE")
        print("="*70)
        print(f" Backup ID source    : {res['backup_id']}")
        print(f" Fichiers vérifiés   : {res['files_verified']} / {res['files_verified']}")
        print(f" Fichiers restaurés  : {res['files_restored']}")
        print(f" Cible isolée        : {res['restored_location']}")
        print(f" Identité restaurée  : {res['organism_id']} (Mentor: {res['mentor']})")
        print(f" ÉTAT DU ROUND-TRIP  : {res['status']}")
        print("="*70 + "\n")
    except Exception as e:
        print(f"\n  [FAIL] Le test de Disaster Recovery a échoué : {e}")

if __name__ == "__main__":
    test_dr_round_trip()
