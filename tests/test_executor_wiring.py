import pytest
from runtime.tools.executors.powershell import PowerShellExecutor
from runtime.tools.executors.filesystem import FileSystemExecutor

def test_executor_module_wiring():
    """Vérifie que les exécuteurs officiels respectent les contrats d'intégrité architecturale."""
    assert PowerShellExecutor.execute.__func__.__module__ == "runtime.tools.executors.powershell"
    assert FileSystemExecutor.execute.__func__.__module__ == "runtime.tools.executors.filesystem"
