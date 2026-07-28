from runtime.tools.base import ToolResult
from runtime.external.base import ExternalExecutorBase



class FileSystemExecutor(ExternalExecutorBase):
    def spawn(self, *args, **kwargs): return None
    def is_alive(self, *args, **kwargs): return False
    def collect_output(self, *args, **kwargs): return ""
    def terminate(self, *args, **kwargs): pass


    # --- ABC IMPLEMENTATION STUBS ---
    @classmethod
    def execute(cls, context, *args, **kwargs):

        path=kwargs.get("path") or context.arguments.get("path")

        try:
            with open(path,"r",encoding="utf-8") as f:
                data=f.read()

            return dict(
                success=True,
                output=data,
                error=""
            )

        except Exception as e:

            return dict(
                success=False,
                output="",
                error=str(e)
            )
