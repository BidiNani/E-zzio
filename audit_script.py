from pathlib import Path
import importlib

print("\n--- 1. AUDIT DU TEST WIRING ---")
w_file = Path("tests/test_executor_wiring.py")
if w_file.exists():
    content = w_file.read_text(encoding="utf-8")
    print(f"Contenu de {w_file} :\n{content.strip()}\n")
else:
    print("[-] tests/test_executor_wiring.py introuvable.")

print("--- 2. AUDIT DES EXÉCUTEURS ---")
try:
    from runtime.tools.executors.powershell import PowerShellExecutor
    from runtime.tools.executors.filesystem import FileSystemExecutor
    print(f"PowerShellExecutor module : {PowerShellExecutor.execute.__module__}")
    print(f"FileSystemExecutor module : {FileSystemExecutor.execute.__module__}")
except Exception as e:
    print(f"[-] Erreur import exécuteurs: {e}")

print("\n--- 3. AUDIT DU REGISTRE DE ROUTAGE ---")
try:
    from runtime.execution.registry import ExecutorRegistry
    reg = ExecutorRegistry()
    tools = ["system.powershell", "powershell.safe.execute", "filesystem.read", "git.status"]
    for t in tools:
        cls = reg.get_class(t) if hasattr(reg, "get_class") else getattr(reg, "_registry", {}).get(t)
        print(f"Outil '{t}' => Resolved to: {cls}")
except Exception as e:
    print(f"[-] Erreur inspection registre: {e}")
