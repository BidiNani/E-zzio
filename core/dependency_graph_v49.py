import ast
import json
import logging
from pathlib import Path
from typing import Dict, List, Set, Tuple
from collections import defaultdict

logger = logging.getLogger("ezzio.core.dependency_graph_v49")


class DependencyGraphV49:
    """
    Construit un graphe de dépendances Python avec fermeture transitive.
    V49.0 : Graphe de base
    V49.1 : Extension de scope par domaine
    V49.2 : Détection orphelins + dépendances circulaires
    """

    EXCLUDED_DIRS = {
        ".venv",
        "test_isolation",
        "evidence",
        "decisions",
        "quarantine",
        "_archive",
        "_archive_memoire_morte",
        "_a_verifier",
        "_backups_auto",
        "archive",
        "backups",
        "runtime_temp_forensic",
        "guardian",
        "__pycache__",
        ".pytest_cache",
        ".mypy_cache",
        ".ruff_cache",
    }

    def __init__(self, project_root: str = "."):
        self.project_root = Path(project_root).resolve()
        self.import_map: Dict[str, Set[str]] = defaultdict(set)
        self.reverse_map: Dict[str, Set[str]] = defaultdict(set)
        self.file_to_module: Dict[str, str] = {}

    def _should_exclude(self, path: Path) -> bool:
        for part in path.parts:
            if part in self.EXCLUDED_DIRS:
                return True
        return False

    def _path_to_module(self, filepath: Path) -> str:
        rel_path = filepath.relative_to(self.project_root)
        parts = list(rel_path.parts)
        if parts[-1] == "__init__.py":
            parts = parts[:-1]
        else:
            parts[-1] = parts[-1].replace(".py", "")
        return ".".join(parts)

    def _parse_imports(self, filepath: Path) -> Set[str]:
        imports = set()
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                content = f.read()
            tree = ast.parse(content)
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        imports.add(alias.name.split(".")[0])
                        imports.add(alias.name)
                elif isinstance(node, ast.ImportFrom):
                    if node.module:
                        imports.add(node.module.split(".")[0])
                        imports.add(node.module)
        except Exception as e:
            logger.warning("[WARN] Erreur parsing %s : %s", filepath, e)
        return imports

    def build(self):
        logger.info("[INFO] Construction du graphe de dépendances...")
        py_files = []
        for py_file in self.project_root.rglob("*.py"):
            if not self._should_exclude(py_file):
                py_files.append(py_file)
        logger.info("[INFO] %d fichiers Python trouvés", len(py_files))

        for filepath in py_files:
            try:
                module_name = self._path_to_module(filepath)
                self.file_to_module[str(filepath)] = module_name
                imports = self._parse_imports(filepath)
                rel_path = str(filepath.relative_to(self.project_root))
                self.import_map[rel_path] = imports
                for imp in imports:
                    self.reverse_map[imp].add(rel_path)
            except Exception as e:
                logger.warning("[WARN] Erreur traitement %s : %s", filepath, e)
        logger.info("[OK] Graphe construit : %d fichiers, %d modules", len(self.import_map), len(self.reverse_map))

    def get_dependents(self, module_name: str) -> List[str]:
        return sorted(self.reverse_map.get(module_name, set()))

    def get_dependencies(self, filepath: str) -> List[str]:
        return sorted(self.import_map.get(filepath, set()))

    def get_transitive_closure(self, seed_files: List[str]) -> Set[str]:
        closure = set(seed_files)
        queue = list(seed_files)
        while queue:
            current = queue.pop(0)
            deps = self.get_dependencies(current)
            for dep in deps:
                for filepath, module in self.file_to_module.items():
                    if module == dep or module.endswith(f".{dep}"):
                        if filepath not in closure:
                            closure.add(filepath)
                            queue.append(filepath)
                        break
        return closure

    def find_orphans(self) -> List[str]:
        orphans = []
        for filepath in self.import_map.keys():
            has_imports = len(self.import_map[filepath]) > 0
            is_imported = filepath in self.reverse_map or any(filepath in deps for deps in self.reverse_map.values())
            if not has_imports and not is_imported:
                orphans.append(filepath)
        return sorted(orphans)

    def find_circular_dependencies(self) -> List[Tuple[str, str]]:
        circular = []
        for filepath, imports in self.import_map.items():
            for imp in imports:
                for other_path, module in self.file_to_module.items():
                    if module == imp or module.endswith(f".{imp}"):
                        if filepath in self.import_map.get(other_path, set()):
                            circular.append((filepath, other_path))
                        break
        return circular

    def export_json(self, output_path: str = "runtime/dependency_graph.json"):
        output = Path(output_path)
        output.parent.mkdir(parents=True, exist_ok=True)
        data = {
            "import_map": {k: sorted(v) for k, v in self.import_map.items()},
            "reverse_map": {k: sorted(v) for k, v in self.reverse_map.items()},
            "file_to_module": self.file_to_module,
            "orphans": self.find_orphans(),
            "circular_dependencies": self.find_circular_dependencies(),
        }
        with open(output, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        logger.info("[OK] Graphe exporté vers %s", output_path)
        return output_path

    def extend_scope_by_domain(self, domain_files: List[str]) -> List[str]:
        closure = self.get_transitive_closure(domain_files)
        return sorted(closure)

    def export_graphviz(self, output_path: str = "runtime/dependency_graph.dot"):
        output = Path(output_path)
        output.parent.mkdir(parents=True, exist_ok=True)
        lines = ["digraph Dependencies {"]
        lines.append("  rankdir=LR;")
        lines.append("  node [shape=box, style=filled, fillcolor=lightblue];")
        lines.append("")
        for filepath in self.import_map.keys():
            node_name = filepath.replace("\\", "_").replace("/", "_").replace(".", "_")
            label = filepath.split("/")[-1].replace(".py", "")
            lines.append(f'  {node_name} [label="{label}"];')
        lines.append("")
        for filepath, imports in self.import_map.items():
            from_node = filepath.replace("\\", "_").replace("/", "_").replace(".", "_")
            for imp in imports:
                for target_path, module in self.file_to_module.items():
                    if module == imp or module.endswith(f".{imp}"):
                        to_node = target_path.replace("\\", "_").replace("/", "_").replace(".", "_")
                        lines.append(f"  {from_node} -> {to_node};")
                        break
        lines.append("}")
        with open(output, "w", encoding="utf-8") as f:
            f.write("\n".join(lines))
        logger.info("[OK] Graphe exporté vers %s", output_path)
        return output_path
