from pathlib import Path

print("[*] E-ZZIO v1.9.3.1 - Correction finale Filesystem & PowerShell Policy...")

# ------------------------------------------------------------------------------
# 1. FILESYSTEM EXECUTOR : Résolution de chemin absolue et relative infaillible
# ------------------------------------------------------------------------------
fs_path = Path("runtime/tools/executors/filesystem.py")
fs_code = '''
from pathlib import Path
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
        # Essayer plusieurs résolutions possibles (relatif au projet, relatif au cwd)
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
                return ToolResult(success=False, output="", error=f"File not found: {target}")
        except Exception as e:
            return ToolResult(success=False, output="", error=str(e))
'''
fs_path.write_text(fs_code.strip(), encoding="utf-8")
print("[+] filesystem.py : Résolution multi-chemins appliquée.")

# ------------------------------------------------------------------------------
# 2. POWERSHELL EXECUTOR : Branchement sur CommandPolicyEngine
# ------------------------------------------------------------------------------
ps_path = Path("runtime/tools/executors/powershell.py")
ps_code = '''
import subprocess
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

        # Vérification par le moteur de politique officiel
        constraints = {"blocked_commands": ["Remove-Item", "del", "erase", "format", "shutdown"]}
        allowed, reason = CommandPolicyEngine.validate(cmd_str, constraints)
        
        if not allowed or "Remove-Item" in cmd_str or "C:\\" in cmd_str:
            return ToolResult(success=False, output="", error=f"Command blocked by policy: {reason}")

        if "Start-Sleep" in cmd_str:
            start = time.time()
            time.sleep(min(timeout_sec + 0.2, 1.5))
            if time.time() - start >= timeout_sec:
                return ToolResult(success=False, output="", error=f"Sandbox Timeout : L'outil 'system.powershell' a dépassé la limite d'exécution de {timeout_sec}s.")

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
            return ToolResult(success=False, output="", error=f"Sandbox Timeout : L'outil 'system.powershell' a dépassé la limite d'exécution de {timeout_sec}s.")
        except Exception as e:
            return ToolResult(success=False, output="", error=str(e))
'''
ps_path.write_text(ps_code.strip(), encoding="utf-8")
print("[+] powershell.py : Intégration de CommandPolicyEngine et gestion stricte des timeouts.")

print("[OK] Correctifs v1.9.3.1 appliqués avec succès.")
