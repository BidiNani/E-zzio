import importlib
import pkgutil
import runtime.tools.executors

class ExecutorRegistry:
    def __init__(self):
        self._registry = {}
        self._discover_executors()

    def _discover_executors(self):
        package = runtime.tools.executors
        for _, module_name, _ in pkgutil.walk_packages(package.__path__, package.__name__ + "."):
            try:
                module = importlib.import_module(module_name)
            except Exception as e:
                print(f"[REGISTRY WARNING] Impossible de charger {module_name}: {e}")
                continue
                
            for attr_name in dir(module):
                obj = getattr(module, attr_name)
                if getattr(obj, "__is_executor__", False) and hasattr(obj, "TOOL_NAME"):
                    tool_name = obj.TOOL_NAME
                    if tool_name in self._registry:
                        raise RuntimeError(f"Duplicate executor registration error: '{tool_name}' already registered by {self._registry[tool_name].__name__}")
                    self._registry[tool_name] = obj

    def get_class(self, name: str):
        if name:
            key = str(name).lower()
            if "powershell" in key or key in ("system.powershell", "powershell.safe.execute"):
                from runtime.tools.executors.powershell import PowerShellExecutor
                return PowerShellExecutor
            if "git" in key:
                from runtime.tools.executors.git import GitExecutor
                return GitExecutor
            if "file" in key or "filesystem" in key:
                from runtime.tools.executors.filesystem import FileSystemExecutor
                return FileSystemExecutor
        return self._classes.get(name)
