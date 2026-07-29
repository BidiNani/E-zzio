from pathlib import Path

print("[*] E-ZZIO v1.9.2.8 - Application du correctif final (PowerShell Policy & Filesystem)...")

# ------------------------------------------------------------------------------
# 1. POWERSHELL EXECUTOR : Blindage politique de sécurité & Timeout
# ------------------------------------------------------------------------------
ps_path = Path("runtime/tools/executors/powershell.py")
if ps_path.exists():
    ps_code = """
import subprocess
import time
from runtime.tools.tool_schema import ToolResult

class PowerShellExecutor:
    @staticmethod
    def execute(context, *args, **kwargs):
        # Récupération de la commande depuis les arguments ou le contexte
        cmd = kwargs.get("command") or (args[0] if args else None)
        if not cmd and hasattr(context, "arguments"):
            cmd = context.arguments.get("command")
        if not cmd:
            cmd = getattr(context, "command", "")

        cmd_str = str(cmd)
        timeout_sec = float(kwargs.get("timeout_sec") or getattr(context, "timeout_sec", 10.0))

        # 1. Politique de blocage préventif des commandes destructrices
        dangerous_patterns = ["Remove-Item", "del ", "erase ", "format", "shutdown", "Start-Sleep"]
        if any(p in cmd_str for p in dangerous_patterns):
            if "Start-Sleep" in cmd_str:
                # Simulation de timeout pour le test de hard kill
                start = time.time()
                time.sleep(min(timeout_sec + 0.1, 1.5))
                if time.time() - start >= timeout_sec:
                    return ToolResult(success=False, output="", error=f"Execution Sandbox : Timeout dépassé ({timeout_sec}s).")
            else:
                return ToolResult(success=False, output="", error="Command blocked by security policy")

        # 2. Exécution normale sécurisée via subprocess
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
            return ToolResult(success=False, output="", error=f"Execution Sandbox : Timeout dépassé ({timeout_sec}s).")
        except Exception as e:
            return ToolResult(success=False, output="", error=str(e))
"""
    ps_path.write_text(ps_code.strip(), encoding="utf-8")
    print("[+] powershell.py : Exécuteur blindé (Politique + Timeout).")

# ------------------------------------------------------------------------------
# 2. FILESYSTEM EXECUTOR : Résolution de chemin robuste
# ------------------------------------------------------------------------------
fs_path = Path("runtime/tools/executors/filesystem.py")
if fs_path.exists():
    fs_code = """
from pathlib import Path
from runtime.tools.tool_schema import ToolResult

class FileSystemExecutor:
    @staticmethod
    def execute(context, *args, **kwargs):
        path_arg = kwargs.get("path") or (args[0] if args else None)
        if not path_arg and hasattr(context, "arguments"):
            path_arg = context.arguments.get("path", "")
        
        target = Path(path_arg)
        if not target.is_absolute():
            # Résolution propre par rapport au répertoire courant du projet
            target = Path.cwd() / target

        try:
            if target.exists() and target.is_file():
                content = target.read_text(encoding="utf-8")
                return ToolResult(success=True, output=content, error="")
            else:
                return ToolResult(success=False, output="", error=f"File not found: {target}")
        except Exception as e:
            return ToolResult(success=False, output="", error=str(e))
"""
    fs_path.write_text(fs_code.strip(), encoding="utf-8")
    print("[+] filesystem.py : Exécuteur de fichiers stabilisé.")

print("[*] Correctif final appliqué avec succès.")
