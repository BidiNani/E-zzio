from __future__ import annotations

import ast
import json
import sys
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]

# Exclusion stricte des archives, snapshots et tests
EXCLUDED_DIRS = {
    "audit", "snapshot", "snapshots", "backup", "backups", "old", "archive",
    ".venv", "venv", "__pycache__", ".pytest_cache", ".git", "tests"
}

TARGET_FILES = {
    Path("core/integrations/discord/discord_client.py"),
    Path("runtime/bidi/presence.py"),
}

class RecursiveDiscordTraceVisitor(ast.NodeVisitor):
    def __init__(self, filepath: Path, rel_path: str, full_tree: ast.AST):
        self.filepath = filepath
        self.rel_path = rel_path
        self.full_tree = full_tree
        self.visited_functions: set[str] = set()
        self.chain_log: list[dict[str, Any]] = []

        # Indexation globale de toutes les fonctions et méthodes du fichier pour résolution récursive
        self.function_registry: dict[str, ast.FunctionDef | ast.AsyncFunctionDef] = {}
        for node in ast.walk(full_tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                self.function_registry[node.name] = node

    def trace_function(self, func_node: ast.FunctionDef | ast.AsyncFunctionDef, depth: int = 0):
        if depth > 5 or func_node.name in self.visited_functions:
            return
        self.visited_functions.add(func_node.name)

        calls_in_func = []
        for child in ast.walk(func_node):
            if isinstance(child, ast.Call):
                call_name = ast.unparse(child.func)
                args = [ast.unparse(a) for a in child.args]
                calls_in_func.append({"call": call_name, "args": args, "line": child.lineno})

                # Résolution récursive si la fonction appelée est définie dans le même fichier
                base_name = call_name.split(".")[-1]
                if base_name in self.function_registry and base_name not in self.visited_functions:
                    self.trace_function(self.function_registry[base_name], depth + 1)

        self.chain_log.append({
            "file": self.rel_path,
            "function": func_node.name,
            "depth": depth,
            "line": func_node.lineno,
            "calls": calls_in_func
        })

def main():
    print("=" * 80)
    print(" GATE v6.45.32 — DISCORD RECURSIVE HANDLER & BACKEND TRACE")
    print("=" * 80)
    print(f"[RACINE] {PROJECT_ROOT}\n")

    all_traces = []

    for target_rel in TARGET_FILES:
        full_path = PROJECT_ROOT / target_rel
        if not full_path.exists():
            print(f"[-] Fichier cible absent : {target_rel}")
            continue

        rel_path = str(target_rel)
        print(f"[+] Analyse récursive de : {rel_path}")

        try:
            content = full_path.read_text(encoding="utf-8", errors="replace")
            tree = ast.parse(content, filename=rel_path)

            visitor = RecursiveDiscordTraceVisitor(full_path, rel_path, tree)

            # Lancement des traces à partir des points d'entrée connus
            for node in ast.walk(tree):
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    if node.name in {"on_message", "slash_ezzio", "slash_status", "setup_hook", "on_ready"}:
                        visitor.trace_function(node, depth=0)

            all_traces.extend(visitor.chain_log)
        except Exception as e:
            print(f"[WARN] Erreur d'analyse sur {rel_path} : {e}", file=sys.stderr)

    print(f"\n[1] RÉSULTATS DE LA CHAÎNE RÉCURSIVE ({len(all_traces)} contextes analysés)\n")
    for trace in all_traces:
        print(f"  • [{trace['file']}] def {trace['function']}() (ligne {trace['line']}, niveau {trace['depth']})")
        for c in trace["calls"]:
            print(f"    -> Appel : `{c['call']}({', '.join(c['args'])})` (ligne {c['line']})")
        print()

    # Sauvegarde du rapport JSON
    out_file = PROJECT_ROOT / "tools" / "gate_v6_45_32_report.json"
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(all_traces, f, indent=2)
    print(f"[+] Rapport JSON de traçage exporté : {out_file}")
    print("=" * 80)

if __name__ == "__main__":
    main()
