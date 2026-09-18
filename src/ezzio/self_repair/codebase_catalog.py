"""
Catalogue universel et graphe de connaissances du codebase E-ZzIO.
Extrait la structure AST de chaque fichier Python, les fonctions, classes, docstrings et dépendances.
"""

import ast
import hashlib
import json
import logging
from pathlib import Path
from typing import Any

from ezzio.config import settings

logger = logging.getLogger("EzzioCatalog")

IGNORE_DIRS = {
    ".venv", "venv", "__pycache__", ".pytest_cache", ".git", ".github",
    ".vscode", ".trae", "legacy_archive", "_forensic", "node_modules",
    "artifacts", "backups", "snapshot", "test_tmp", "data"
}


class CodebaseCatalog:
    def __init__(self, root_dir: Path | str = settings.root_dir) -> None:
        self.root_dir = Path(root_dir).resolve()
        self.catalog_path = self.root_dir / "data" / "codebase_catalog.json"
        self.catalog_path.parent.mkdir(parents=True, exist_ok=True)
        self.entries: dict[str, Any] = {}

    def scan_all(self) -> dict[str, Any]:
        """Scanne l'intégralité du projet et construit le catalogue structuré."""
        logger.info("Scan complet du projet pour l'auto-connaissance : %s", self.root_dir)
        catalog: dict[str, Any] = {
            "root": str(self.root_dir),
            "files_count": 0,
            "python_modules_count": 0,
            "files": {},
            "symbol_index": {},  # symbole -> chemin du fichier
        }

        for path in self.root_dir.rglob("*"):
            if not path.is_file():
                continue

            try:
                rel_parts = set(path.relative_to(self.root_dir).parts[:-1])
            except ValueError:
                rel_parts = set()

            if rel_parts.intersection(IGNORE_DIRS):
                continue

            try:
                rel_path = path.relative_to(self.root_dir).as_posix()
            except ValueError:
                rel_path = path.name

            file_info = self._analyze_file(path, rel_path)
            catalog["files"][rel_path] = file_info

            # Enregistrer les symboles dans l'index inversé
            for sym in file_info.get("symbols", []):
                catalog["symbol_index"][sym] = rel_path

        catalog["files_count"] = len(catalog["files"])
        catalog["python_modules_count"] = sum(
            1 for f in catalog["files"].values() if f.get("type") == "python"
        )

        self.entries = catalog
        self.save()
        logger.info("Scan terminé : %d fichiers cartographiés.", catalog["files_count"])
        return catalog

    def _analyze_file(self, path: Path, rel_path: str) -> dict[str, Any]:
        stat = path.stat()
        file_hash = hashlib.sha256(path.read_bytes()).hexdigest()

        info: dict[str, Any] = {
            "path": rel_path,
            "extension": path.suffix.lower(),
            "size_bytes": stat.st_size,
            "sha256": file_hash,
            "type": "other",
            "symbols": [],
            "docstring": "",
            "imports": [],
            "classes": [],
            "functions": [],
            "syntax_valid": True,
        }

        if path.suffix == ".py":
            info["type"] = "python"
            try:
                content = path.read_text(encoding="utf-8", errors="ignore")
                tree = ast.parse(content)
                info["docstring"] = ast.get_docstring(tree) or ""

                for node in ast.iter_child_nodes(tree):
                    if isinstance(node, ast.ClassDef):
                        info["classes"].append(node.name)
                        info["symbols"].append(node.name)
                        # Méthodes
                        for sub in node.body:
                            if isinstance(sub, ast.FunctionDef | ast.AsyncFunctionDef):
                                method_name = f"{node.name}.{sub.name}"
                                info["symbols"].append(method_name)
                    elif isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef):
                        info["functions"].append(node.name)
                        info["symbols"].append(node.name)
                    elif isinstance(node, ast.Import):
                        for alias in node.names:
                            info["imports"].append(alias.name)
                    elif isinstance(node, ast.ImportFrom):
                        mod = node.module or ""
                        for alias in node.names:
                            info["imports"].append(f"{mod}.{alias.name}")
            except Exception as err:
                info["syntax_valid"] = False
                info["error"] = str(err)
        elif path.suffix == ".md":
            info["type"] = "markdown"
        elif path.suffix == ".json":
            info["type"] = "json"
        elif path.suffix == ".ps1":
            info["type"] = "powershell"

        return info

    def save(self) -> None:
        """Enregistre le catalogue sur disque en JSON lisible."""
        self.catalog_path.write_text(
            json.dumps(self.entries, indent=2, ensure_ascii=False),
            encoding="utf-8"
        )

    def load(self) -> dict[str, Any]:
        """Charge le catalogue existant ou lance un scan si nécessaire."""
        if self.catalog_path.exists():
            try:
                self.entries = json.loads(self.catalog_path.read_text(encoding="utf-8"))
                return self.entries
            except Exception:
                pass
        return self.scan_all()

    def find_symbol(self, symbol_name: str) -> str | None:
        """Retrouve le fichier définissant une classe ou une fonction."""
        if not self.entries:
            self.load()
        return self.entries.get("symbol_index", {}).get(symbol_name)


_GLOBAL_CATALOG: CodebaseCatalog | None = None


def get_codebase_catalog() -> CodebaseCatalog:
    global _GLOBAL_CATALOG
    if _GLOBAL_CATALOG is None:
        _GLOBAL_CATALOG = CodebaseCatalog()
    return _GLOBAL_CATALOG
