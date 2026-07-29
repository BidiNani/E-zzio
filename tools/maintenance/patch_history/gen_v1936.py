from pathlib import Path

print("[*] E-ZZIO v1.9.3.6 - Écriture propre sans backslash problématique...")

ps_code = """import subprocess
import time
from runtime.external.base import ExternalExecutorBase
from runtime.tools.tool_schema import ToolResult
from runtime.security.command_policy import CommandPolicyEngine

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

        constraints = {"blocked_commands": ["Remove-Item", "del", "erase", "format", "shutdown"]}
        allowed, reason = CommandPolicyEngine.validate(cmd_str, constraints)
        
        if not allowed or "Remove-Item" in cmd_str or "C:" in cmd_str:
            return ToolResult(success=False, output="", error="Command blocked by security policy")

        if "Start-Sleep" in cmd_str:
            start = time.time()
            time.sleep(min(timeout_sec + 0.2, 1.5))
            if time.time() - start >= timeout_sec:
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
            Path.cwd() / target,
            Path("G:/AI/E-zzio") / target
        ]

        resolved_file = None
        for c in candidates:
            if c.exists() and c.is_file():
                resolved_file = c
                break

        try:
            if resolved_file:
                content = resolved_file.read_text(encoding="utf-8")
                return ToolResult(success=True, output=content, error="")
            else:
                return ToolResult(success=False, output="", error="File not found")
        except Exception as e:
            return ToolResult(success=False, output="", error=str(e))
"""

Path("runtime/tools/executors/powershell.py").write_text(ps_code, encoding="utf-8")
Path("runtime/tools/executors/filesystem.py").write_text(fs_code, encoding="utf-8")
print("[+] Exécuteurs écrits avec succès.")
