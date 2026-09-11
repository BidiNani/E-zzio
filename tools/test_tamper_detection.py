import subprocess
import shutil
import sys
from pathlib import Path

ROOT = Path("G:/AI/E-zzio")
target_file = ROOT / "tools/launch_desktop.ps1"
backup_file = ROOT / "tools/launch_desktop.ps1.tamper_bak"

pwsh_exe = "pwsh"
shutil.copy2(target_file, backup_file)
tamper_detected = False

try:
    with open(target_file, "a", encoding="utf-8") as f:
        f.write("\n# TAMPER_TEST_STRING\n")
    
    # Run verifier: it should FAIL with exit code != 0
    res_tamper = subprocess.run(
        [pwsh_exe, "-ExecutionPolicy", "Bypass", "-File", str(ROOT / "tools/verify_golden_release.ps1"), "-SkipTests"],
        capture_output=True,
        text=True
    )
    if res_tamper.returncode != 0:
        tamper_detected = True
        print("[OK] Tamper successfully detected by verifier (Exit Code:", res_tamper.returncode, ")")
    else:
        print("[FAIL] Tamper was NOT detected:", res_tamper.stdout)

finally:
    shutil.move(backup_file, target_file)

# Run verifier on restored clean state: it should PASS with exit code 0
res_clean = subprocess.run(
    [pwsh_exe, "-ExecutionPolicy", "Bypass", "-File", str(ROOT / "tools/verify_golden_release.ps1"), "-SkipTests"],
    capture_output=True,
    text=True
)

if res_clean.returncode == 0 and "GOLDEN_RELEASE_VALID" in res_clean.stdout:
    print("[OK] Post-restore verifier returned GOLDEN_RELEASE_VALID.")
else:
    print("[FAIL] Post-restore verification failed:", res_clean.stdout, res_clean.stderr)

if tamper_detected and res_clean.returncode == 0:
    print("TAMPER_DETECTION_AND_RESTORE: PASS")
    sys.exit(0)
else:
    print("TAMPER_DETECTION_AND_RESTORE: FAILED")
    sys.exit(1)
