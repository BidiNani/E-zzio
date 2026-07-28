from pathlib import Path

p=Path("runtime/execution/router.py")

p.write_text("""
from runtime.tools.tool_schema import ToolResult

class ExecutionRouter:

    @staticmethod
    def route(context, executor_cls, project_root, **kwargs):
        try:
            result = executor_cls.execute(
                context=context,
                **kwargs
            )

            if not isinstance(result, ToolResult):
                return ToolResult(
                    success=False,
                    output="",
                    error="Executor contract violation"
                )

            return result

        except Exception as e:
            return ToolResult(
                success=False,
                output="",
                error=str(e)
            )
""".strip()+"\n",encoding="utf-8")

print("[+] Router v1.9.5.4 aligné")
