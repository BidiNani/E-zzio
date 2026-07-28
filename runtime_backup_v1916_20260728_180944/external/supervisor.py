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
            
            process = getattr(executor_instance, 'process', None)
            if process:
                isolator.assign(process)
                context.(state.get("metadata") if isinstance(state, dict) else getattr(state, "metadata", None))["pid"] = process.pid
            
            context.(state.get("metadata") if isinstance(state, dict) else getattr(state, "metadata", None))["executor"] = executor_instance.TOOL_NAME

            while executor_instance.is_alive():
                try:
                    context.cancellation.check()
                    guard.check_size_limits() # Watchdog Actif I/O Disque
                except InterruptedError as ie:
                    executor_instance.terminate(graceful_timeout=1.0)
                    return ToolResult(success=False, output="", error=f"Superviseur (Forced Stop): {str(ie)}")
                time.sleep(0.05)
            
            result = executor_instance.collect_output()
            if result and process:
                context.(state.get("metadata") if isinstance(state, dict) else getattr(state, "metadata", None))["exit_code"] = process.returncode
            return result or ToolResult(success=False, output="", error="Erreur de collecte.")

        except Exception as e:
            executor_instance.terminate(graceful_timeout=0.1)
            return ToolResult(success=False, output="", error=f"Superviseur Crash : {str(e)}")
        finally:
            isolator.close()