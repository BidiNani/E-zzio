"""
E-ZZIO — Universal File Scanner
Scan et indexe TOUS les fichiers du projet (code, config, docs, etc.)
"""

from pathlib import Path
from typing import List, Dict
import hashlib
import json


class FileScanner:
    """Scanner universel pour tous types de fichiers."""

    # Extensions à ignorer (binaires, cache, etc.)
    IGNORED_EXTENSIONS = {
        ".pyc",
        ".pyo",
        ".pyd",
        ".so",
        ".dll",
        ".exe",
        ".bin",
        ".db",
        ".sqlite",
        ".sqlite3",
        ".db-journal",
        ".lock",
        ".log",
        ".tmp",
        ".temp",
        ".bak",
        ".swp",
        ".png",
        ".jpg",
        ".jpeg",
        ".gif",
        ".ico",
        ".svg",
        ".woff",
        ".woff2",
        ".ttf",
        ".eot",
        ".zip",
        ".tar",
        ".gz",
        ".rar",
        ".7z",
        ".pkl",
        ".pickle",
        ".parquet",
        ".feather",
        ".egg-info",
        ".dist-info",
    }

    # Dossiers à ignorer
    IGNORED_DIRS = {
        "__pycache__",
        ".git",
        ".venv",
        "venv",
        "node_modules",
        ".pytest_cache",
        ".mypy_cache",
        ".ruff_cache",
        "runtime",
        "build",
        "dist",
        ".eggs",
    }

    def __init__(self, project_root: Path):
        self.project_root = project_root
        self.files: Dict[str, Dict] = {}

    def scan(self, include_hidden: bool = False) -> List[str]:
        """
        Scan tous les fichiers du projet.
        Retourne une liste de chemins relatifs.
        """
        all_files = []

        for filepath in self.project_root.rglob("*"):
            # Ignorer les dossiers
            if any(ignored in filepath.parts for ignored in self.IGNORED_DIRS):
                continue

            # Ignorer les fichiers non-supportés
            if filepath.is_file():
                ext = filepath.suffix.lower()
                if ext in self.IGNORED_EXTENSIONS:
                    continue

                # Ignorer les fichiers cachés (optionnel)
                if not include_hidden and filepath.name.startswith("."):
                    continue

                rel_path = str(filepath.relative_to(self.project_root))
                all_files.append(rel_path)

        self.files = {f: self._get_file_info(f) for f in all_files}
        return all_files

    def _get_file_info(self, rel_path: str) -> Dict:
        """Récupère les métadonnées d'un fichier."""
        filepath = self.project_root / rel_path

        try:
            stat = filepath.stat()
            return {
                "size": stat.st_size,
                "ext": filepath.suffix.lower(),
                "hash": self._file_hash(filepath),
            }
        except Exception as e:
            return {
                "size": 0,
                "ext": "",
                "hash": "",
                "error": str(e),
            }

    def _file_hash(self, filepath: Path) -> str:
        """Calcule le hash MD5 d'un fichier."""
        try:
            with open(filepath, "rb") as f:
                return hashlib.md5(f.read()).hexdigest()
        except:
            return ""

    def get_files_by_type(self) -> Dict[str, List[str]]:
        """Groupe les fichiers par extension."""
        by_type: Dict[str, List[str]] = {}

        for rel_path, info in self.files.items():
            ext = info.get("ext", "")
            if ext not in by_type:
                by_type[ext] = []
            by_type[ext].append(rel_path)

        return by_type

    def get_summary(self) -> Dict:
        """Résumé du scan."""
        by_type = self.get_files_by_type()

        return {
            "total_files": len(self.files),
            "total_size": sum(info["size"] for info in self.files.values()),
            "by_extension": {ext: len(files) for ext, files in by_type.items()},
            "top_extensions": sorted([(ext, len(files)) for ext, files in by_type.items()], key=lambda x: x[1], reverse=True)[:10],
        }

    def export_to_json(self, output_path: Path) -> None:
        """Export le scan en JSON."""
        output_path.parent.mkdir(parents=True, exist_ok=True)

        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(
                {
                    "project_root": str(self.project_root),
                    "files": self.files,
                    "summary": self.get_summary(),
                },
                f,
                indent=2,
                ensure_ascii=False,
            )
