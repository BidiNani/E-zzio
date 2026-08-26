class SecurityPolicy:
    LEVEL_READ = 0
    LEVEL_MODIFY = 1
    LEVEL_EXECUTE = 2
    LEVEL_SYSTEM = 3

    @classmethod
    def get_level(cls, tool_name: str) -> int:
        if tool_name in ["filesystem.read", "filesystem.list", "filesystem.observe", "research.search"]:
            return cls.LEVEL_READ
        if tool_name in ["filesystem.write", "filesystem.delete"]:
            return cls.LEVEL_MODIFY
        if tool_name in ["process.execute", "shell.run"]:
            return cls.LEVEL_EXECUTE
        return cls.LEVEL_SYSTEM
