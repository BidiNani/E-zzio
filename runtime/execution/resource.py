from pathlib import Path
from runtime.contracts.execution_context import ExecutionContext


class FileSystemResourceSandbox:
    """Applique la physique du système de fichiers en se basant UNIQUEMENT sur le token."""

    def __init__(self, context: ExecutionContext, project_root: str):
        self.context = context
        self.project_root = Path(project_root).resolve()
        # L'exécuteur est aveugle : il ne lit JAMAIS le manifest, il obéit au Token.
        self.constraints = context.capability.constraints

    def validate_read(self, raw_path: str) -> Path:
        target_path = None
        valid_root = False
        roots = self.constraints.get("roots", ["."])

        # Résolution brute
        temp_path = (self.project_root / raw_path).resolve()

        # 1. Blocage strict des Symlinks (Avant toute autre validation)
        if temp_path.is_symlink():
            raise PermissionError("Sandbox Resource : Les liens symboliques sont strictement interdits.")

        # 2. Validation de la racine (anti Path-Traversal)
        for r in roots:
            root_path = (self.project_root / r).resolve()
            try:
                temp_path.relative_to(root_path)
                valid_root = True
                target_path = temp_path
                break
            except ValueError:
                continue

        if not valid_root or not target_path:
            raise PermissionError("Sandbox Resource : Chemin hors des racines autorisées.")

        if not target_path.exists() or not target_path.is_file():
            raise FileNotFoundError("Sandbox Resource : Fichier introuvable.")

        # 3. Validation de l'extension stricte
        allowed_exts = self.constraints.get("allowed_extensions", [])
        if allowed_exts:
            if target_path.suffix.lower() not in allowed_exts:
                raise PermissionError(f"Sandbox Resource : Extension '{target_path.suffix}' interdite.")

        # 4. Vérification de taille
        max_size = self.constraints.get("max_file_size_bytes", 2097152)
        if target_path.stat().st_size > max_size:
            raise PermissionError("Sandbox Resource : Fichier trop volumineux.")

        return target_path
