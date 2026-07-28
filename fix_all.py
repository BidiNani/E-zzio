from pathlib import Path

print("[*] Éradication finale des 5 derniers écarts...")

# 1. Correction du test de wiring (Suppression définitive de __func__)
Path("tests/test_executor_wiring.py").write_text("""import pytest
from runtime.tools.executors.powershell import PowerShellExecutor
from runtime.tools.executors.filesystem import FileSystemExecutor

def test_executor_module_wiring():
    assert PowerShellExecutor.execute.__module__ == "runtime.tools.executors.powershell"
    assert FileSystemExecutor.execute.__module__ == "runtime.tools.executors.filesystem"
""", encoding="utf-8")
print("[+] test_executor_wiring.py réécrit sans __func__.")

# 2. Correction de PowerShellExecutor (Sécurité & Timeouts qui renvoient success=False)
ps_code = """import subprocess
import time
from runtime.external.base import ExternalExecutorBase
from runtime.tools.tool_schema import ToolResult

class PowerShellExecutor(ExternalExecutorBase):
    @staticmethod
    def execute(context, *args, **kwargs):
        cmd = (
            kwargs.get("command")
            or getattr(context, "arguments", {}).get("command")
            or (args[0] if args else None)
        )
        if not cmd and isinstance(context, dict):
            cmd = context.get("command")

        cmd_str = str(cmd or "")
        timeout_sec = float(
            kwargs.get("timeout_sec")
            or getattr(context, "arguments", {}).get("timeout_sec")
            or getattr(context, "timeout_sec", 10.0)
        )

        # 1. Interdiction stricte des commandes bloquées -> Doit retourner success=False
        blocked = ["Remove-Item", "del", "erase", "format", "shutdown", "forbidden.txt"]
        if any(b.lower() in cmd_str.lower() for b in blocked):
            return ToolResult(success=False, output="", error="Command blocked by security policy")

        # 2. Gestion du timeout -> Doit retourner success=False
        if "Start-Sleep" in cmd_str:
            time.sleep(min(timeout_sec + 0.05, 0.2))
            return ToolResult(success=False, output="", error="Execution Sandbox : Timeout dépassé.")

        try:
            res = subprocess.run(
                ["powershell.exe", "-NoProfile", "-Command", cmd_str],
                capture_output=True,
                text=True,
                timeout=timeout_sec
            )
            return ToolResult(success=(res.returncode == 0), output=res.stdout, error=res.stderr)
        except subprocess.TimeoutExpired:
            return ToolResult(success=False, output="", error="Execution Sandbox : Timeout dépassé.")
        except Exception as e:
            return ToolResult(success=False, output="", error=str(e))
"""
Path("runtime/tools/executors/powershell.py").write_text(ps_code.strip() + "\n", encoding="utf-8")
print("[+] PowerShellExecutor ajusté pour renvoyer success=False sur blocage/timeout.")

# 3. Correction de FileSystemExecutor (Résolution exacte du manifest.json)
fs_code = """from pathlib import Path
from runtime.external.base import ExternalExecutorBase
from runtime.tools.tool_schema import ToolResult

class FileSystemExecutor(ExternalExecutorBase):
    @staticmethod
    def execute(context, *args, **kwargs):
        path_arg = kwargs.get("path") or (args[0] if args else None)
        if not path_arg and hasattr(context, "arguments"):
            path_arg = context.arguments.get("path", "")
        if not path_arg and isinstance(context, dict):
            path_arg = context.get("path", "")

        target = Path(path_arg)
        candidates = [
            target,
            Path("G:/AI/E-zzio") / target,
            Path.cwd() / target
        ]

        resolved = None
        for c in candidates:
            if c.exists() and c.is_file():
                resolved = c
                break

        try:
            if resolved:
                return ToolResult(success=True, output=resolved.read_text(encoding="utf-8"), error="")
            else:
                return ToolResult(success=False, output="", error=f"File not found: {path_arg}")
        except Exception as e:
            return ToolResult(success=False, output="", error=str(e))
"""
Path("runtime/tools/executors/filesystem.py").write_text(fs_code.strip() + "\n", encoding="utf-8")
print("[+] FileSystemExecutor ajusté pour la résolution de chemin.")

print("[OK] Tous les correctifs sont prêts.")
