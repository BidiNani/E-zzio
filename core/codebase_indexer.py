import logging
import pathlib

logger = logging.getLogger("ezzio.codebase")


class CodebaseIndexer:
    """Indexe et cartographie l'ensemble des fichiers et de la structure d'E-zzio."""

    def __init__(self, root_dir: str = "."):
        self.root_dir = pathlib.Path(root_dir).resolve()
        self.ignored_dirs = {".venv", ".git", "__pycache__", ".pytest_cache", ".github", "runtime/evidence"}
        self.ignored_extensions = {".pyc", ".db", ".log", ".png", ".jpg", ".ico"}

    def get_structure_tree(self) -> str:
        """Génère une représentation textuelle de l'arborescence du projet."""
        tree_lines = []
        for path in sorted(self.root_dir.rglob("*")):
            rel_path = path.relative_to(self.root_dir)
            if any(part in self.ignored_dirs for part in rel_path.parts):
                continue
            if path.suffix in self.ignored_extensions:
                continue

            indent = "    " * (len(rel_path.parts) - 1)
            prefix = "├── " if path.is_file() else "📂 "
            tree_lines.append(f"{indent}{prefix}{path.name}")

        return "\n".join(tree_lines)

    def read_file(self, relative_path: str) -> str:
        """Lit le contenu d'un fichier spécifique de la codebase."""
        target_path = self.root_dir / relative_path
        if not target_path.exists() or not target_path.is_file():
            return f"[-] Erreur : Fichier introuvable ({relative_path})"
        try:
            with open(target_path, encoding="utf-8") as f:
                return f.read()
        except Exception as e:
            return f"[-] Erreur de lecture : {e}"

    def list_all_files(self) -> list:
        """Retourne la liste de tous les fichiers suivis."""
        files = []
        for path in sorted(self.root_dir.rglob("*")):
            rel_path = path.relative_to(self.root_dir)
            if any(part in self.ignored_dirs for part in rel_path.parts):
                continue
            if path.is_file() and path.suffix not in self.ignored_extensions:
                files.append(str(rel_path).replace("\\", "/"))
        return files
