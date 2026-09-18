from __future__ import annotations

import ast
import json
import sys
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]

EXCLUDED_DIRS = {".venv", "venv", "__pycache__", ".pytest_cache", ".git", "tests"}

TARGET_OBJECTS = {
    "EzzioMaster",
    "CognitiveGateway",
    "CodingAgentHarness",
    "AgentProviderAdapter",
    "IntentFabricConnector",
    "build_fabric",
    "AutonomousModelFabric",
    "_build_canonical_router",
}

DISCORD_DECORATORS = {"event", "command", "hybrid_command", "task"}
DISCORD_FUNCTIONS = {"on_message", "on_interaction", "setup_hook", "on_ready", "process_commands", "invoke"}
METHOD_CALLS_OF_INTEREST = {"process", "ask", "run", "chat", "generate", "generate_content", "complete", "predict", "invoke"}

class DiscordForensicVisitor(ast.NodeVisitor):
    def __init__(self, filepath: Path, rel_path: str):
        self.filepath = filepath
        self.rel_path = rel_path
        self.imports: dict[str, str] = {}
        self.global_vars: dict[str, str] = {}
        self.detected_handlers: list[dict[str, Any]] = []
        self.current_scope: list[str] = []
        self.current_args: set[str] = set()
        self.instantiations: dict[str, str] = {}

    def visit_Import(self, node: ast.Import):
        for alias in node.names:
            name = alias.asname or alias.name
            self.imports[name] = alias.name
        self.generic_visit(node)

    def visit_ImportFrom(self, node: ast.ImportFrom):
        mod = node.module or ""
        for alias in node.names:
            name = alias.asname or alias.name
            self.imports[name] = f"{mod}.{alias.name}"
        self.generic_visit(node)

    def visit_Assign(self, node: ast.Assign):
        assigned_type = None
        if isinstance(node.value, ast.Call):
            if isinstance(node.value.func, ast.Name):
                assigned_type = node.value.func.id
            elif isinstance(node.value.func, ast.Attribute):
                assigned_type = node.value.func.attr

        for target in node.targets:
            if isinstance(target, ast.Name):
                if assigned_type:
                    self.instantiations[target.id] = assigned_type
                if not self.current_scope:
                    self.global_vars[target.id] = assigned_type or "EXPRESSION"
        self.generic_visit(node)

    def _qualify_provenance(self, var_name: str) -> str:
        if var_name in self.current_args:
            return "INJECTED"
        if var_name in self.instantiations:
            return "CREATED"
        if var_name in self.imports:
            return "IMPORTED"
        if var_name in self.global_vars:
            return "GLOBAL"
        if var_name.startswith("self.") or var_name.startswith("bot.") or var_name.startswith("ctx."):
            return "ATTRIBUTE"
        return "UNKNOWN"

    def _is_discord_decorator(self, decorator: ast.AST) -> bool:
        if isinstance(decorator, ast.Name):
            return decorator.id in DISCORD_DECORATORS
        if isinstance(decorator, ast.Attribute):
            return decorator.attr in DISCORD_DECORATORS or decorator.attr in ("command", "event")
        if isinstance(decorator, ast.Call):
            return self._is_discord_decorator(decorator.func)
        return False

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef):
        self._inspect_function(node)

    def visit_FunctionDef(self, node: ast.FunctionDef):
        self._inspect_function(node)

    def _inspect_function(self, node: Any):
        is_discord_hook = node.name in DISCORD_FUNCTIONS
        has_decorator = any(self._is_discord_decorator(dec) for dec in node.decorator_list)

        if is_discord_hook or has_decorator:
            handler_info = {
                "file": self.rel_path,
                "function": node.name,
                "line": node.lineno,
                "is_hook": is_discord_hook,
                "decorators": [ast.unparse(d) for d in node.decorator_list],
                "args": [arg.arg for arg in node.args.args],
                "downstream_calls": [],
                "target_interactions": [],
            }

            self.current_scope.append(node.name)
            self.current_args = {arg.arg for arg in node.args.args}

            for child in ast.walk(node):
                if isinstance(child, ast.Call):
                    call_repr = ast.unparse(child.func)
                    args_repr = [ast.unparse(a) for a in child.args]

                    for target in TARGET_OBJECTS:
                        if target in call_repr:
                            handler_info["target_interactions"].append({
                                "target": target,
                                "call": call_repr,
                                "args": args_repr,
                                "line": child.lineno,
                            })

                    if isinstance(child.func, ast.Attribute):
                        if child.func.attr in METHOD_CALLS_OF_INTEREST:
                            caller = ast.unparse(child.func.value)
                            provenance = self._qualify_provenance(caller)
                            handler_info["downstream_calls"].append({
                                "caller": caller,
                                "method": child.func.attr,
                                "provenance": provenance,
                                "args": args_repr,
                                "line": child.lineno,
                            })

            self.detected_handlers.append(handler_info)
            self.current_scope.pop()
            self.current_args.clear()

        self.generic_visit(node)

def main():
    print("=" * 80)
    print(" GATE v6.45.31 — DISCORD LIVE-CALL FORENSICS")
    print("=" * 80)
    print(f"[RACINE] {PROJECT_ROOT}\n")

    py_files = [p for p in PROJECT_ROOT.glob("**/*.py") if not (set(p.parts) & EXCLUDED_DIRS)]

    all_handlers: list[dict[str, Any]] = []
    target_usages: dict[str, list[dict[str, str]]] = {obj: [] for obj in TARGET_OBJECTS}

    for path in py_files:
        rel_path = str(path.relative_to(PROJECT_ROOT))
        try:
            content = path.read_text(encoding="utf-8", errors="replace")
            tree = ast.parse(content, filename=rel_path)
            visitor = DiscordForensicVisitor(path, rel_path)
            visitor.visit(tree)

            if visitor.detected_handlers:
                all_handlers.extend(visitor.detected_handlers)

            for name, src in visitor.imports.items():
                for target in TARGET_OBJECTS:
                    if target in src or target == name:
                        target_usages[target].append({
                            "file": rel_path,
                            "type": "IMPORT",
                            "source": src,
                        })
        except Exception as e:
            print(f"[WARN] Erreur parsing {rel_path} : {e}", file=sys.stderr)

    print(f"[+] Total fichiers scannés : {len(py_files)}")
    print(f"[+] Handlers / Écouteurs Discord détectés : {len(all_handlers)}\n")

    print("[1] HANDLERS ET POINTS D'ENTRÉE DISCORD DÉTECTÉS")
    for h in all_handlers:
        print(f"  • {h['file']}:{h['line']} -> def {h['function']}({', '.join(h['args'])})")
        if h["decorators"]:
            print(f"    Décorateurs : {', '.join(h['decorators'])}")
        for t in h["target_interactions"]:
            print(f"    -> [TARGET] {t['target']} via `{t['call']}({', '.join(t['args'])})` (ligne {t['line']})")
        for d in h["downstream_calls"]:
            print(f"    -> [CALL] [{d['provenance']}] `{d['caller']}.{d['method']}({', '.join(d['args'])})` (ligne {d['line']})")
        print()

    print("[2] USAGES DES COMPOSANTS CIBLES PAR IMPORT")
    for target, usages in target_usages.items():
        if usages:
            print(f"  • {target} ({len(usages)} imports) :")
            for u in usages[:5]:
                print(f"      - {u['file']} [{u['source']}]")
            if len(usages) > 5:
                print(f"      ... +{len(usages) - 5} autres")
            print()

    # Sauvegarde du rapport JSON
    out_file = PROJECT_ROOT / "tools" / "gate_v6_45_31_report.json"
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump({"handlers": all_handlers, "target_usages": target_usages}, f, indent=2)
    print(f"[+] Rapport JSON exporté dans : {out_file}")
    print("=" * 80)

if __name__ == "__main__":
    main()
