from runtime.tools.executors.powershell import PowerShellExecutor
from runtime.tools.executors.filesystem import FileSystemExecutor
from runtime.tools.executors.git import GitExecutor

class ExecutorRegistry:
    def __init__(self):
        self._registry = {
            "system.powershell": PowerShellExecutor,
            "powershell.safe.execute": PowerShellExecutor,
            "filesystem.read": FileSystemExecutor,
            "git.status": GitExecutor
        }

    def register(self, name, cls):
        self._registry[name] = cls

    def get_class(self, tool_name: str):
        if not tool_name:
            return None
        k = str(tool_name).lower()
        if key := self._registry.get(k):
            return key
        if "power" in k or "shell" in k or "safe" in k:
            return PowerShellExecutor
        if "git" in k:
            return GitExecutor
        if "file" in k or "system" in k:
            return FileSystemExecutor
        return self._registry.get(tool_name, PowerShellExecutor)
