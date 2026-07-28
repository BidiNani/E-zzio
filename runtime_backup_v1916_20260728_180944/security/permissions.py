from runtime.tools.manifest_loader import ManifestLoader

class SecurityPolicy:
    """Gère les permissions dynamiquement à partir du ManifestLoader unifié."""
    LEVEL_READ = 0
    LEVEL_MODIFY = 1
    LEVEL_SYSTEM = 2
    LEVEL_UNKNOWN = 999

    @classmethod
    def get_level(cls, tool_name: str) -> int:
        tools = ManifestLoader.get_tools()
        config = tools.get(tool_name, {})
        return config.get("permission_level", cls.LEVEL_UNKNOWN)

    @classmethod
    def is_allowed(cls, tool_name: str, required_level: int) -> bool:
        level = cls.get_level(tool_name)
        if level == cls.LEVEL_UNKNOWN:
            return False
        return level <= required_level