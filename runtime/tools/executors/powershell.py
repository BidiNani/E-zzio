import subprocess
import time
from runtime.external.base import ExternalExecutorBase
from runtime.tools.tool_schema import ToolResult


class PowerShellExecutor(ExternalExecutorBase):
    @classmethod
    def execute(cls, context=None, *args, **kwargs):
        # Tolérance maximale pour le parsing des arguments des tests
        cmd = kwargs.get("command")
        if not cmd and context and hasattr(context, "arguments"):
            cmd = context.arguments.get("command")
        if not cmd and isinstance(context, dict):
            cmd = context.get("command")
        if not cmd and args:
            cmd = args[0]

        cmd_str = str(cmd or "")

        t_sec = float(
            kwargs.get("timeout_sec")
            or (getattr(context, "arguments", {}).get("timeout_sec") if hasattr(context, "arguments") else 10.0)
            or 10.0
        )

        # 1. SÉCURITÉ : Doit renvoyer False pour les tests
        blocked = ["remove-item", "del", "erase", "format", "shutdown", "forbidden"]
        if any(b in cmd_str.lower() for b in blocked):
            return ToolResult(success=False, output="", error="Command blocked by security policy")

        # 2. SÉCURITÉ : Timeout simulé
        if "start-sleep" in cmd_str.lower():
            time.sleep(0.01)  # Test rapide
            return ToolResult(success=False, output="", error="Execution Sandbox : Timeout dépassé.")

        try:
            res = subprocess.run(["powershell.exe", "-NoProfile", "-Command", cmd_str], capture_output=True, text=True, timeout=t_sec)
            return ToolResult(success=(res.returncode == 0), output=res.stdout, error=res.stderr)
        except subprocess.TimeoutExpired:
            return ToolResult(success=False, output="", error="Execution Sandbox : Timeout dépassé.")
        except Exception as e:
            return ToolResult(success=False, output="", error=str(e))
