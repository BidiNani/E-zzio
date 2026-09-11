import ast
from pathlib import Path
from typing import Dict, List, Set
import logging

logger = logging.getLogger("ezzio.core.dependency_graph")


class DependencyGraphBuilder:
    """
    Construit un graphe de dépendances Python (import, from ... import).
    Exclut les dossiers de scratch/quarantaine (V49.2).
    """

    # Liste d'exclusion ÉTENDUE de V49.2
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
    }

    def __init__(self, project_root: str = "."):
        self.project_root = Path(project_root)
        self.import_map: Dict[str, Set[str]] = {}  # fichier → ensemble des imports
        self.reverse_map: Dict[str, Set[str]] = {}  # module → ensemble des fichiers qui l'importent

    def _should_exclude(self, path: Path) -> bool:
        """Vérifie si un chemin doit être exclu."""
        for part in path.parts:
            if part in self.EXCLUDED_DIRS:
                return True
        return False

    def _parse_imports(self, filepath: Path) -> Set[str]:
        """Extrait les imports d'un fichier Python."""
        imports = set()
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                content = f.read()

            tree = ast.parse(content)
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        imports.add(alias.name.split(".")[0])
                elif isinstance(node, ast.ImportFrom):
                    if node.module:
                        imports.add(node.module.split(".")[0])
        except Exception as e:
            logger.warning(f"[WARN] Erreur parsing {filepath} : {e}")

        return imports

    def build(self, seed_files: List[str] = None):
        """
        Construit le graphe de dépendances.
        seed_files : liste de fichiers de départ (ex: bot.py, server.py)
        """
        # Si aucun seed, on scanne tout le projet
        if not seed_files:
            seed_files = []
            for py_file in self.project_root.rglob("*.py"):
                if not self._should_exclude(py_file):
                    seed_files.append(str(py_file))

        logger.info(f"[INFO] Construction du graphe depuis {len(seed_files)} fichiers seeds...")

        # Premier pass : extraire tous les imports
        for filepath_str in seed_files:
            filepath = Path(filepath_str)
            if not filepath.exists() or self._should_exclude(filepath):
                continue

            imports = self._parse_imports(filepath)
            rel_path = str(filepath.relative_to(self.project_root))
            self.import_map[rel_path] = imports

            # Build reverse map
            for imp in imports:
                if imp not in self.reverse_map:
                    self.reverse_map[imp] = set()
                self.reverse_map[imp].add(rel_path)

        logger.info(f"[OK] Graphe construit : {len(self.import_map)} fichiers, {len(self.reverse_map)} modules")

    def get_dependents(self, module_name: str) -> List[str]:
        """Retourne tous les fichiers qui importent un module donné."""
        return sorted(self.reverse_map.get(module_name, set()))

    def get_dependencies(self, filepath: str) -> List[str]:
        """Retourne tous les modules importés par un fichier donné."""
        return sorted(self.import_map.get(filepath, set()))
