import os
import sys
import json
import ast
import re
from pathlib import Path
from datetime import datetime

ROOT_DIR = Path("G:/AI/E-zzio").resolve()
REGISTRY_OUT = ROOT_DIR / "runtime" / "audit" / "intelligence_scan" / "V7_REGISTRY"
REGISTRY_OUT.mkdir(parents=True, exist_ok=True)

def analyze_architecture():
    print("[*] Démarrage de V7.11.0.2 — Full Architecture Discovery...")
    
    inventory = {"folders": 0, "files": 0, "extensions": {}, "obsolete": []}
    dependencies = {"imports": {}, "circular_risks": []}
    tech_debt = {"todo": 0, "fixme": 0, "pass": 0}
    secrets_potential = []
    contracts = []

    for path in ROOT_DIR.rglob("*"):
        if any(ex in path.parts for ex in {".git", "__pycache__", "venv", "node_modules", "runtime/audit"}):
            continue
        
        if path.is_dir():
            inventory["folders"] += 1
            continue
        
        inventory["files"] += 1
        ext = path.suffix
        inventory["extensions"][ext] = inventory["extensions"].get(ext, 0) + 1

        try:
            content = path.read_text(encoding="utf-8", errors="replace")
            
            # Debt
            tech_debt["todo"] += content.lower().count("todo")
            tech_debt["fixme"] += content.lower().count("fixme")
            tech_debt["pass"] += content.count("pass")

            # Secrets (basique)
            if any(k in content.lower() for k in ["api_key", "secret", "token", "password"]):
                secrets_potential.append(str(path.relative_to(ROOT_DIR)))

            # Contracts
            if "contract.json" in path.name:
                contracts.append(str(path.relative_to(ROOT_DIR)))

            # Python Dependencies
            if path.suffix == ".py":
                tree = ast.parse(content, filename=str(path))
                for node in ast.walk(tree):
                    if isinstance(node, ast.Import):
                        for n in node.names:
                            dependencies["imports"][n.name] = dependencies["imports"].get(n.name, 0) + 1
                    elif isinstance(node, ast.ImportFrom):
                        if node.module:
                            dependencies["imports"][node.module] = dependencies["imports"].get(node.module, 0) + 1
        except:
            pass

    report = {
        "timestamp": datetime.now().isoformat(),
        "inventory": inventory,
        "tech_debt": tech_debt,
        "secrets_risk": secrets_potential[:20],
        "contracts_detected": contracts,
        "top_dependencies": sorted(dependencies["imports"].items(), key=lambda x: x[1], reverse=True)[:20]
    }

    out_json = REGISTRY_OUT / "architecture_discovery_report.json"
    out_json.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    
    # Génération Markdown
    md_path = REGISTRY_OUT / "V7_11_0_2_FULL_ARCHITECTURE_REPORT.md"
    lines = [
        "# E-ZZIO V7.11.0.2 — Full Architecture Discovery Report",
        f"**Date :** {report['timestamp']}",
        "",
        "## 1. Inventaire",
        f"- **Dossiers :** {inventory['folders']}",
        f"- **Fichiers :** {inventory['files']}",
        "",
        "## 2. Dette Technique",
        f"- **TODOs :** {tech_debt['todo']}",
        f"- **FIXMEs :** {tech_debt['fixme']}",
        f"- **'pass' statiques :** {tech_debt['pass']}",
        "",
        "## 3. Contrats détectés",
        *[f"- `{c}`" for c in contracts],
        "",
        "## 4. Top Dépendances Python",
        *[f"- `{k}` (utilisé {v} fois)" for k, v in report['top_dependencies']],
        "",
        "## 5. Risques Sécurité (Secrets potentiels)",
        *[f"- `{s}`" for s in report['secrets_risk']]
    ]
    md_path.write_text("\n".join(lines), encoding="utf-8")
    print(f"[OK] Audit terminé. Rapport : {md_path}")

if __name__ == "__main__":
    analyze_architecture()
