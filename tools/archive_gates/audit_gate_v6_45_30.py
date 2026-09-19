from __future__ import annotations

import ast
import sys
from dataclasses import dataclass, field
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]

# Exclusion stricte des archives, tests et caches
EXCLUDED_PARTS = {"audit", "snapshot", "snapshots", "backup", "backups", "old", "archive", ".venv", "venv", "__pycache__", ".pytest_cache", "tests"}

TARGET_CLASSES = {
    "EzzioMaster",
    "CognitiveGateway",
    "CodingAgentHarness",
    "AgentProviderAdapter",
    "AutonomousModelFabric",
    "IntentFabricConnector",
}
TARGET_FACTORIES = {"build_fabric"}

@dataclass
class InstanceLineage:
    file_path: str
    line: int
    target_var: str
    callable_name: str
    scope_type: str  # MODULE_LEVEL (UNANCHORED), METHOD, FUNCTION, LIFECYCLE
    scope_name: str
    args: list[str] = field(default_factory=list)
    keywords: dict[str, str] = field(default_factory=dict)
    classification: str = "DIRECT_LOCAL"

@dataclass
class CogRegistration:
    file_path: str
    line: int
    scope: str
    cog_expr: str
    passed_args: str

class LineageVisitor(ast.NodeVisitor):
    def __init__(self, rel_path: str):
        self.rel_path = rel_path
        self.scope_stack: list[str] = ["<module>"]
        self.lineages: list[InstanceLineage] = []
        self.cog_registrations: list[CogRegistration] = []
        self.build_fabric_call_count = 0

    def visit_FunctionDef(self, node: ast.FunctionDef):
        self.scope_stack.append(f"def {node.name}")
        self.generic_visit(node)
        self.scope_stack.pop()

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef):
        self.scope_stack.append(f"async def {node.name}")
        self.generic_visit(node)
        self.scope_stack.pop()

    def visit_ClassDef(self, node: ast.ClassDef):
        self.scope_stack.append(f"class {node.name}")
        self.generic_visit(node)
        self.scope_stack.pop()

    def visit_Assign(self, node: ast.Assign):
        target_str = ast.unparse(node.targets[0])
        val_node = node.value

        if isinstance(val_node, ast.Call):
            func_name = self._resolve_name(val_node.func)
            if func_name in TARGET_CLASSES or func_name in TARGET_FACTORIES:
                scope_str = " -> ".join(self.scope_stack)
                scope_type = "METHOD" if len(self.scope_stack) > 2 else ("FUNCTION" if len(self.scope_stack) == 2 else "MODULE_LEVEL (UNANCHORED)")

                args = [ast.unparse(a) for a in val_node.args]
                kw = {k.arg: ast.unparse(k.value) for k in val_node.keywords if k.arg}

                # Qualification du statut d'ancrage
                classification = "DIRECT_LOCAL"
                if scope_type.startswith("MODULE_LEVEL"):
                    classification = "⚠️ UNANCHORED MODULE-LEVEL INSTANCE"
                elif any(k in target_str for k in ("self.", "cls.", "app.state", "bot.")):
                    classification = "PERSISTENT ATTRIBUTE"

                self.lineages.append(
                    InstanceLineage(
                        file_path=self.rel_path,
                        line=node.lineno,
                        target_var=target_str,
                        callable_name=func_name,
                        scope_type=scope_type,
                        scope_name=scope_str,
                        args=args,
                        keywords=kw,
                        classification=classification
                    )
                )
        self.generic_visit(node)

    def visit_Call(self, node: ast.Call):
        func_name = self._resolve_name(node.func)

        # Traçage spécifique de build_fabric sans assignation
        if func_name == "build_fabric":
            self.build_fabric_call_count += 1

        # Traçage des cogs Discord
        if isinstance(node.func, ast.Attribute) and node.func.attr == "add_cog":
            cog_arg = ast.unparse(node.args[0]) if node.args else "<inconnu>"
            self.cog_registrations.append(
                CogRegistration(
                    file_path=self.rel_path,
                    line=node.lineno,
                    scope=" -> ".join(self.scope_stack),
                    cog_expr=ast.unparse(node),
                    passed_args=cog_arg
                )
            )
        self.generic_visit(node)

    def _resolve_name(self, node: ast.AST) -> str:
        if isinstance(node, ast.Name):
            return node.id
        if isinstance(node, ast.Attribute):
            return node.attr
        return ""

def main():
    print("=" * 80)
    print(" E-ZZIO — INSTANCE LINEAGE & RUNTIME PROVENANCE (GATE v6.45.30)")
    print("=" * 80)
    print(f"[RACINE] {PROJECT_ROOT}\n")

    py_files = [p for p in PROJECT_ROOT.glob("**/*.py") if not (set(p.parts) & EXCLUDED_PARTS)]

    all_lineages: list[InstanceLineage] = []
    all_cogs: list[CogRegistration] = []

    fabric_counter = 0

    for path in py_files:
        rel_path = str(path.relative_to(PROJECT_ROOT))
        try:
            tree = ast.parse(path.read_text(encoding="utf-8"), filename=rel_path)
            visitor = LineageVisitor(rel_path)
            visitor.visit(tree)
            all_lineages.extend(visitor.lineages)
            all_cogs.extend(visitor.cog_registrations)
        except Exception as e:
            print(f"[WARN] Erreur parsing {rel_path} : {e}", file=sys.stderr)

    # 1. Cartographie des instances Fabric construites
    print("[1] IDENTIFICATION ET INDEXATION DES INSTANCES FABRIC")
    for lin in all_lineages:
        if lin.callable_name in {"build_fabric", "AutonomousModelFabric"}:
            fabric_counter += 1
            print(f"  • Fabric #{fabric_counter:<2} | {lin.file_path}:{lin.line}")
            print(f"    Assigné à   : {lin.target_var}")
            print(f"    Scope       : {lin.scope_name} ({lin.scope_type})")
            print(f"    Statut      : {lin.classification}\n")

    if fabric_counter == 0:
        print("  [AUCUNE INSTANCE DE FABRIC DÉTECTÉE DANS LE RUNTIME ACTIF]\n")

    # 2. Généalogie des objets critiques (Master, Gateway, Harness, Adapter)
    print("[2] GÉNÉALOGIE & PROVENANCE DES OBJETS CRITIQUES D'EXÉCUTION")
    for lin in all_lineages:
        if lin.callable_name not in {"build_fabric", "AutonomousModelFabric"}:
            kw_repr = ", ".join(f"{k}={v}" for k, v in lin.keywords.items())
            args_repr = ", ".join(filter(None, [", ".join(lin.args), kw_repr]))
            print(f"  • {lin.callable_name:<22} | {lin.file_path}:{lin.line}")
            print(f"    Conteneur/Cible : {lin.target_var}")
            print(f"    Scope           : {lin.scope_name}")
            print(f"    Paramètres      : ({args_repr})")
            print(f"    Classification  : {lin.classification}\n")

    # 3. Traçage du cycle de vie des Cogs Discord (Baseline opérationnelle)
    print("[3] TRAÇAGE DE LA CHAÎNE DE CYCLE DE VIE DISCORD (BASELINE TÉMOIN)")
    if all_cogs:
        for cog in all_cogs:
            print(f"  • Enregistrement Cog | {cog.file_path}:{cog.line}")
            print(f"    Scope       : {cog.scope}")
            print(f"    Expression  : {cog.cog_expr}")
            print(f"    Cog injecté : {cog.passed_args}\n")
    else:
        print("  [AUCUN APPEL bot.add_cog DÉTECTÉ DANS LES FICHIERS PRINCIPAUX]\n")

    print("=" * 80)
    print(" VERDICT FORENSIQUE v6.45.30 : AUDIT D'ANCRAGE TERMINÉ")
    print("=" * 80)

if __name__ == "__main__":
    main()
