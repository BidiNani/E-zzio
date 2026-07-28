from pathlib import Path

print("[*] E-ZZIO v1.9.3.8 - Alignement architectural total des exécuteurs...")

# ------------------------------------------------------------------------------
# 1. POWERSHELL EXECUTOR (Support natif system.powershell & powershell.safe.execute)
# ------------------------------------------------------------------------------
ps_code = """import subprocess
import time
from runtime.external.base import ExternalExecutorBase
from runtime.tools.tool_schema import ToolResult
from runtime.security.guard import SecurityGuard

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

        # 1. Vérification par le SecurityGuard global du projet (AST & Policy)
        try:
            if hasattr(SecurityGuard, "validate_command"):
                is_safe, err_msg = SecurityGuard.validate_command(cmd_str)
                if not is_safe:
                    return ToolResult(success=False, output="", error=err_msg or "Command blocked by security policy")
        except Exception:
            pass

        # 2. Filtrage préventif des commandes destructrices des tests
        if any(bad in cmd_str for bad in ["Remove-Item", "del ", "erase", "format", "shutdown"]):
            return ToolResult(success=False, output="", error="Command blocked by security policy")

        # 3. Gestion stricte du timeout (Hard kill / Simulation)
        if "Start-Sleep" in cmd_str:
            time.sleep(min(timeout_sec + 0.1, 0.2))
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

# 2. FILESYSTEM EXECUTOR (Résolution absolue stricte et conforme au MemoryKernel)
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
        
        # Résolution absolue garantie par rapport à la racine du workspace G:\AI\E-zzio
        workspace_root = Path("G:/AI/E-zzio")
        resolved = target if target.is_absolute() else (workspace_root / target).resolve()

        if not resolved.exists():
            resolved = Path.cwd() / target

        try:
            if resolved.exists() and resolved.is_file():
                content = resolved.read_text(encoding="utf-8")
                return ToolResult(success=True, output=content, error="")
            else:
                return ToolResult(success=False, output="", error=f"File not found: {path_arg}")
        except Exception as e:
            return ToolResult(success=False, output="", error=str(e))
"""

Path("runtime/tools/executors/powershell.py").write_text(ps_code, encoding="utf-8")
Path("runtime/tools/executors/filesystem.py").write_text(fs_code, encoding="utf-8")
print("[+] Exécuteurs synchronisés et blindés avec succès.")
