import os
import sys
import json
import ast
import re
from pathlib import Path

ROOT_DIR = Path("G:/AI/E-zzio").resolve()
OUTPUT_DIR = ROOT_DIR / "runtime" / "audit" / "intelligence_scan"

def scan_dynamic_imports():
    """Détecte les usages d'import dynamique (importlib, __import__, exec, etc.)."""
    dynamic_findings = []
    for py_file in ROOT_DIR.rglob("*.py"):
        if any(ex in py_file.parts for ex in {".git", "__pycache__", "venv", "node_modules", "runtime/audit"}):
            continue
        try:
            content = py_file.read_text(encoding="utf-8", errors="replace")
            rel_path = str(py_file.relative_to(ROOT_DIR)).replace("\\", "/")
            
            if re.search(r'\b(importlib|__import__|exec|eval)\b', content):
                # Extraction des lignes concernées
                lines = [line.strip() for line in content.splitlines() if any(k in line for k in ["importlib", "__import__", "exec", "eval"])]
                dynamic_findings.append({
                    "path": rel_path,
                    "matches": lines
                })
        except Exception:
            pass
    return dynamic_findings

def inspect_runtime_core():
    """Liste les composants de runtime/core/ pour clarifier sa responsabilité."""
    runtime_core_dir = ROOT_DIR / "runtime" / "core"
    components = []
    if runtime_core_dir.exists():
        for p in runtime_core_dir.rglob("*.py"):
            components.append(str(p.relative_to(ROOT_DIR)).replace("\\", "/"))
    return components

def inspect_model_registry_code():
    """Vérifie si core/model_registry.py référence des contrats ou uniquement du JSON de latence."""
    reg_file = ROOT_DIR / "core" / "model_registry.py"
    if not reg_file.exists():
        return {"error": "core/model_registry.py introuvable"}
    
    content = reg_file.read_text(encoding="utf-8", errors="replace")
    return {
        "mentions_contracts": "contract" in content.lower(),
        "mentions_hmac": "hmac" in content.lower() or "signature" in content.lower(),
        "mentions_latency_json": "model_latency.json" in content,
        "content_lines": len(content.splitlines())
    }

def run_targeted_autopsy():
    print("[*] Lancement de l'autopsie ciblée V7.3...")
    
    dynamic_imports = scan_dynamic_imports()
    runtime_core_files = inspect_runtime_core()
    registry_inspection = inspect_model_registry_code()

    payload = {
        "dynamic_imports": dynamic_imports,
        "runtime_core_files": runtime_core_files,
        "model_registry_inspection": registry_inspection
    }

    out_file = OUTPUT_DIR / "V7_TARGETED_AUTOPSY.json"
    out_file.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")

    # Génération du résumé Markdown
    summary_path = OUTPUT_DIR / "V7_TARGETED_AUTOPSY_SUMMARY.md"
    lines = [
        "# E-ZZIO V7.3 — Rapport d'Autopsie Ciblée",
        "",
        "## 1. Analyse du Double Core (`core/` vs `runtime/core/`)",
        f"- **Fichiers dans `runtime/core/` :** {len(runtime_core_files)} fichiers",
    ]
    for f in runtime_core_files:
        lines.append(f"  - `{f}`")
    
    lines.extend([
        "",
        "## 2. État Réel de `core/model_registry.py`",
        f"- **Lit le JSON de latence (`model_latency.json`) :** {registry_inspection.get('mentions_latency_json', False)}",
        f"- **Intègre les Contrats Signés (`contract` / `hmac`) :** {registry_inspection.get('mentions_contracts', False)} (HMAC: {registry_inspection.get('mentions_hmac', False)})",
        "",
        "## 3. Détection des Imports Dynamiques et Code Évolutif",
        f"- **Modules utilisant importlib/exec/eval :** {len(dynamic_imports)} fichiers",
    ])
    for d in dynamic_imports:
        lines.append(f"  - `{d['path']}` : {d['matches']}")

    summary_path.write_text("\n".join(lines), encoding="utf-8")
    print(f"[OK] Rapport d'autopsie ciblée enregistré dans {summary_path}")

if __name__ == "__main__":
    run_targeted_autopsy()
