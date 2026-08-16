from pathlib import Path

class ConstitutionGuard:
    def __init__(self, constitution_path="registry/core/constitution.md"):
        self.constitution_path = Path(constitution_path)
        self.axioms = self._load_constitution()

    def _load_constitution(self) -> list:
        if self.constitution_path.exists():
            try:
                with open(self.constitution_path, "r", encoding="utf-8") as f:
                    return [line.strip() for line in f if line.strip().startswith("-")]
            except Exception:
                pass
        return []

    def validate_action(self, target_path: str) -> bool:
        """Vérifie si une action cible un composant critique protégé."""
        normalized_target = target_path.replace("\\", "/")
        protected_scopes = ["registry/core", "runtime/kernel", "runtime/constitution"]
        
        for scope in protected_scopes:
            if normalized_target.startswith(scope):
                return False
        return True