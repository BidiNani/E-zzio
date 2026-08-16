import json
import ast
import sys
from pathlib import Path

ROOT_PATH = Path(r"G:\AI\E-zzio")
CLASSIFICATION_PATH = ROOT_PATH / "runtime" / "audit" / "reliability" / "classification_v4.json"
MATRIX_OUTPUT = ROOT_PATH / "runtime" / "audit" / "reliability" / "runtime_failure_matrix.json"

if not CLASSIFICATION_PATH.exists():
    print(f"[!] Fichier introuvable : {CLASSIFICATION_PATH}")
    sys.exit(1)

items = json.loads(CLASSIFICATION_PATH.read_text(encoding="utf-8"))
prod_items = [i for i in items if i.get("category") == "REAL_RUNTIME_FAILURE"]

matrix = []

for item in prod_items:
    src_rel = item["source"]
    ref_mod = item["reference"]
    src_path = ROOT_PATH / src_rel

    if not src_path.exists():
        continue

    try:
        content = src_path.read_text(encoding="utf-8", errors="ignore")
        tree = ast.parse(content, filename=str(src_path))
    except Exception:
        continue

    symbols = []
    line_no = None

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name == ref_mod or alias.name.startswith(ref_mod + "."):
                    symbols.append(alias.asname or alias.name)
                    if line_no is None and hasattr(node, "lineno"):
                        line_no = node.lineno
        elif isinstance(node, ast.ImportFrom):
            if node.module and (node.module == ref_mod or node.module.startswith(ref_mod)):
                for alias in node.names:
                    symbols.append(alias.name)
                if line_no is None and hasattr(node, "lineno"):
                    line_no = node.lineno

    # Catégorisation fonctionnelle et évaluation de sévérité
    if ref_mod.startswith("runtime.security"):
        category = "SECURITY"
        severity = "CRITICAL"
    elif ref_mod.startswith("runtime.audit") or "observability" in ref_mod:
        category = "AUDIT_OBSERVABILITY"
        severity = "CRITICAL" if ("kernel" in src_rel or "microkernel" in src_rel) else "HIGH"
    elif "memory" in ref_mod or "skill" in ref_mod or "index_api" in ref_mod:
        category = "MEMORY_SKILLS"
        severity = "HIGH"
    else:
        category = "HARDWARE_EXPERIMENTAL"
        severity = "MEDIUM"

    matrix.append({
        "module_missing": ref_mod,
        "imported_by": src_rel,
        "line_number": line_no,
        "symbols_imported": sorted(list(set(symbols))),
        "category": category,
        "severity": severity
    })

MATRIX_OUTPUT.write_text(json.dumps(matrix, indent=2), encoding="utf-8")

print(f"[*] Analyse forensic terminée : {len(matrix)} éléments analysés.")
print(f"[OK] Matrice exportée dans : {MATRIX_OUTPUT}")
