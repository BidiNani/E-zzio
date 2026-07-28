from runtime.tools.base import ToolResult
import subprocess
from runtime.external.base import ExternalExecutorBase



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
            return dict(
                success=(res.returncode == 0),
                output=res.stdout,
                error=res.stderr
            )
        except Exception as e:
            return ToolResult(success=False, output="", error=str(e))
