"""
Moteur d'auto-guérison et de correction automatique pour E-ZzIO.
"""

import logging
from pathlib import Path
from typing import Any

from ezzio.config import settings
from ezzio.schemas import FilePatchResult
from ezzio.self_repair.codebase_catalog import get_codebase_catalog
from ezzio.tools.file_tools import (
    apply_file_patch,
    verify_python_syntax,
)

logger = logging.getLogger("EzzioAutoHealer")


class AutoHealer:
    def __init__(self, root_dir: Path | str = settings.root_dir) -> None:
        self.root_dir = Path(root_dir).resolve()
        self.catalog = get_codebase_catalog()

    def diagnose_all(self) -> dict[str, Any]:
        """Analyse la santé de l'ensemble des fichiers répertoriés."""
        catalog_data = self.catalog.scan_all()
        files = catalog_data.get("files", {})

        syntax_errors = []
        clean_files = []

        for rel_path, info in files.items():
            if info.get("type") == "python":
                if not info.get("syntax_valid", True):
                    syntax_errors.append({
                        "file": rel_path,
                        "error": info.get("error", "Erreur de syntaxe inconnue")
                    })
                else:
                    clean_files.append(rel_path)

        return {
            "total_files": len(files),
            "python_modules": len(clean_files) + len(syntax_errors),
            "syntax_valid_count": len(clean_files),
            "syntax_errors": syntax_errors,
            "healthy": len(syntax_errors) == 0,
        }

    def repair_syntax_error(self, rel_path: str, fixed_code: str) -> FilePatchResult:
        """Applique une correction complète de fichier après validation AST."""
        is_valid, err = verify_python_syntax(fixed_code)
        if not is_valid:
            return FilePatchResult(
                file_path=rel_path,
                success=False,
                message=f"Correction refusée : code non syntaxiquement valide ({err})",
                ast_valid=False
            )

        target = self.root_dir / rel_path
        if not target.exists():
            return FilePatchResult(
                file_path=rel_path,
                success=False,
                message=f"Fichier {rel_path} introuvable",
                ast_valid=False
            )

        try:
            # Backup
            backup = target.with_suffix(f"{target.suffix}.ezzio_bak")
            backup.write_text(target.read_text(encoding="utf-8", errors="ignore"), encoding="utf-8")

            # Écriture
            target.write_text(fixed_code, encoding="utf-8")

            # Mettre à jour le catalogue
            self.catalog.scan_all()

            return FilePatchResult(
                file_path=rel_path,
                success=True,
                message="Fichier corrigé avec succès et validé par AST.",
                ast_valid=True
            )
        except Exception as exc:
            return FilePatchResult(
                file_path=rel_path,
                success=False,
                message=f"Erreur d'écriture : {exc}",
                ast_valid=False
            )

    def apply_patch(self, rel_path: str, target_content: str, replacement_content: str) -> FilePatchResult:
        """Applique un patch ciblé et rafraîchit le catalogue."""
        res = apply_file_patch(rel_path, target_content, replacement_content, base_dir=self.root_dir)
        if res.success:
            self.catalog.scan_all()
        return res
