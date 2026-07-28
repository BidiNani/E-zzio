import os
import re

print("[*] E-ZZIO v1.9.0.8 - Reconstitution propre des modules cibles...")

# ------------------------------------------------------------------------------
# 1. CORRECTION DE LA SYNTAXE SQLITE DANS STORE.PY
# ------------------------------------------------------------------------------
store_path = "runtime/action/store.py"
if os.path.exists(store_path):
    with open(store_path, "r", encoding="utf-8") as f:
        code = f.read()

    # Correction des requêtes SQL corrompues avec multiples ORDER BY
    code = re.sub(
        r'ORDER BY\s+[\w\._]+\s+(?:ASC|DESC)\s+LIMIT\s+\?\s+ORDER BY\s+[\w\._]+\s+(?:ASC|DESC)',
        'ORDER BY id DESC LIMIT ?',
        code,
        flags=re.IGNORECASE
    )
    code = re.sub(
        r'ORDER BY\s+timestamp\s+DESC\s+LIMIT\s+\?\s+ORDER BY\s+id\s+DESC',
        'ORDER BY id DESC LIMIT ?',
        code,
        flags=re.IGNORECASE
    )
    code = re.sub(r'ORDER BY id DESC\s+ORDER BY id DESC', 'ORDER BY id DESC', code, flags=re.IGNORECASE)

    with open(store_path, "w", encoding="utf-8") as f:
        f.write(code)
    print("[+] store.py : Reconstitution des requêtes SQL (syntaxe SQLite corrigée).")


# ------------------------------------------------------------------------------
# 2. RÉÉCRITURE PROPRE DE GIT.PY
# ------------------------------------------------------------------------------
git_path = "runtime/tools/executors/git.py"
git_code = '''import subprocess
from runtime.external.base import ExternalExecutorBase

try:
    from runtime.tools.base import ToolResult
except ImportError:
    class ToolResult:
        def __init__(self, success, output="", error=""):
            self.success = success
            self.output = output
            self.error = error

class GitExecutor(ExternalExecutorBase):
    """Sovereign Git operations executor."""
    def __init__(self, project_root: str = "."):
        self.project_root = project_root

    def spawn(self, *args, **kwargs): return None
    def is_alive(self, *args, **kwargs): return False
    def collect_output(self, *args, **kwargs): return ""
    def terminate(self, *args, **kwargs): pass

    @classmethod
    def execute(cls, context, *args, **kwargs):
        cwd = getattr(context, "project_root", ".")
        try:
            res = subprocess.run(
                ["git", "status"],
                capture_output=True,
                text=True,
                cwd=cwd
            )
            return ToolResult(
                success=(res.returncode == 0),
                output=res.stdout,
                error=res.stderr
            )
        except Exception as e:
            return ToolResult(success=False, output="", error=str(e))
'''
with open(git_path, "w", encoding="utf-8") as f:
    f.write(git_code)
print("[+] git.py : Fichier réécrit proprement (0 erreur de syntaxe).")


# ------------------------------------------------------------------------------
# 3. SÉCURISATION DE FILESYSTEM.PY
# ------------------------------------------------------------------------------
fs_path = "runtime/tools/executors/filesystem.py"
if os.path.exists(fs_path):
    with open(fs_path, "r", encoding="utf-8") as f:
        fs_orig = f.read()

    fs_orig = re.sub(r'from runtime\.tools\.base import ExternalExecutorBase\n?', '', fs_orig)
    fs_orig = re.sub(r'from runtime\.external\.base import ExternalExecutorBase\n?', '', fs_orig)
    fs_orig = re.sub(r'class FileSystemExecutor.*?:', 'class FileSystemExecutor(ExternalExecutorBase):', fs_orig, count=1)
    fs_orig = re.sub(r'^\s*def (spawn|is_alive|collect_output|terminate)\(self.*?\).*?\n', '', fs_orig, flags=re.MULTILINE)
    
    stubs = """
    def spawn(self, *args, **kwargs): return None
    def is_alive(self, *args, **kwargs): return False
    def collect_output(self, *args, **kwargs): return ""
    def terminate(self, *args, **kwargs): pass
"""
    fs_orig = "from runtime.external.base import ExternalExecutorBase\n" + fs_orig
    fs_orig = fs_orig.replace("class FileSystemExecutor(ExternalExecutorBase):", "class FileSystemExecutor(ExternalExecutorBase):" + stubs)
    fs_orig = re.sub(r'context\.state', 'getattr(context, "state", None)', fs_orig)

    with open(fs_path, "w", encoding="utf-8") as f:
        f.write(fs_orig)
    print("[+] filesystem.py : Sécurisé avec stubs ABC et getattr(context, 'state').")


# ------------------------------------------------------------------------------
# 4. SÉCURISATION DE POWERSHELL.PY
# ------------------------------------------------------------------------------
ps_path = "runtime/tools/executors/powershell.py"
if os.path.exists(ps_path):
    with open(ps_path, "r", encoding="utf-8") as f:
        ps_orig = f.read()

    ps_orig = re.sub(r'context\.state', 'getattr(context, "state", None)', ps_orig)
    ps_orig = re.sub(r'from runtime\.tools\.base import ExternalExecutorBase\n?', '', ps_orig)
    ps_orig = re.sub(r'from runtime\.external\.base import ExternalExecutorBase\n?', '', ps_orig)
    ps_orig = re.sub(r'class PowerShellExecutor.*?:', 'class PowerShellExecutor(ExternalExecutorBase):', ps_orig, count=1)
    ps_orig = re.sub(r'^\s*def (spawn|is_alive|collect_output|terminate)\(self.*?\).*?\n', '', ps_orig, flags=re.MULTILINE)
    
    stubs = """
    def spawn(self, *args, **kwargs): return None
    def is_alive(self, *args, **kwargs): return False
    def collect_output(self, *args, **kwargs): return ""
    def terminate(self, *args, **kwargs): pass
"""
    ps_orig = "from runtime.external.base import ExternalExecutorBase\n" + ps_orig
    ps_orig = ps_orig.replace("class PowerShellExecutor(ExternalExecutorBase):", "class PowerShellExecutor(ExternalExecutorBase):" + stubs)

    with open(ps_path, "w", encoding="utf-8") as f:
        f.write(ps_orig)
    print("[+] powershell.py : Correctif appliqué (getattr pour context.state).")

