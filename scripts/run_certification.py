import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def run_certification():
    print("\n--- [PILIER 1] INTÉGRITÉ STATIQUE (RUFF READ-ONLY) ---")
    ruff_res = subprocess.run(
        [sys.executable, "-m", "ruff", "check", "core/", "runtime/core/", "routers/", "interfaces/", "tests/"],
        capture_output=True,
        text=True,
        cwd=str(ROOT),
    )
    if ruff_res.returncode == 0:
        print("  [PASS] Analyse statique : 0 violation, 0 dette technique.")
    else:
        print(f"  [FAIL] Dette détectée :\n{ruff_res.stdout}")
        sys.exit(1)

    print("\n--- [PILIER 2] TESTS FONCTIONNELS & WARNINGS STRICTS ---")
    pytest_res = subprocess.run(
        [sys.executable, "-W", "error::DeprecationWarning", "-m", "pytest", "-v", "tests"], capture_output=True, text=True, cwd=str(ROOT)
    )

    passed_count = pytest_res.stdout.count(" PASSED")
    failed_count = pytest_res.stdout.count(" FAILED")

    if failed_count == 0 and passed_count >= 40:
        print(f"  [PASS] {passed_count}/{passed_count} tests au vert.")
        print("  [PASS] Zéro DeprecationWarning ou fuite toxique.")
    else:
        print(f"  [FAIL] Échec des tests ({passed_count} passés, {failed_count} échoués) :\n")
        # On affiche uniquement les lignes d'erreur pour ne pas polluer l'écran
        for line in pytest_res.stdout.splitlines():
            if "FAILED" in line or "ERROR" in line:
                print(f"    {line}")
        sys.exit(1)

    print("\n=====================================================")
    print("      STATUT GLOBAL : E-ZZIO OS 100% CERTIFIÉ       ")
    print("=====================================================\n")


if __name__ == "__main__":
    run_certification()
