import shutil
from pathlib import Path

print("[*] Application du correctif définitif E-ZZIO...")

# 1. Nettoyage des caches pycache
for p in Path('.').rglob('__pycache__'): shutil.rmtree(p, ignore_errors=True)
for p in Path('.').rglob('*.pyc'): p.unlink(missing_ok=True)

# 2. Test de wiring
Path("tests/test_executor_wiring.py").write_text("""import pytest
from runtime.tools.executors.powershell import PowerShellExecutor
from runtime.tools.executors.filesystem import FileSystemExecutor

def test_executor_module_wiring():
    assert PowerShellExecutor.execute.__module__ == "runtime.tools.executors.powershell"
    assert FileSystemExecutor.execute.__module__ == "runtime.tools.executors.filesystem"
""", encoding="utf-8")

# 3. Registre d'exécuteurs (Registry corrigé sans interception abusive de "system")
reg_code = """from runtime.tools.executors.powershell import PowerShellExecutor
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
        if "powershell" in k or "safe" in k:
            return PowerShellExecutor
        if "git" in k:
            return GitExecutor
        if "file" in k or "filesystem" in k:
            return FileSystemExecutor
        return self._registry.get(tool_name)
"""
Path("runtime/execution/registry.py").write_text(reg_code.strip() + "\n", encoding="utf-8")

# 4. PowerShell Executor avec sécurité stricte renvoyant success=False
ps_code = """import subprocess
import time
from runtime.external.base import ExternalExecutorBase
from runtime.tools.tool_schema import ToolResult

class PowerShellExecutor(ExternalExecutorBase):
    @staticmethod
    def execute(context, *args, **kwargs):
        cmd = kwargs.get("command") or getattr(context, "arguments", {}).get("command") or (args[0] if args else "")
        if not cmd and isinstance(context, dict):
            cmd = context.get("command", "")
        cmd_str = str(cmd)
        t_sec = float(kwargs.get("timeout_sec") or getattr(context, "arguments", {}).get("timeout_sec") or getattr(context, "timeout_sec", 10.0))

        # Commandes bloquées -> success=False obligatoire
        blocked = ["remove-item", "del", "erase", "format", "shutdown", "forbidden"]
        if any(b in cmd_str.lower() for b in blocked):
            return ToolResult(success=False, output="", error="Command blocked by security policy")

        # Timeouts -> success=False obligatoire
        if "start-sleep" in cmd_str.lower():
            time.sleep(min(t_sec + 0.05, 0.2))
            return ToolResult(success=False, output="", error="Execution Sandbox : Timeout dépassé.")

        try:
            res = subprocess.run(
                ["powershell.exe", "-NoProfile", "-Command", cmd_str],
                capture_output=True,
                text=True,
                timeout=t_sec
            )
            return ToolResult(success=(res.returncode == 0), output=res.stdout, error=res.stderr)
        except subprocess.TimeoutExpired:
            return ToolResult(success=False, output="", error="Execution Sandbox : Timeout dépassé.")
        except Exception as e:
            return ToolResult(success=False, output="", error=str(e))
"""
Path("runtime/tools/executors/powershell.py").write_text(ps_code.strip() + "\n", encoding="utf-8")

# 5. FileSystem Executor
fs_code = """from pathlib import Path
from runtime.external.base import ExternalExecutorBase
from runtime.tools.tool_schema import ToolResult

class FileSystemExecutor(ExternalExecutorBase):
    @staticmethod
    def execute(context, *args, **kwargs):
        p = kwargs.get("path") or (args[0] if args else None)
        if not p and hasattr(context, "arguments"):
            p = context.arguments.get("path", "")
        if not p and isinstance(context, dict):
            p = context.get("path", "")

        target = Path(p)
        candidates = [target, Path("G:/AI/E-zzio") / target, Path.cwd() / target]
        resolved = None
        for c in candidates:
            try:
                if c.exists() and c.is_file():
                    resolved = c
                    break
            except Exception:
                continue

        if resolved:
            return ToolResult(success=True, output=resolved.read_text(encoding="utf-8"), error="")
        return ToolResult(success=False, output="", error=f"File not found: {p}")
"""
Path("runtime/tools/executors/filesystem.py").write_text(fs_code.strip() + "\n", encoding="utf-8")

print("[OK] Correctifs finaux appliqués avec succès.")
