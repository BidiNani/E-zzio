from __future__ import annotations
import ast
import json
import sys
from pathlib import Path
from typing import Any, Dict, List

PROJECT_ROOT = Path(__file__).resolve().parents[1]
EXCLUDED_DIRS = {"audit", "snapshot", "snapshots", "backup", "backups", "old", "archive", ".venv", "venv", "__pycache__", ".pytest_cache", ".git", "tests"}

DECISION_KEYWORDS = {
    "selected_model", "preferred_model", "model =", "provider =", "provider_name =",
    "registry.get", "registry.resolve", "fabric.route", "fabric.select", 
    "router.route", "router.resolve", "build_fabric"
}

class DecisionPathVisitor(ast.NodeVisitor):
    def __init__(self, rel_path: str):
        self.rel_path = rel_path
        self.decisions_found: List[Dict[str, Any]] = []

    def visit_Assign(self, node: ast.Assign):
        target_str = ast.unparse(node.targets) if node.targets else ""
        if any(kw in target_str for kw in {"model", "provider", "route", "selected_model", "preferred_model"}):
            self.decisions_found.append({
                "file": self.rel_path,
                "line": node.lineno,
                "type": "ASSIGN",
                "code": ast.unparse(node)
            })
        self.generic_visit(node)

    def visit_Call(self, node: ast.Call):
        call_str = ast.unparse(node.func)
        if any(kw in call_str for kw in {"registry", "fabric", "router", "resolve", "route", "select", "build_fabric"}):
            self.decisions_found.append({
                "file": self.rel_path,
                "line": node.lineno,
                "type": "CALL",
                "code": ast.unparse(node)
            })
        self.generic_visit(node)

def main():
    print("=" * 80)
    print(" GATE v6.45.40 — AUTHORITY DECISION PATH FORENSICS")
    print("=" * 80)
    print(f"[RACINE] {PROJECT_ROOT}\n")

    py_files = [p for p in PROJECT_ROOT.glob("**/*.py") if not (set(p.parts) & EXCLUDED_DIRS)]
    all_decisions = []

    for path in py_files:
        rel_path = str(path.relative_to(PROJECT_ROOT))
        try:
            content = path.read_text(encoding="utf-8", errors="replace")
            tree = ast.parse(content, filename=rel_path)
            visitor = DecisionPathVisitor(rel_path)
            visitor.visit(tree)
            if visitor.decisions_found:
                all_decisions.extend(visitor.decisions_found)
        except Exception as e:
            print(f"[WARN] Erreur parsing {rel_path} : {e}", file=sys.stderr)

    print(f"[+] Points de décision / résolution détectés : {len(all_decisions)}")
    
    # Affichage d'un échantillon ciblé ou groupé par fichier clé
    key_files_summary: Dict[str, int] = {}
    for d in all_decisions:
        key_files_summary[d['file']] = key_files_summary.get(d['file'], 0) + 1

    print("\n[RÉSUMÉ PAR FICHIER CLÉ]")
    for file, count in sorted(key_files_summary.items(), key=lambda x: x[1], reverse=True)[:15]:
        print(f"  • {file}: {count} occurrences de décision/résolution")

    out_file = PROJECT_ROOT / "tools" / "gate_v6_45_40_report.json"
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(all_decisions, f, indent=2)
    print(f"\n[+] Rapport d'arbitrage JSON exporté : {out_file}")
    print("=" * 80)

if __name__ == "__main__":
    main()