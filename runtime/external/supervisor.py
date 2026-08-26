import time
from runtime.contracts.execution_context import ExecutionContext
from runtime.external.base import ExternalExecutorBase
from runtime.external.platform.windows import WindowsProcessIsolator
from runtime.external.output_guard import OutputGuard
from runtime.tools.tool_schema import ToolResult


class WorkerSupervisor:
    @staticmethod
    def run_worker(executor_instance: ExternalExecutorBase, context: ExecutionContext, project_root: str, **kwargs) -> ToolResult:
        isolator = WindowsProcessIsolator()
        guard = OutputGuard()

        try:
            executor_instance.spawn(context, project_root, guard=guard, **kwargs)

            process = getattr(executor_instance, "process", None)
            if process:
                isolator.assign(process)
                st = getattr(context, "state", {})
                if isinstance(st, dict):
                    st.setdefault("metadata", {})["pid"] = process.pid

            st = getattr(context, "state", {})
            if isinstance(st, dict):
                st.setdefault("metadata", {})["executor"] = getattr(executor_instance, "TOOL_NAME", "unknown")

            while executor_instance.is_alive():
                try:
                    if hasattr(executor_instance, "collect_output"):
                        chunk = executor_instance.collect_output()
                        if chunk:
                            guard.feed(chunk)
                except Exception:
                    pass
                time.sleep(0.05)

            output = guard.get_output()
            error = guard.get_error()
            success = guard.is_success()

            return ToolResult(success=success, output=output, error=error)

        except Exception as e:
            return ToolResult(success=False, output="", error=str(e))
        finally:
            try:
                executor_instance.terminate()
            except Exception:
                pass
