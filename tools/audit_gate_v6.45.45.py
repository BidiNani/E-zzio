from __future__ import annotations
import ast
import json
import sys
from pathlib import Path
from typing import Any, Dict, List

PROJECT_ROOT = Path(__file__).resolve().parents[1]

TARGET_FILES = [
    "core/models/registry.py",
    "core/models/fabric.py",
    "core/models/lifecycle.py",
    "core/intents/fabric_connector.py"
]

def safe_unparse(node: ast.AST | None) -> str:
    if node is None:
        return "None"
    try:
        return ast.unparse(node)
    except Exception:
        return "<unparse_error>"

def inspect_file(rel_path: str) -> Dict[str, Any]:
    target_path = PROJECT_ROOT / rel_path
    if not target_path.exists():
        return {"error": "file_not_found"}

    try:
        content = target_path.read_text(encoding="utf-8", errors="replace")
        tree = ast.parse(content, filename=rel_path)
    except Exception as e:
        return {"error": f"ast_parse_error: {str(e)}"}

    classes_info: List[Dict[str, Any]] = []
    functions_info: List[Dict[str, Any]] = []

    for stmt in tree.body:
        if isinstance(stmt, ast.ClassDef):
            methods = []
            for item in stmt.body:
                if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    args_list = []
                    for a in item.args.args:
                        ann = f": {safe_unparse(a.annotation)}" if a.annotation else ""
                        args_list.append(f"{a.arg}{ann}")
                    
                    methods.append({
                        "name": item.name,
                        "line": item.lineno,
                        "is_async": isinstance(item, ast.AsyncFunctionDef),
                        "args": args_list,
                        "returns": safe_unparse(item.returns),
                        "docstring": (ast.get_docstring(item) or "").strip()
                    })
            classes_info.append({
                "name": stmt.name,
                "line": stmt.lineno,
                "docstring": (ast.get_docstring(stmt) or "").strip(),
                "methods": methods
            })
        elif isinstance(stmt, (ast.FunctionDef, ast.AsyncFunctionDef)):
            args_list = []
            for a in stmt.args.args:
                ann = f": {safe_unparse(a.annotation)}" if a.annotation else ""
                args_list.append(f"{a.arg}{ann}")
            functions_info.append({
                "name": stmt.name,
                "line": stmt.lineno,
                "is_async": isinstance(stmt, ast.AsyncFunctionDef),
                "args": args_list,
                "returns": safe_unparse(stmt.returns),
                "docstring": (ast.get_docstring(stmt) or "").strip()
            })

    return {
        "classes": classes_info,
        "functions": functions_info
    }

def main():
    print("=" * 80)
    print(" GATE v6.45.45 — ROBUST CONTRACT & RESOLUTION FORENSICS")
    print("=" * 80)
    print(f"[RACINE] {PROJECT_ROOT}\n")

    report: Dict[str, Any] = {}

    for rel_path in TARGET_FILES:
        data = inspect_file(rel_path)
        report[rel_path] = data

        print(f"\n📁 FICHIER : {rel_path}")
        if "error" in data:
            print(f"  ❌ Erreur : {data['error']}")
            continue

        for cls in data.get("classes", []):
            doc = f" — {cls['docstring'].splitlines()[0]}" if cls['docstring'] else ""
            print(f"  🏛️  CLASS {cls['name']} (ligne {cls['line']}){doc}")
            for m in cls["methods"]:
                prefix = "async " if m["is_async"] else ""
                args_str = ", ".join(m["args"])
                mdoc = f"\n        ↳ {m['docstring'].splitlines()[0]}" if m['docstring'] else ""
                print(f"      • {prefix}{m['name']}({args_str}) -> {m['returns']}{mdoc}")

        for fn in data.get("functions", []):
            prefix = "async " if fn["is_async"] else ""
            args_str = ", ".join(fn["args"])
            fdoc = f"\n        ↳ {fn['docstring'].splitlines()[0]}" if fn['docstring'] else ""
            print(f"  ⚙️  FUNCTION {prefix}{fn['name']}({args_str}) -> {fn['returns']}{fdoc}")

    out_file = PROJECT_ROOT / "tools" / "gate_v6_45_45_report.json"
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)
    print(f"\n[+] Rapport d'arbitrage JSON exporté : {out_file}")
    print("=" * 80)

if __name__ == "__main__":
    main()