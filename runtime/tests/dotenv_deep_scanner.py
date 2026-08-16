import ast
import json
from pathlib import Path

root_dir = Path("G:/AI/E-zzio")
report_path = root_dir / "runtime" / "tests" / "reports" / "core_dependency_matrix.json"

if not report_path.exists():
    print('{"error": "Report introuvable."}')
    exit(1)

with open(report_path, "r", encoding="utf-8") as f:
    matrix = json.load(f)

dotenv_files = matrix.get("dependency_matrix", {}).get("dotenv", {}).get("used_by", [])

results = {}

for rel_path in dotenv_files:
    file_path = root_dir / rel_path
    if not file_path.exists():
        continue
        
    content = file_path.read_text(encoding="utf-8")
    try:
        tree = ast.parse(content)
    except Exception:
        continue

    import_styles = []
    usages = set()

    for node in ast.walk(tree):
        # Détection des styles d'import
        if isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name.split('.')[0] == "dotenv":
                    import_styles.append(f"import {alias.name}")
        elif isinstance(node, ast.ImportFrom):
            if node.module and node.module.split('.')[0] == "dotenv":
                names = ", ".join([a.name for a in node.names])
                import_styles.append(f"from {node.module} import {names}")
        
        # Détection de l'utilisation (les appels de fonctions)
        elif isinstance(node, ast.Call):
            if isinstance(node.func, ast.Name):
                if node.func.id in ["load_dotenv", "dotenv_values", "find_dotenv"]:
                    usages.add(f"{node.func.id}()")
            elif isinstance(node.func, ast.Attribute):
                if node.func.attr in ["load_dotenv", "dotenv_values", "find_dotenv"]:
                    caller = node.func.value.id if hasattr(node.func.value, 'id') else "unknown"
                    usages.add(f"{caller}.{node.func.attr}()")

    results[rel_path] = {
        "import_style": list(set(import_styles)),
        "usage": list(usages)
    }

output = {
    "dotenv_consumers_audit": {
        "total": len(results),
        "files": results
    }
}

print(json.dumps(output, indent=2, ensure_ascii=False))
