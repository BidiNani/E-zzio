import os
import ast
import json
from pathlib import Path

ROOT_DIR = Path("G:/AI/E-zzio").resolve()
REGISTRY_OUT = ROOT_DIR / "runtime" / "audit" / "intelligence_scan" / "V7_REGISTRY" / "V7_11_0_5_ISOLATION_MAP"
REGISTRY_OUT.mkdir(parents=True, exist_ok=True)

DOMAIN_HIERARCHY = {
    "core": ["contracts", "governance"],
    "governance": ["contracts", "runtime"],
    "runtime": ["contracts", "sandbox"],
    "sandbox": [],
    "contracts": []
}

def get_domain(file_path: Path):
    parts = file_path.relative_to(ROOT_DIR).parts
    for domain in DOMAIN_HIERARCHY.keys():
        if domain in parts: return domain
    return None

def analyze_refactoring():
    print("[*] Génération de la carte de refactoring V7.11.0.5...")
    violations = []
    
    for py_file in ROOT_DIR.rglob("*.py"):
        if any(ex in py_file.parts for ex in {".git", "venv", "audit"}): continue
        
        src_domain = get_domain(py_file)
        if not src_domain: continue

        try:
            tree = ast.parse(py_file.read_text(encoding="utf-8", errors="replace"))
            for node in ast.walk(tree):
                if isinstance(node, (ast.Import, ast.ImportFrom)):
                    module = node.module if isinstance(node, ast.ImportFrom) else ""
                    # Vérifier si l'import pointe vers un domaine différent
                    for target_domain in DOMAIN_HIERARCHY.keys():
                        if target_domain in module and target_domain != src_domain:
                            # Vérification hiérarchique
                            if target_domain not in DOMAIN_HIERARCHY.get(src_domain, []):
                                severity = "HIGH" if src_domain in ["core", "runtime"] and target_domain in ["core", "runtime"] else "MEDIUM"
                                violations.append({
                                    "source": str(py_file.relative_to(ROOT_DIR)),
                                    "source_domain": src_domain,
                                    "target_domain": target_domain,
                                    "import": module,
                                    "severity": severity,
                                    "suggestion": f"Replace direct import with runtime.contracts.{target_domain}_contract"
                                })
        except: pass
    return violations

def run_mapping():
    violations = analyze_refactoring()
    
    # JSON Map
    (REGISTRY_OUT / "refactoring_map.json").write_text(json.dumps(violations, indent=2))
    
    # Markdown Report
    md_path = REGISTRY_OUT / "V7_11_0_5_REFACTORING_MAP_REPORT.md"
    lines = ["# V7.11.0.5 — Isolation Refactoring Map", ""]
    for v in violations:
        lines.append(f"### 🔴 Violation {v['severity']} : `{v['source']}`")
        lines.append(f"- **Import interdit :** `{v['import']}` ({v['source_domain']} -> {v['target_domain']})")
        lines.append(f"- **Suggestion :** `{v['suggestion']}`")
        lines.append("")
        
    md_path.write_text("\n".join(lines), encoding="utf-8")
    print(f"[OK] Carte générée : {md_path}")

if __name__ == "__main__":
    run_mapping()
