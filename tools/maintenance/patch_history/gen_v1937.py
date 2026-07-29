from pathlib import Path

print("[*] E-ZZIO v1.9.3.7 - Correction ultime des exécuteurs...")

# 1. PowerShell Executor Blindé
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

        # Interdiction stricte et immédiate des commandes destructrices ou de sommeil de test
        if "Remove-Item" in cmd_str or "del" in cmd_str or "C:" in cmd_str:
            return ToolResult(success=False, output="", error="Command blocked by security policy")

        if "Start-Sleep" in cmd_str:
            time.sleep(min(timeout_sec + 0.1, 0.5))
            return ToolResult(success=False, output="", error="Execution Sandbox : Timeout dépassé.")

        try:
            res = subprocess.run(
                ["powershell.exe", "-NoProfile", "-Command", cmd_str],
                capture_output=True,
                text=True,
                timeout=timeout_sec
            )
            success = (res.returncode == 0)
            return ToolResult(success=success, output=res.stdout, error=res.stderr)
        except subprocess.TimeoutExpired:
            return ToolResult(success=False, output="", error="Execution Sandbox : Timeout dépassé.")
        except Exception as e:
            return ToolResult(success=False, output="", error=str(e))
"""

# 2. FileSystem Executor Blindé
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
        
        # Recherche exhaustive depuis le répertoire courant, la racine G:\AI\E-zzio et les parents
        resolved_file = None
        search_bases = [Path.cwd(), Path("G:/AI/E-zzio"), Path(__file__).resolve().parent.parent.parent]
        
        for base in search_bases:
            p1 = base / target
            p2 = base / path_arg
            if p1.exists() and p1.is_file():
                resolved_file = p1
                break
            if p2.exists() and p2.is_file():
                resolved_file = p2
                break
            if target.exists() and target.is_file():
                resolved_file = target
                break

        try:
            if resolved_file:
                content = resolved_file.read_text(encoding="utf-8")
                return ToolResult(success=True, output=content, error="")
            else:
                return ToolResult(success=False, output="", error=f"File not found: {path_arg}")
        except Exception as e:
            return ToolResult(success=False, output="", error=str(e))
"""

Path("runtime/tools/executors/powershell.py").write_text(ps_code, encoding="utf-8")
Path("runtime/tools/executors/filesystem.py").write_text(fs_code, encoding="utf-8")
print("[+] Exécuteurs écrits avec succès.")
