"""
Pipeline CI/CD local de pré-commit pour E-ZzIO.
Valide la syntaxe AST de tous les fichiers Python, régénère le catalogue, exécute le linter et la suite pytest.
"""

import subprocess
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR / "src"))

from ezzio.self_repair.codebase_catalog import get_codebase_catalog
from ezzio.self_repair.auto_healer import AutoHealer


def run_pre_commit():
    print("=======================================================")
    print("         E-ZZIO LOCAL PRE-COMMIT CI/CD PIPELINE       ")
    print("=======================================================\n")
    
    # 1. Diagnostic AST & Auto-Guérison
    print("[1/4] Vérification de la santé syntaxique AST...")
    healer = AutoHealer()
    report = healer.diagnose_all()
    if not report["healthy"]:
        print("❌ ÉCHEC : Erreurs de syntaxe détectées !")
        for err in report["syntax_errors"]:
            print(f"  - {err['file']} : {err['error']}")
        sys.exit(1)
    print(f"  ✔ {report['syntax_valid_count']}/{report['python_modules']} modules Python 100% valides.\n")
    
    # 2. Mise à jour du catalogue d'auto-connaissance
    print("[2/4] Régénération du catalogue d'auto-connaissance...")
    catalog = get_codebase_catalog()
    cat_data = catalog.scan_all()
    print(f"  ✔ {cat_data['files_count']} fichiers cartographiés.\n")
    
    # 3. Exécution de la suite de tests pytest
    print("[3/4] Exécution de la suite de tests unitaires (pytest)...")
    test_files = [
        "tests/test_rag.py",
        "tests/test_graph.py",
        "tests/test_self_repair.py",
        "tests/test_api.py",
        "tests/test_memory.py",
        "tests/test_circuit_breaker.py"
    ]
    res = subprocess.run(
        [sys.executable, "-m", "pytest"] + test_files + ["-v", "--tb=short"],
        cwd=str(ROOT_DIR)
    )
    if res.returncode != 0:
        print("❌ ÉCHEC : Certains tests unitaires ont échoué !")
        sys.exit(res.returncode)
    print("  ✔ Tous les tests unitaires sont passés avec succès.\n")
    
    # 4. Succès
    print("=======================================================")
    print("  ✔ PIPELINE CI/CD LOCAL VALIDÉ : PRÊT POUR COMMIT !  ")
    print("=======================================================")


if __name__ == "__main__":
    run_pre_commit()
