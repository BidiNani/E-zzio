import os
import sys
import json
import ast
from pathlib import Path
from datetime import datetime

ROOT_DIR = Path("G:/AI/E-zzio").resolve()
REGISTRY_OUT = ROOT_DIR / "runtime" / "audit" / "intelligence_scan" / "V7_REGISTRY"
REGISTRY_OUT.mkdir(parents=True, exist_ok=True)

def deep_scan_emission_chains():
    """Analyse l'AST de tous les modules pour repérer l'utilisation active de ContractSigner et l'écriture de contrats."""
    emission_findings = []
    
    for py_file in ROOT_DIR.rglob("*.py"):
        rel_parts = py_file.relative_to(ROOT_DIR).parts
        if any(ex in rel_parts for ex in {".git", "__pycache__", "venv", "node_modules", "runtime/audit"}):
            continue
            
        try:
            content = py_file.read_text(encoding="utf-8", errors="replace")
            if "ContractSigner" not in content and "contract.json" not in content.lower():
                continue

            rel_path = str(py_file.relative_to(ROOT_DIR)).replace("\\", "/")
            file_evidence = {
                "file_path": rel_path,
                "instantiations": [],
                "method_calls": [],
                "file_writes": []
            }

            tree = ast.parse(content, filename=rel_path)
            for node in ast.walk(tree):
                # Détection des instanciations de classes (ex: ContractSigner(...))
                if isinstance(node, ast.Call):
                    func_name = ""
                    if isinstance(node.func, ast.Name):
                        func_name = node.func.id
                    elif isinstance(node.func, ast.Attribute):
                        func_name = node.func.attr

                    if "ContractSigner" in func_name or "Signer" in func_name:
                        args_repr = [ast.unparse(arg) for arg in node.args]
                        file_evidence["instantiations"].append({
                            "class_or_func": func_name,
                            "arguments": args_repr,
                            "lineno": node.lineno
                        })
                    elif "sign" in func_name.lower() or "write" in func_name.lower():
                        file_evidence["method_calls"].append({
                            "method": func_name,
                            "lineno": node.lineno
                        })

            # Ajout si des indices pertinents ont été trouvés
            if file_evidence["instantiations"] or file_evidence["method_calls"]:
                emission_findings.append(file_evidence)

        except Exception as e:
            pass
            
    return emission_findings

def run_emission_trace():
    print("[*] Démarrage de V7.10.1 — Contract Emission Chain Trace...")
    
    findings = deep_scan_emission_chains()

    payload = {
        "timestamp": datetime.now().isoformat(),
        "emission_chains_discovered": findings
    }

    out_json = REGISTRY_OUT / "contract_emission_chain.json"
    out_json.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")

    build_markdown(payload)
    print(f"[OK] V7.10.1 Emission Chain Trace terminé. Rapport enregistré dans {REGISTRY_OUT}")

def build_markdown(res: dict):
    md_path = REGISTRY_OUT / "V7_10_1_CONTRACT_EMISSION_CHAIN_REPORT.md"
    findings = res.get("emission_chains_discovered", [])

    lines = [
        "# E-ZZIO V7.10.1 — Contract Emission Chain Report",
        f"**Date :** {res.get('timestamp')}",
        "",
        "## 1. Analyse des Chaînes d'Instanciation et d'Émission",
        f"**Modules impliquant ContractSigner ou des méthodes de signature :** {len(findings)}",
        ""
    ]

    for f in findings:
        lines.append(f"### Fichier : `{f['file_path']}`")
        if f['instantiations']:
            lines.append("  - **Instanciations / Appels ciblés :**")
            for inst in f['instantiations']:
                lines.append(f"    - Ligne {inst['lineno']} : `{inst['class_or_func']}(args={inst['arguments']})`")
        if f['method_calls']:
            lines.append("  - **Méthodes détectées :**")
            for meth in f['method_calls']:
                lines.append(f"    - Ligne {meth['lineno']} : `{meth['method']}`")
        lines.append("")

    lines.extend([
        "",
        "## 2. Statut de la Migration Trust",
        "**MIGRATION BLOQUÉE :** Cet audit complète la cartographie des appelants. Tant que le contexte exact d'écriture du fichier `qwen2.5-7b.contract.json` n'est pas formellement relié à un flux d'exécution traçable, aucune altération de la Trust Layer n'est permise."
    ])

    md_path.write_text("\n".join(lines), encoding="utf-8")
    print(f"[OK] Rapport Markdown d'émission généré : {md_path}")

if __name__ == "__main__":
    run_emission_trace()
