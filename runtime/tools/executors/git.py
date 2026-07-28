import subprocess
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
