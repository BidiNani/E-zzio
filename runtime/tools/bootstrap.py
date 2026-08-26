from runtime.tools.executors.powershell import PowerShellExecutor
from runtime.tools.executors.filesystem import FileSystemExecutor
from runtime.tools.executors.git import GitExecutor


def register_core_tools(registry):
    # Enregistrement standardisé et direct des CLASSE (et non des méthodes)
    registry.register("system.powershell", PowerShellExecutor)
    registry.register("powershell.safe.execute", PowerShellExecutor)
    registry.register("filesystem.read", FileSystemExecutor)
    registry.register("git.status", GitExecutor)

    # Rétrocompatibilité si le registre attend la méthode statique/classe
    if hasattr(registry, "_registry"):
        registry._registry["system.powershell"] = PowerShellExecutor
        registry._registry["powershell.safe.execute"] = PowerShellExecutor
        registry._registry["filesystem.read"] = FileSystemExecutor
