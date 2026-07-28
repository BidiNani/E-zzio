from runtime.tools.base import ToolResult
from runtime.external.base import ExternalExecutorBase



class PowerShellExecutor(ExternalExecutorBase):
    def spawn(self, *args, **kwargs): return None
    def is_alive(self, *args, **kwargs): return False
    def collect_output(self, *args, **kwargs): return ""
    def terminate(self, *args, **kwargs): pass


    # --- ABC IMPLEMENTATION STUBS ---
    @classmethod
    def execute(cls, context, *args, **kwargs):

        command=context.arguments.get("command")

        try:

            r=subprocess.run(
                [
                    "powershell",
                    "-Command",
                    command
                ],
                capture_output=True,
                text=True,
                timeout=10
            )


            output=r.stdout[:10000]

            return dict(
                success=r.returncode==0,
                output=output,
                error=r.stderr
            )


        except Exception as e:

            return dict(
                success=False,
                output="",
                error=str(e)
            )
