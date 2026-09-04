import zipfile
from pathlib import Path

ROOT = Path("G:/AI/E-zzio")
archive = ROOT / "dist/releases/E-ZzIO-V9.1-GOLDEN-SOURCE.zip"

print(f"Testing Archive Recovery: {archive}")
with zipfile.ZipFile(archive, "r") as z:
    names = set(z.namelist())
    
    # Check essential layers
    checks = [
        ("core/capabilities/capability_policy.py", "Frozen Core Policy"),
        ("core/capabilities/registry.py", "Frozen Core Registry"),
        ("core/security/audit_ledger.py", "Frozen Core Ledger"),
        ("runtime/web/index.html", "Living AI Office UI"),
        ("runtime/web/manifest.json", "PWA Manifest"),
        ("runtime/web/sw.js", "Service Worker"),
        ("android/app/src/main/AndroidManifest.xml", "Android Source Manifest"),
        ("android/app/src/main/java/ai/ezzio/office/MainActivity.java", "Android MainActivity"),
        ("android/app/build.gradle", "Android Gradle Build"),
        ("dist/android/E-ZzIO-v9.1-release.apk", "Compiled Release APK"),
        ("tools/launch_desktop.ps1", "Desktop Launcher"),
        ("tools/build_android_apk.ps1", "Android Builder"),
        ("tests/test_android_device_gate.py", "Device Gate Test"),
        ("tests/test_product_certification.py", "Product Cert Test"),
        ("docs/RELEASE_MANIFEST.json", "Release Manifest"),
        ("docs/E-ZZIO_V9.1_GOLDEN_RELEASE_LOCK.md", "Golden Lock Doc"),
        ("docs/GOLDEN_RELEASE_RESTORE.md", "Restore Guide")
    ]
    
    all_ok = True
    for p, desc in checks:
        if p in names:
            print(f"  [OK] {desc}: {p}")
        else:
            print(f"  [FAIL] Missing: {p}")
            all_ok = False

if all_ok:
    print("RECOVERY_ARCHIVE_VERIFICATION: PASS (All components present)")
else:
    print("RECOVERY_ARCHIVE_VERIFICATION: FAILED")
