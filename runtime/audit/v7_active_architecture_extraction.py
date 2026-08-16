import os
import ast
import json
from pathlib import Path

ROOT_DIR = Path("G:/AI/E-zzio").resolve()
REGISTRY_IN = ROOT_DIR / "runtime" / "audit" / "intelligence_scan" / "V7_REGISTRY"
REGISTRY_OUT = REGISTRY_IN / "V7_11_0_7_ACTIVE_ARCH"
REGISTRY_OUT.mkdir(parents=True, exist_ok=True)

def extract_active_info():
    print("[*] Extraction de l'Architecture Active...")
    
    # 1. Charger la Baseline
    baseline = json.loads((REGISTRY_IN / "architecture_baseline.json").read_text())
    active_files = [Path(ROOT_DIR / f) for f in baseline["ACTIVE"]]
    
    # 2. Détection Points d'Entrée
    entry_points = []
    # 3. Graphe de dépendances restreint
    graph = {}
    
    entry_patterns = ["if __name__ == \"__main__\":", "FastAPI(", "uvicorn", "run(", "start("]

    for py_file in active_files:
        if py_file.suffix != ".py": continue
        try:
            content = py_file.read_text(encoding="utf-8", errors="replace")
            
            # Entry points
            for pat in entry_patterns:
                if pat in content:
                    entry_points.append({"file": str(py_file.relative_to(ROOT_DIR)), "pattern": pat})
            
            # Domain mapping
            tree = ast.parse(content)
            imports = []
            for node in ast.walk(tree):
                if isinstance(node, (ast.Import, ast.ImportFrom)):
                    mod = node.module if isinstance(node, ast.ImportFrom) else ""
                    imports.append(mod)
            graph[str(py_file.relative_to(ROOT_DIR))] = imports
            
        except: pass

    # Sauvegarde résultats
    report = {"entry_points": entry_points, "dependency_map": graph}
    (REGISTRY_OUT / "active_architecture_map.json").write_text(json.dumps(report, indent=2))
    
    # Markdown
    md_path = REGISTRY_OUT / "V7_11_0_7_ACTIVE_ARCH_REPORT.md"
    lines = ["# V7.11.0.7 — Active Architecture Extraction", ""]
    lines.append("## 1. Points d'Entrée Actifs (Entry Points)")
    for ep in entry_points: lines.append(f"- `{ep['file']}` (détecté via `{ep['pattern']}`)")
    
    lines.append("\n## 2. Dépendances Active Code (Nœuds critiques)")
    # Simplification : montrer juste les liens inter-domaines
    for f, imps in graph.items():
        if any("runtime" in i or "core" in i for i in imps):
            lines.append(f"- `{f}` -> {imps}")

    md_path.write_text("\n".join(lines), encoding="utf-8")
    print(f"[OK] Extraction active terminée : {md_path}")

if __name__ == "__main__":
    extract_active_info()
