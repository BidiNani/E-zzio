import os
import ast
import json
from pathlib import Path
from collections import defaultdict

ROOT_DIR = Path("G:/AI/E-zzio").resolve()
REGISTRY_OUT = ROOT_DIR / "runtime" / "audit" / "intelligence_scan" / "V7_REGISTRY"

# Définit la hiérarchie autorisée (Top-Down)
# core -> governance -> runtime -> sandbox
DOMAIN_HIERARCHY = {
    "core": ["governance", "sandbox"],
    "governance": ["runtime", "sandbox"],
    "runtime": ["sandbox"],
    "sandbox": []
}

def get_domain(file_path: Path):
    parts = file_path.relative_to(ROOT_DIR).parts
    if "core" in parts: return "core"
    if "governance" in parts: return "governance"
    if "runtime" in parts: return "runtime"
    if "sandbox" in parts: return "sandbox"
    return "other"

def analyze_dependencies():
    print("[*] Démarrage de V7.11.0.4 — Domain Isolation Audit...")
    graph = defaultdict(set)
    violations = []

    for py_file in ROOT_DIR.rglob("*.py"):
        if any(ex in py_file.parts for ex in {".git", "venv", "audit"}): continue
        
        source_domain = get_domain(py_file)
        if source_domain == "other": continue

        try:
            content = py_file.read_text(encoding="utf-8", errors="replace")
            tree = ast.parse(content, filename=str(py_file))
            for node in ast.walk(tree):
                if isinstance(node, (ast.Import, ast.ImportFrom)):
                    module_name = ""
                    if isinstance(node, ast.ImportFrom): module_name = node.module or ""
                    
                    # Vérifier si l'import pointe vers un domaine interne
                    for domain in ["core", "governance", "runtime", "sandbox"]:
                        if domain in module_name:
                            graph[source_domain].add(domain)
                            # Audit de violation
                            if domain in DOMAIN_HIERARCHY.get(source_domain, []):
                                continue # Allowed
                            elif domain != source_domain:
                                violations.append({
                                    "file": str(py_file.relative_to(ROOT_DIR)),
                                    "source": source_domain,
                                    "target": domain,
                                    "type": "FORBIDDEN_CROSSING"
                                })
        except: pass
    
    return graph, violations

def run_dep_analysis():
    graph, violations = analyze_dependencies()
    
    # Sérialisation simple pour JSON
    serial_graph = {k: list(v) for k, v in graph.items()}
    
    payload = {
        "dependency_graph": serial_graph,
        "isolation_violations": violations
    }
    
    (REGISTRY_OUT / "dependency_graph.json").write_text(json.dumps(payload, indent=2))
    
    # Markdown
    md_path = REGISTRY_OUT / "V7_11_0_4_DEPENDENCY_REPORT.md"
    lines = ["# E-ZZIO V7.11.0.4 — Dependency & Isolation Report", ""]
    lines.append("## 1. Violations d'Isolation de Domaine")
    for v in violations:
        lines.append(f"- 🔴 `{v['file']}` : `{v['source']}` -> `{v['target']}`")
    
    if not violations:
        lines.append("✅ Aucune violation de hiérarchie détectée.")
        
    lines.extend(["", "## 2. Graphe de dépendances (DOMAINS)", ""])
    for src, targets in serial_graph.items():
        lines.append(f"- `{src}` appelle -> `{targets}`")
        
    md_path.write_text("\n".join(lines), encoding="utf-8")
    print(f"[OK] Audit terminé. Rapport : {md_path}")

if __name__ == "__main__":
    run_dep_analysis()
