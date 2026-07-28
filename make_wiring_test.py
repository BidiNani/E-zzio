from pathlib import Path

test_code = """import pytest
from runtime.tools.executors.powershell import PowerShellExecutor
from runtime.tools.executors.filesystem import FileSystemExecutor

def test_executor_module_wiring():
    \"\"\"Vérifie que les exécuteurs officiels respectent les contrats d'intégrité architecturale.\"\"\"
    assert PowerShellExecutor.execute.__func__.__module__ == "runtime.tools.executors.powershell"
    assert FileSystemExecutor.execute.__func__.__module__ == "runtime.tools.executors.filesystem"
"""

Path("tests/test_executor_wiring.py").write_text(test_code.strip() + "\n", encoding="utf-8")
print("[+] Test d'intégrité architecturale créé.")
