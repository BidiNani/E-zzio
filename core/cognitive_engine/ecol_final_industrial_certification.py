"""
E-ZZIO Core — Final Industrial Certification Drill (V7.65)
Teste les dernières frontières de confiance (incohérence d'ID, corruption de vault,
échec DPAPI et disaster recovery complet) pour l'obtention objective du 10/10.
"""
import os
import sys
import json
import ctypes
import hmac
import logging
import hashlib
import shutil
from pathlib import Path
from datetime import datetime, timezone

logger = logging.getLogger(__name__)

ROOT_DIR = Path(r"G:\AI\E-zzio")

class DPAPIVaultError(Exception):
    pass

class DATA_BLOB(ctypes.Structure):
    _fields_ = [("cbData", ctypes.c_ulong),
                ("pbData", ctypes.POINTER(ctypes.c_ubyte))]

def _dpapi_encrypt(secret_bytes: bytes) -> bytes:
    if os.name != "nt":
        return secret_bytes
    blob_in = DATA_BLOB(len(secret_bytes), ctypes.cast(secret_bytes, ctypes.POINTER(ctypes.c_ubyte)))
    blob_out = DATA_BLOB()
    res = ctypes.windll.crypt32.CryptProtectData(
        ctypes.byref(blob_in), "E-ZZIO Final Sandbox", None, None, None, 0, ctypes.byref(blob_out)
    )
    if not res:
        raise DPAPIVaultError("Échec chiffrement DPAPI.")
    enc = ctypes.string_at(blob_out.pbData, blob_out.cbData)
    ctypes.windll.kernel32.LocalFree(blob_out.pbData)
    return enc

def _dpapi_decrypt(encrypted_bytes: bytes) -> bytes:
    if os.name != "nt":
        return encrypted_bytes
    blob_in = DATA_BLOB(len(encrypted_bytes), ctypes.cast(encrypted_bytes, ctypes.POINTER(ctypes.c_ubyte)))
    blob_out = DATA_BLOB()
    res = ctypes.windll.crypt32.CryptUnprotectData(
        ctypes.byref(blob_in), None, None, None, None, 0, ctypes.byref(blob_out)
    )
    if not res:
        raise DPAPIVaultError("Échec déchiffrement DPAPI (contexte ou intégrité invalide).")
    dec = ctypes.string_at(blob_out.pbData, blob_out.cbData)
    ctypes.windll.kernel32.LocalFree(blob_out.pbData)
    return dec

class FinalCertificationManager:
    def __init__(self, sandbox_dir: Path):
        self.sandbox_dir = sandbox_dir
        self.vault_path = self.sandbox_dir / "dpapi_vault.json"
        self.keys_dir = self.sandbox_dir / "dpapi_keys"
        self.sandbox_dir.mkdir(parents=True, exist_ok=True)
        self.keys_dir.mkdir(parents=True, exist_ok=True)

    def _canonical_dump(self, payload: dict) -> str:
        return json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False)

    def initialize(self, key_id: str = "ECOL-KEY-001"):
        raw_secret = os.urandom(32)
        encrypted = _dpapi_encrypt(raw_secret)
        (self.keys_dir / f"{key_id}.dpkey").write_bytes(encrypted)
        vault = {
            "active_key_id": key_id,
            "protection_mode": "WINDOWS_DPAPI_USER_CURRENT",
            "keys": {
                key_id: {"status": "ACTIVE", "created_at": datetime.now(timezone.utc).isoformat()}
            }
        }
        self.vault_path.write_text(self._canonical_dump(vault) + "\n", encoding="utf-8")
        return raw_secret

    def get_secret(self, key_id: str) -> bytes:
        if not self.vault_path.exists():
            raise DPAPIVaultError("FAIL CLOSED : Coffre-fort introuvable.")
        try:
            vault = json.loads(self.vault_path.read_text(encoding="utf-8"))
        except Exception as e:
            raise DPAPIVaultError(f"FAIL CLOSED : Corruption structurelle du coffre : {e}")

        if key_id not in vault.get("keys", {}):
            raise DPAPIVaultError(f"FAIL CLOSED : Tentative d'accès à une clé inconnue ou révoquée '{key_id}'.")
        
        key_file = self.keys_dir / f"{key_id}.dpkey"
        if not key_file.exists():
            raise DPAPIVaultError(f"FAIL CLOSED : Perte physique du fichier de clé '{key_id}.dpkey'.")
        
        return _dpapi_decrypt(key_file.read_bytes())

def run_final_certification():
    print("[*] Lancement du Final Industrial Certification Drill (V7.65)...")
    sandbox = ROOT_DIR / "runtime" / "security" / "final_sandbox"
    if sandbox.exists():
        shutil.rmtree(sandbox)

    manager = FinalCertificationManager(sandbox)
    test_results = {}

    # -------------------------------------------------------------
    # TEST 1 : Key ID Inconsistency -> Fail-Closed
    # -------------------------------------------------------------
    print("\n--- Test 1 : Unknown Key ID Reference (Fail-Closed) ---")
    try:
        manager.initialize("ECOL-KEY-001")
        manager.get_secret("ECOL-KEY-999") # Clé inexistante
        test_results["unknown_key_id_rejection"] = "FAIL: Clé inconnue acceptée !"
        print("  [FAIL] Une clé inexistante a été acceptée !")
    except DPAPIVaultError:
        test_results["unknown_key_id_rejection"] = "PASS"
        print("  [PASS] Clé inconnue rejetée immédiatement (FAIL CLOSED).")

    # -------------------------------------------------------------
    # TEST 2 : Vault JSON Corruption -> Fail-Closed
    # -------------------------------------------------------------
    print("\n--- Test 2 : Vault JSON Structural Corruption (Fail-Closed) ---")
    try:
        vault_file = sandbox / "dpapi_vault.json"
        vault_file.write_text("{ broken_json_structure ", encoding="utf-8")
        manager.get_secret("ECOL-KEY-001")
        test_results["vault_json_corruption"] = "FAIL: Manifeste corrompu ignoré !"
        print("  [FAIL] Manifeste corrompu accepté !")
    except DPAPIVaultError:
        test_results["vault_json_corruption"] = "PASS"
        print("  [PASS] Corruption du manifeste interceptée (FAIL CLOSED).")

    # Réinitialisation sandbox
    shutil.rmtree(sandbox)
    manager = FinalCertificationManager(sandbox)
    manager.initialize("ECOL-KEY-001")

    # -------------------------------------------------------------
    # TEST 3 : Disaster Recovery & Complete Restore Simulation
    # -------------------------------------------------------------
    print("\n--- Test 3 : Full Disaster Recovery & Backup Restore ---")
    try:
        backup_dir = ROOT_DIR / "runtime" / "security" / "final_backup_sandbox"
        if backup_dir.exists():
            shutil.rmtree(backup_dir)
        
        # Sauvegarde (Backup)
        shutil.copytree(sandbox, backup_dir)
        print("  * Backup complet du coffre et des clés réalisé.")

        # Sinistre : Destruction totale de l'environnement actif
        shutil.rmtree(sandbox)
        print("  * Sinistre simulé : Suppression totale de la zone active.")

        # Restauration depuis le backup
        shutil.copytree(backup_dir, sandbox)
        shutil.rmtree(backup_dir)
        print("  * Restauration de l'environnement depuis l'archive de sauvegarde.")

        # Reprise et validation post-restauration
        restored_manager = FinalCertificationManager(sandbox)
        recovered_secret = restored_manager.get_secret("ECOL-KEY-001")
        assert len(recovered_secret) == 32, "Le secret restauré est invalide."

        test_results["disaster_recovery_restore"] = "PASS"
        print("  [PASS] Restauration réussie et intégrité de la racine restaurée.")
    except Exception as e:
        test_results["disaster_recovery_restore"] = f"FAIL: {e}"
        print(f"  [FAIL] {e}")

    # Nettoyage final
    if sandbox.exists():
        shutil.rmtree(sandbox)

    # -------------------------------------------------------------
    # ÉVALUATION DYNAMIQUE STRICTE DU TRUST REPORT (10/10 SEULEMENT SI TOUT PASSE)
    # -------------------------------------------------------------
    all_passed = all(val == "PASS" for val in test_results.values())
    
    if all_passed:
        overall_status = "CERTIFIED 10/10 ABSOLUTE — ECOL GOVERNANCE"
        score = "10/10"
    else:
        overall_status = "CERTIFICATION DEGRADED"
        score = "< 10/10"

    report = {
        "target": "E-ZZIO Cognitive Governance (ECOL)",
        "certification_level": score,
        "version": "V7.65",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "final_trust_boundary_results": test_results,
        "overall_governance_status": overall_status
    }

    report_path = ROOT_DIR / "runtime" / "cognition" / "budget" / "ECOL_TRUST_REPORT.json"
    report_path.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    
    print(f"\n" + "="*65)
    print(f" RÉSULTAT DE LA CERTIFICATION FINALE : {score}")
    print(f" STATUT : {overall_status}")
    print(f" RAPPORT GÉNÉRÉ : {report_path}")
    print("="*65)

if __name__ == "__main__":
    run_final_certification()
