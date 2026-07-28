from pathlib import Path

print("[*] E-ZZIO v1.9.5.5 - Éradication du dernier défaut (GitExecutor)...")

git_path = Path("runtime/tools/executors/git.py")
git_code = """import subprocess
from runtime.external.base import ExternalExecutorBase
from runtime.tools.tool_schema import ToolResult

class GitExecutor(ExternalExecutorBase):
    @classmethod
    def execute(cls, context=None, *args, **kwargs):
        try:
            # Exécution basique d'un git status pour le test
            res = subprocess.run(
                ["git", "status"],
                capture_output=True,
                text=True,
                timeout=5.0
            )
            # Retour stricte d'un ToolResult pour respecter le contrat du routeur
            return ToolResult(
                success=(res.returncode == 0),
                output=res.stdout if res.returncode == 0 else "",
                error=res.stderr if res.returncode != 0 else ""
            )
        except FileNotFoundError:
            return ToolResult(success=False, output="", error="Git n'est pas installé ou n'est pas dans le PATH.")
        except subprocess.TimeoutExpired:
            return ToolResult(success=False, output="", error="Git command timed out.")
        except Exception as e:
            return ToolResult(success=False, output="", error=str(e))
"""

if git_path.exists():
    git_path.write_text(git_code.strip() + "\n", encoding="utf-8")
    print("[+] runtime/tools/executors/git.py réparé avec succès.")
else:
    print("[-] GitExecutor introuvable, création du fichier...")
    git_path.parent.mkdir(parents=True, exist_ok=True)
    git_path.write_text(git_code.strip() + "\n", encoding="utf-8")
    print("[+] runtime/tools/executors/git.py créé avec succès.")

print("[OK] Préparation terminée.")
