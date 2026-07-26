class ToolResolver:
    """
    Résolveur unique des identifiants logiques et alias vers les noms canoniques.
    Garantit l'immutabilité de l'audit tout en assurant la résolution interne.
    """
    ALIASES = {
        "system.powershell": "powershell.safe.execute"
    }

    @classmethod
    def resolve(cls, tool_name: str) -> str:
        """Résout un alias logique vers son exécuteur canonique."""
        return cls.ALIASES.get(tool_name, tool_name)