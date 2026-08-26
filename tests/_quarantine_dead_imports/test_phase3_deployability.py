import pytest
import os
from pathlib import Path
from core.secrets import load_secrets, get_secrets_path
from interfaces.api.server import app

def test_deployability_secrets_path_resolution():
    secrets_file = get_secrets_path()
    assert isinstance(secrets_file, Path)
    # Le chemin doit être résolu relativement à la racine du projet
    assert secrets_file.name == ".env"
    assert secrets_file.parent.name == "secrets"

def test_deployability_no_hardcoded_user_absolute_paths():
    # Vérification que le code actif ne contient pas de chemin dur 'C:\Users\...'
    root = Path(__file__).resolve().parent.parent
    active_dirs = ["core", "routers", "interfaces", "runtime/core"]
    
    violations = []
    for d in active_dirs:
        target_dir = root / d
        if not target_dir.exists():
            continue
        for py_file in target_dir.rglob("*.py"):
            text = py_file.read_text(encoding="utf-8", errors="ignore")
            if "C:\\Users\\" in text or "/home/" in text:
                violations.append(str(py_file.relative_to(root)))
                
    assert len(violations) == 0, f"Chemins absolus en dur détectés dans : {violations}"

def test_deployability_api_lifespan_contract():
    # L'application FastAPI doit être instanciable sans erreur
    assert app.title == "E-ZZIO OS API"
    assert len(app.routes) > 5
