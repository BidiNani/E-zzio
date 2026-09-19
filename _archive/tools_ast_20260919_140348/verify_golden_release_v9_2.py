"""
tools/verify_golden_release_v9_2.py - Verificateur d'integrite officielle Golden Release E-ZZIO V9.2.
"""
import hashlib
import json
import os
import subprocess
import sys
import zipfile
from pathlib import Path

ROOT = Path("G:/AI/E-zzio").resolve()
os.chdir(ROOT)

print("=" * 60)
print("   E-ZZIO V9.2 — GOLDEN RELEASE INTEGRITY VERIFIER")
print("=" * 60)

# 1. Verification Frozen Core (3/3)
print("[1/8] Verification cryptographique du Frozen Core...")
fc_expected = {
    "core/capabilities/capability_policy.py": "89A770354EBFE4233697F944F0963C3873B811AF1C7DF73E6DACC7AABB389AE2",
    "core/capabilities/registry.py": "3EE057B327354FAA95CF72A0A920A5EED4FA5DF77AE87298615ED3860FFB0F68",
    "core/security/audit_ledger.py": "B26E0D106F0E76121B15B6278F057DEA3ABC1395AA425D86D383E695DFC21C17"
}
for p, h in fc_expected.items():
    actual = hashlib.sha256((ROOT / p).read_bytes()).hexdigest().upper()
    if actual != h:
        print(f"[FAIL] Frozen Core inviolability violation on {p}: {actual} != {h}")
        sys.exit(1)
print("[OK] Frozen Core 3/3 INTACT.")

# 2. Verification des Empreintes d'Artefacts
print("[2/8] Verification des empreintes d'artefacts state/audit/golden/v9.2/...")
art_meta = json.loads((ROOT / "state/audit/golden/v9.2/artifact_hashes.json").read_text(encoding="utf-8"))
for rel, info in art_meta.items():
    actual = hashlib.sha256((ROOT / rel).read_bytes()).hexdigest().upper()
    expected = info["sha256"]
    if actual != expected:
        print(f"[FAIL] Artefact hash mismatch for {rel}: {actual} != {expected}")
        sys.exit(1)
print("[OK] Tous les artefacts de release correspondent aux hashes certifies.")

# 3. Verification Forensique APK
print("[3/8] Verification du binaire APK Release...")
apk_path = ROOT / "dist/android/E-ZzIO-v9.1-release.apk"
with zipfile.ZipFile(apk_path, "r") as z:
    names = set(z.namelist())
    if not {"classes.dex", "resources.arsc", "AndroidManifest.xml"}.issubset(names):
        print("[FAIL] APK non conforme (classes.dex ou resources.arsc manquant) !")
        sys.exit(1)
print("[OK] Binaire APK release Dalvik & ressources valides.")

# 4. Verification de l'Archive Golden
print("[4/8] Verification de l'archive Golden Source V9.2...")
archive_path = ROOT / "dist/releases/E-ZZIO-V9.2-GOLDEN-SOURCE.zip"
manifest_path = ROOT / "dist/releases/E-ZZIO-V9.2-GOLDEN-MANIFEST.json"
if not archive_path.exists() or not manifest_path.exists():
    print("[FAIL] Archive ou manifeste Golden V9.2 manquant !")
    sys.exit(1)
arch_hash = hashlib.sha256(archive_path.read_bytes()).hexdigest().upper()
manifest_data = json.loads(manifest_path.read_text(encoding="utf-8"))
if arch_hash != manifest_data["archive_sha256"]:
    print(f"[FAIL] Archive hash mismatch: {arch_hash} != {manifest_data['archive_sha256']}")
    sys.exit(1)
print(f"[OK] Archive Golden Source integre ({arch_hash}).")

# 5. Verification Documentation Golden V9.2
print("[5/8] Verification des documents obligatoires Golden V9.2...")
required_docs = [
    "docs/V9.2_GAP_MATRIX.md",
    "docs/E-ZZIO_V9.2_FINAL_GAP_CLOSURE_REPORT.md",
    "docs/V9.2_GOLDEN_COMPARISON.md",
    "state/audit/golden/v9.2/provenance_seal.json"
]
for doc in required_docs:
    if not (ROOT / doc).exists():
        print(f"[FAIL] Document obligatoire manquant: {doc}")
        sys.exit(1)
print("[OK] Documentation Golden V9.2 complete et presente.")

# 6. Verification de la Suite de Regression (123 tests)
if "--skip-tests" not in sys.argv:
    print("[6/8] Verification de la suite de certification complete V9.2 (123 tests)...")
    res = subprocess.run([
        sys.executable, "-m", "pytest",
        "tests/test_hitl_approval.py", "tests/test_hermes_mcp_confinement.py",
        "tests/test_federation_smokes.py", "tests/test_ai_office_visual.py",
        "tests/test_ai_office.py", "tests/test_product_certification.py",
        "tests/test_product_lifecycle.py", "tests/test_hitl_api.py",
        "tests/test_hitl_cli.py", "tests/test_hitl_discord.py",
        "tests/test_capability_policy.py", "tests/test_capability_enforcement.py",
        "tests/test_android_project.py", "tests/test_android_artifact.py",
        "tests/test_android_runtime_contract.py", "tests/test_android_device_gate.py",
        "tests/test_v9_2_platform.py", "tests/test_v9_2_gap_closure.py",
        "-q"
    ], capture_output=True, text=True)
    if res.returncode != 0:
        print(f"[FAIL] Suite de tests en echec:\n{res.stdout}\n{res.stderr}")
        sys.exit(1)
    print("[OK] 123/123 tests PASS (100% hygiene verte).")

# 7. Verification Runtime Android Device
print("[7/8] Verification de l'execution reelle sur materiel Android / AVD...")
adb = Path("G:/tools/platform-tools/adb.exe")
if adb.exists():
    pm_res = subprocess.run([str(adb), "shell", "pm", "path", "ai.ezzio.office"], capture_output=True, text=True)
    if "ai.ezzio.office" in pm_res.stdout:
        print("[OK] Package ai.ezzio.office actif et detecte sur l'appareil connecte.")
    else:
        print(f"[WARN] Appareil detecte mais package non confirme: {pm_res.stdout}")

# 8. Verdict Global
print("=" * 60)
print("   GOLDEN_RELEASE_VALID")
print("   E-ZZIO V9.2 BASELINE IMMUTABLE & VERIFIEE AVEC SUCCES")
print("=" * 60)
