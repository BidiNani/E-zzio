from __future__ import annotations
import ast
import json
import os
import sys
from pathlib import Path
from typing import Any, Dict, List

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

def scan_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8", errors="replace")
    except Exception:
        return ""

def main():
    print("=" * 80)
    print(" RECONCILIATION CANONIQUE — PASSE UNIQUE D'INVENTAIRE")
    print("=" * 80)
    print(f"[RACINE] {PROJECT_ROOT}\n")

    report: Dict[str, Any] = {
        "gemini_rotation": [],
        "ollama_local_models": [],
        "secrets_vault": [],
        "kernel_routing": []
    }

    # 1. Recherche des mécanismes Gemini & Rotation de clés
    py_files = [p for p in PROJECT_ROOT.glob("**/*.py") if not any(x in p.parts for x in {".venv", "venv", ".git", "__pycache__", "snapshots", "backup", "backups"})]
    
    for p in py_files:
        rel = str(p.relative_to(PROJECT_ROOT))
        content = scan_text(p)
        
        # Détection Gemini / Key Rotation
        if any(k in content for k in {"GEMINI_API_KEY", "GeminiProvider", "key_rotation", "rotate_key", "api_key_rotator", "gemini-2.5"}):
            report["gemini_rotation"].append(rel)
            
        # Détection Granite / Ornith
        if any(k in content.lower() for k in {"granite", "ornith", "qwen3-coder", "gpt-oss-20b"}):
            report["ollama_local_models"].append(rel)
            
        # Détection Secrets / Vault / Keyring
        if any(k in content for k in {"SecretStore", "Vault", "KeyManager", "get_secret", "load_dotenv"}):
            report["secrets_vault"].append(rel)

    print("[1] MODULES LIÉS À GEMINI ET ROTATION DE CLÉS :")
    for r in sorted(set(report["gemini_rotation"]))[:15]:
        print(f"  • {r}")

    print("\n[2] MODULES RÉFÉRENÇANT LES MODÈLES LOCAUX (GRANITE / ORNITH) :")
    for r in sorted(set(report["ollama_local_models"]))[:15]:
        print(f"  • {r}")

    print("\n[3] GESTION DES SECRETS & CLÉS D'AUTHENTIFICATION :")
    for r in sorted(set(report["secrets_vault"]))[:15]:
        print(f"  • {r}")

    # Export pour réconciliation formelle
    out_file = PROJECT_ROOT / "tools" / "canonical_reconciliation_inventory.json"
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)

    print(f"\n[+] Rapport d'inventaire complet exporté : {out_file}")
    print("=" * 80)

if __name__ == "__main__":
    main()