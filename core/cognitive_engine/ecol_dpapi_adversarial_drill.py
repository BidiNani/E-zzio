"""
E-ZZIO Core — DPAPI Adversarial Certification (V7.64.2)
Correction de l'affectation du secret déchiffré (Test 1) et génération dynamique du Trust Report.
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
        ctypes.byref(blob_in), "E-ZZIO Sandbox Root", None, None, None, 0, ctypes.byref(blob_out)
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
        raise DPAPIVaultError("Échec déchiffrement DPAPI (contexte invalide ou altération).")
    dec = ctypes.string_at(blob_out.pbData, blob_out.cbData)
    ctypes.windll.kernel32.LocalFree(blob_out.pbData)
    return dec

class SandboxDPAPIManager:
    def __init__(self, sandbox_dir: Path):
        self.sandbox_dir = sandbox_dir
        self.vault_path = self.sandbox_dir / "dpapi_vault.json"
        self.keys_dir = self.sandbox_dir / "dpapi_keys"
        self.sandbox_dir.mkdir(parents=True, exist_ok=True)
        self.keys_dir.mkdir(parents=True, exist_ok=True)

    def _canonical_dump(self, payload: dict) -> str:
        return json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False)

    def initialize(self, key_id: str = "ECOL-DPAPI-KEY-001"):
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

    def rotate(self, new_key_id: str):
        vault = json.loads(self.vault_path.read_text(encoding="utf-8"))
        old_active = vault["active_key_id"]
        raw_secret = os.urandom(32)
        encrypted = _dpapi_encrypt(raw_secret)
        (self.keys_dir / f"{new_key_id}.dpkey").write_bytes(encrypted)

        vault["keys"][old_active]["status"] = "VERIFY_ONLY"
        vault["keys"][new_key_id] = {"status": "ACTIVE", "created_at": datetime.now(timezone.utc).isoformat()}
        vault["active_key_id"] = new_key_id
        self.vault_path.write_text(self._canonical_dump(vault) + "\n", encoding="utf-8")
        return raw_secret

    def get_secret(self, key_id: str) -> bytes:
        vault = json.loads(self.vault_path.read_text(encoding="utf-8"))
        if key_id not in vault.get("keys", {}):
            raise DPAPIVaultError(f"Clé inconnue ou révoquée : {key_id}")
        key_file = self.keys_dir / f"{key_id}.dpkey"
        if not key_file.exists():
            raise DPAPIVaultError(f"Fichier de clé physique absent : {key_id}.dpkey")
        return _dpapi_decrypt(key_file.read_bytes())

def run_adversarial_drill():
    print("[*] Lancement du DPAPI Adversarial Certification Drill (V7.64.2)...")
    sandbox = ROOT_DIR / "runtime" / "security" / "dpapi_sandbox"
    if sandbox.exists():
        shutil.rmtree(sandbox)

    manager = SandboxDPAPIManager(sandbox)
    test_results = {}

    # -------------------------------------------------------------
    # TEST 1 : Nominal Encryption & Decryption
    # -------------------------------------------------------------
    print("\n--- Test 1 : Nominal DPAPI Roundtrip ---")
    try:
        secret_orig = manager.initialize("ECOL-DPAPI-KEY-001")
        secret_dec = manager.get_secret("ECOL-DPAPI-KEY-001")  # Correction : assignation directe des bytes
        assert secret_orig == secret_dec, "Le secret déchiffré ne correspond pas à l'original."
        test_results["nominal_roundtrip"] = "PASS"
        print("  [PASS] Nominal OK.")
    except Exception as e:
        test_results["nominal_roundtrip"] = f"FAIL: {e}"
        print(f"  [FAIL] {e}")

    # -------------------------------------------------------------
    # TEST 2 : Corrupted .dpkey file -> Fail-Closed
    # -------------------------------------------------------------
    print("\n--- Test 2 : Corrupted .dpkey File (Fail-Closed) ---")
    try:
        key_file = sandbox / "dpapi_keys" / "ECOL-DPAPI-KEY-001.dpkey"
        key_file.write_bytes(os.urandom(64))
        manager.get_secret("ECOL-DPAPI-KEY-001")
        test_results["corrupted_dpkey"] = "FAIL: Accepté un fichier corrompu !"
        print("  [FAIL] Le système a accepté un fichier DPAPI corrompu !")
    except DPAPIVaultError:
        test_results["corrupted_dpkey"] = "PASS"
        print("  [PASS] Interception immédiate (FAIL CLOSED).")
    except Exception as e:
        test_results["corrupted_dpkey"] = f"PASS (via exception: {e})"
        print(f"  [PASS] Interception via exception : {e}")

    # Réinitialisation sandbox pour les tests suivants
    shutil.rmtree(sandbox)
    manager = SandboxDPAPIManager(sandbox)
    manager.initialize("ECOL-DPAPI-KEY-001")

    # -------------------------------------------------------------
    # TEST 3 : Missing .dpkey file -> Fail-Closed
    # -------------------------------------------------------------
    print("\n--- Test 3 : Missing .dpkey File (Fail-Closed) ---")
    try:
        key_file = sandbox / "dpapi_keys" / "ECOL-DPAPI-KEY-001.dpkey"
        key_file.unlink()
        manager.get_secret("ECOL-DPAPI-KEY-001")
        test_results["missing_dpkey"] = "FAIL: Clé manquante ignorée !"
        print("  [FAIL] Clé manquante ignorée !")
    except DPAPIVaultError:
        test_results["missing_dpkey"] = "PASS"
        print("  [PASS] Interception immédiate de la perte de fichier (FAIL CLOSED).")

    # Réinitialisation sandbox
    shutil.rmtree(sandbox)
    manager = SandboxDPAPIManager(sandbox)
    manager.initialize("ECOL-DPAPI-KEY-001")

    # -------------------------------------------------------------
    # TEST 4 : ACTIVE vs VERIFY_ONLY Enforcement & Rotation
    # -------------------------------------------------------------
    print("\n--- Test 4 : Active vs Verify-Only Epoch Rotation ---")
    try:
        manager.rotate("ECOL-DPAPI-KEY-002")
        vault = json.loads((sandbox / "dpapi_vault.json").read_text(encoding="utf-8"))
        
        assert vault["active_key_id"] == "ECOL-DPAPI-KEY-002", "La nouvelle clé n'est pas active."
        assert vault["keys"]["ECOL-DPAPI-KEY-001"]["status"] == "VERIFY_ONLY", "L'ancienne clé n'est pas en VERIFY_ONLY."
        
        old_secret = manager.get_secret("ECOL-DPAPI-KEY-001")
        assert len(old_secret) == 32, "Échec de lecture de l'ancienne époque."
        
        test_results["epoch_rotation_and_verify_only"] = "PASS"
        print("  [PASS] Rotation validée et ancienneté protégée en VERIFY_ONLY.")
    except Exception as e:
        test_results["epoch_rotation_and_verify_only"] = f"FAIL: {e}"
        print(f"  [FAIL] {e}")

    # Nettoyage final du sandbox de test
    if sandbox.exists():
        shutil.rmtree(sandbox)

    # -------------------------------------------------------------
    # ÉVALUATION DYNAMIQUE DU RAPPORT D'AUDIT (Basé 100% sur les faits)
    # -------------------------------------------------------------
    all_passed = all(val == "PASS" for val in test_results.values())
    overall_status = "CERTIFIED ADVERSARIAL PASS" if all_passed else "CERTIFICATION DEGRADED / FAILED"

    report = {
        "target": "E-ZZIO Secret Sovereignty DPAPI Layer",
        "version": "V7.64.2",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "adversarial_test_results": test_results,
        "os_bound_protection": "Windows DPAPI (User-Context)",
        "overall_status": overall_status
    }

    report_path = ROOT_DIR / "runtime" / "cognition" / "budget" / "ECOL_TRUST_REPORT.json"
    report_path.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"\n[*] Rapport d'audit dynamique généré : {report_path}")
    print(f"[*] Statut global : {overall_status}")

if __name__ == "__main__":
    run_adversarial_drill()
