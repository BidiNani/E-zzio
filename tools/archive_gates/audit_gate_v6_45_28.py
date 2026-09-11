from __future__ import annotations
import ast
from dataclasses import dataclass, field
from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]

# Répertoires explicitement isolés comme archives / snapshots
ARCHIVE_PARTS = {"audit", "snapshot", "snapshots", "backup", "backups", "old", "archive"}
# Répertoires hors périmètre d'exécution opérationnelle
TEST_TOOL_PARTS = {".venv", "venv", "__pycache__", ".pytest_cache", "tests"}

TARGET_CLASSES = {
    "EzzioMaster",
    "CognitiveGateway",
    "AgentProviderAdapter",
    "CodingAgentLoop",
    "AutonomousModelFabric",
    "FabricConnector",
}
TARGET_FACTORIES = {"build_fabric"}

@dataclass
class CallRecord:
    rel_path: str
    line: int
    scope: str
    callable_name: str
    args: list[str] = field(default_factory=list)
    keywords: dict[str, str] = field(default_factory=dict)
    is_active_tree: bool = True

@dataclass
class StateBinding:
    rel_path: str
    line: int
    scope: str
    target: str
    value: str
    is_active_tree: bool = True

@dataclass
class EntrypointRecord:
    rel_path: str
    line: int
    category: str
    details: str
    is_active_tree: bool = True

class SovereignFlowVisitor(ast.NodeVisitor):
    def __init__(self, rel_path: str, is_active: bool):
        self.rel_path = rel_path
        self.is_active = is_active
        self.scope_stack: list[str] = ["<module>"]
        
        self.calls: list[CallRecord] = []
        self.bindings: list[StateBinding] = []
        self.entrypoints: list[EntrypointRecord] = []

    def visit_FunctionDef(self, node: ast.FunctionDef):
        self.scope_stack.append(f"def {node.name}")
        # Détection des lifecycle hooks
        if node.name in {"lifespan", "startup", "shutdown", "setup_hook"}:
            self.entrypoints.append(
                EntrypointRecord(self.rel_path, node.lineno, "Lifecycle Hook", f"{node.name}()", self.is_active)
            )
        self.generic_visit(node)
        self.scope_stack.pop()

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef):
        self.scope_stack.append(f"async def {node.name}")
        if node.name in {"lifespan", "startup", "shutdown", "setup_hook"}:
            self.entrypoints.append(
                EntrypointRecord(self.rel_path, node.lineno, "Async Lifecycle Hook", f"{node.name}()", self.is_active)
            )
        self.generic_visit(node)
        self.scope_stack.pop()

    def visit_ClassDef(self, node: ast.ClassDef):
        self.scope_stack.append(f"class {node.name}")
        self.generic_visit(node)
        self.scope_stack.pop()

    def visit_Call(self, node: ast.Call):
        func_name = self._resolve_name(node.func)
        
        # 1. Capture des constructeurs et fabriques cibles
        if func_name in TARGET_CLASSES or func_name in TARGET_FACTORIES:
            args = [ast.unparse(a) for a in node.args]
            kw = {k.arg: ast.unparse(k.value) for k in node.keywords if k.arg}
            self.calls.append(
                CallRecord(
                    rel_path=self.rel_path,
                    line=node.lineno,
                    scope=" -> ".join(self.scope_stack),
                    callable_name=func_name,
                    args=args,
                    keywords=kw,
                    is_active_tree=self.is_active,
                )
            )

        # 2. Capture des démarreurs de runtime et d'extensions
        if func_name in {"Bot", "FastAPI"}:
            self.entrypoints.append(
                EntrypointRecord(self.rel_path, node.lineno, f"{func_name} Initialization", ast.unparse(node), self.is_active)
            )
        elif isinstance(node.func, ast.Attribute) and node.func.attr in {"add_cog", "load_extension", "include_router", "mount"}:
            self.entrypoints.append(
                EntrypointRecord(self.rel_path, node.lineno, f"Runtime Attachment .{node.func.attr}()", ast.unparse(node), self.is_active)
            )

        self.generic_visit(node)

    def visit_If(self, node: ast.If):
        test_str = ast.unparse(node.test)
        if "__name__" in test_str and "__main__" in test_str:
            self.entrypoints.append(
                EntrypointRecord(self.rel_path, node.lineno, "Main Entrypoint Block", test_str, self.is_active)
            )
        self.generic_visit(node)

    def visit_Assign(self, node: ast.Assign):
        for target in node.targets:
            target_str = ast.unparse(target)
            if any(k in target_str for k in ("fabric", "_fabric", "FABRIC", "app.state", "bot.")):
                self.bindings.append(
                    StateBinding(
                        rel_path=self.rel_path,
                        line=node.lineno,
                        scope=" -> ".join(self.scope_stack),
                        target=target_str,
                        value=ast.unparse(node.value),
                        is_active_tree=self.is_active,
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
    print(" E-ZZIO — BOOTSTRAP ANCHOR & FABRIC PROPAGATION GATE v6.45.28")
    print("=" * 80)
    print(f"[RACINE DU PROJET] {PROJECT_ROOT}\n")

    py_files = list(PROJECT_ROOT.glob("**/*.py"))
    all_calls: list[CallRecord] = []
    all_bindings: list[StateBinding] = []
    all_entrypoints: list[EntrypointRecord] = []

    for path in py_files:
        parts_set = set(path.parts)
        if parts_set & TEST_TOOL_PARTS:
            continue

        is_active = not bool(parts_set & ARCHIVE_PARTS)
        rel_path = str(path.relative_to(PROJECT_ROOT))

        try:
            tree = ast.parse(path.read_text(encoding="utf-8"), filename=rel_path)
            visitor = SovereignFlowVisitor(rel_path, is_active)
            visitor.visit(tree)
            all_calls.extend(visitor.calls)
            all_bindings.extend(visitor.bindings)
            all_entrypoints.extend(visitor.entrypoints)
        except Exception as err:
            print(f"[WARN] Erreur de parsing sur {rel_path} : {err}", file=sys.stderr)

    # 1. CALL-SITES DES COMPOSANTS (ARBRE ACTIF)
    print("[1] CALL-SITES DES COMPOSANTS CLÉS (ARBRE ACTIF)\n")
    active_calls = [c for c in all_calls if c.is_active_tree]
    for c in sorted(active_calls, key=lambda x: (x.callable_name, x.rel_path, x.line)):
        kw_str = ", ".join(f"{k}={v}" for k, v in c.keywords.items())
        params = ", ".join(filter(None, [", ".join(c.args), kw_str]))
        print(f"  • {c.callable_name:<22} | {c.rel_path}:{c.line}")
        print(f"    Scope : {c.scope}")
        print(f"    Appel : {c.callable_name}({params})\n")

    # 2. BINDINGS D'ÉTAT ET ATTACHES (ARBRE ACTIF)
    print("[2] ATTACHES D'ÉTAT & PROPAGATION DE LA FABRIC (ARBRE ACTIF)\n")
    active_bindings = [b for b in all_bindings if b.is_active_tree]
    if active_bindings:
        for b in sorted(active_bindings, key=lambda x: (x.rel_path, x.line)):
            print(f"  • {b.rel_path}:{b.line} (Scope: {b.scope})")
            print(f"    {b.target} = {b.value}\n")
    else:
        print("  [AUCUN POINT DE RÉTENTION D'ÉTAT TROUVÉ DANS L'ARBRE ACTIF]\n")

    # 3. POINTS D'ENTRÉE ET HOOKS DU PROCESSUS (ARBRE ACTIF)
    print("[3] DÉMARREURS ET HOOKS DU PROCESSUS (ARBRE ACTIF)\n")
    active_entrypoints = [e for e in all_entrypoints if e.is_active_tree]
    for e in sorted(active_entrypoints, key=lambda x: (x.category, x.rel_path, x.line)):
        print(f"  • [{e.category}] {e.rel_path}:{e.line}")
        print(f"    Détail : {e.details}\n")

    # 4. TRACE DES ARCHIVES ET SNAPSHOTS
    print("[4] DÉTECTIONS DANS LES ARCHIVES / SNAPSHOTS D'AUDIT (HORS SCORE)\n")
    archive_calls = [c for c in all_calls if not c.is_active_tree]
    print(f"  Total occurrences isolées dans l'historique : {len(archive_calls)}")
    for c in archive_calls[:5]:
        print(f"    - [ARCHIVE] {c.callable_name} dans {c.rel_path}:{c.line}")
    if len(archive_calls) > 5:
        print(f"    ... et {len(archive_calls) - 5} autres références archivées.")

    print("\n" + "=" * 80)
    print(" ANALYSE v6.45.28 COMPLÈTE : PRÊT POUR EXTRACTION DU RAPPORT")
    print("=" * 80)

if __name__ == "__main__":
    main()
