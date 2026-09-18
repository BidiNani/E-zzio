"""
Outils de sécurité pour l'inspection, la lecture, la validation et la modification de fichiers pour E-ZzIO.
"""

import ast
import difflib
import logging
from pathlib import Path

from ezzio.config import settings
from ezzio.schemas import FilePatchResult

logger = logging.getLogger("EzzioFileTools")

IGNORE_DIRS = {
    ".venv", "venv", "__pycache__", ".pytest_cache", ".git", ".github",
    ".vscode", ".trae", "legacy_archive", "_forensic", "node_modules",
    "artifacts", "backups", "snapshot", "test_tmp", "data"
}


def list_project_files(base_dir: Path | str = settings.root_dir) -> list[str]:
    """Liste récursivement tous les fichiers du projet en ignorant les répertoires temporaires/virtuels."""
    root = Path(base_dir)
    files: list[str] = []

    for path in root.rglob("*"):
        if not path.is_file():
            continue
        try:
            rel_parts = set(path.relative_to(root).parts[:-1])
        except ValueError:
            rel_parts = set()

        if rel_parts.intersection(IGNORE_DIRS):
            continue
        try:
            rel = path.relative_to(root).as_posix()
            files.append(rel)
        except ValueError:
            files.append(str(path))

    return sorted(files)


def read_project_file(rel_path: str, base_dir: Path | str = settings.root_dir) -> str:
    """Lit un fichier du projet de manière sécurisée."""
    root = Path(base_dir).resolve()
    target = (root / rel_path).resolve()

    # Vérification anti-path traversal
    if not str(target).startswith(str(root)):
        raise PermissionError(f"Accès refusé hors du répertoire racine : {rel_path}")

    if not target.exists():
        raise FileNotFoundError(f"Fichier introuvable : {rel_path}")

    return target.read_text(encoding="utf-8", errors="ignore")


def verify_python_syntax(code: str) -> tuple[bool, str | None]:
    """Valide la syntaxe Python avec AST sans exécuter le code."""
    try:
        ast.parse(code)
        return True, None
    except SyntaxError as err:
        return False, f"Erreur de syntaxe ligne {err.lineno}: {err.msg}"


def apply_file_patch(
    rel_path: str,
    target_content: str,
    replacement_content: str,
    base_dir: Path | str = settings.root_dir
) -> FilePatchResult:
    """
    Applique une modification ciblée à un fichier après vérification syntaxique.
    Crée une sauvegarde automatique avant écriture.
    """
    root = Path(base_dir).resolve()
    target = (root / rel_path).resolve()

    if not str(target).startswith(str(root)):
        return FilePatchResult(
            file_path=rel_path,
            success=False,
            message="Accès interdit hors de la racine du projet",
            ast_valid=False
        )

    if not target.exists():
        return FilePatchResult(
            file_path=rel_path,
            success=False,
            message=f"Le fichier {rel_path} n'existe pas",
            ast_valid=False
        )

    try:
        current_content = target.read_text(encoding="utf-8")

        if target_content not in current_content:
            return FilePatchResult(
                file_path=rel_path,
                success=False,
                message="Le bloc cible à remplacer n'a pas été trouvé à l'identique dans le fichier.",
                ast_valid=True
            )

        new_content = current_content.replace(target_content, replacement_content, 1)

        # Validation AST si c'est un fichier Python
        if target.suffix == ".py":
            is_valid, err_msg = verify_python_syntax(new_content)
            if not is_valid:
                return FilePatchResult(
                    file_path=rel_path,
                    success=False,
                    message=f"Correction rejetée : invalidité syntaxique ({err_msg})",
                    ast_valid=False
                )

        # Calcul du diff
        diff_lines = list(difflib.unified_diff(
            current_content.splitlines(keepends=True),
            new_content.splitlines(keepends=True),
            fromfile=f"a/{rel_path}",
            tofile=f"b/{rel_path}"
        ))
        diff_str = "".join(diff_lines)

        # Sauvegarde de secours
        backup_file = target.with_suffix(f"{target.suffix}.ezzio_bak")
        backup_file.write_text(current_content, encoding="utf-8")

        # Écriture du nouveau contenu
        target.write_text(new_content, encoding="utf-8")

        return FilePatchResult(
            file_path=rel_path,
            success=True,
            message="Modification appliquée avec succès et syntaxe validée.",
            ast_valid=True,
            diff=diff_str
        )
    except Exception as exc:
        logger.error("Erreur lors de l'application du patch : %s", exc)
        return FilePatchResult(
            file_path=rel_path,
            success=False,
            message=f"Erreur d'écriture : {exc}",
            ast_valid=False
        )
