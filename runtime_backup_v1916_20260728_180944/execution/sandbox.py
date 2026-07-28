import concurrent.futures
from runtime.contracts.execution_context import ExecutionContext
from runtime.tools.tool_schema import ToolResult

class ExecutionSandbox:
    """Isole l'exécution dans le temps et l'espace (Gère la Cancellation et les Timeouts)."""
    
    @staticmethod
    def run(context: ExecutionContext, func, *args, **kwargs) -> ToolResult:
        # Vérification d'expiration du token éphémère avant exécution
        if not context.capability.is_valid():
            return ToolResult(success=False, output="", error="Execution Sandbox : Token expiré.")

        timeout = context.capability.timeout_sec

        # Isolation selon le type d'exécuteur déclaré dans le manifest
        if context.capability.executor_type == "subprocess":
            # Préparation pour la Phase 5.1 (Git, PowerShell)
            # Implémentera `subprocess.run(..., timeout=timeout, capture_output=True)`
            return ToolResult(success=False, output="", error="Subprocess executor not implemented yet.")
        else:
            # Type "python" : Thread coopératif
            with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
                future = executor.submit(func, context, *args, **kwargs)
                try:
                    return future.result(timeout=timeout)
                except concurrent.futures.TimeoutError:
                    return ToolResult(success=False, output="", error=f"Execution Sandbox : Timeout dépassé ({timeout}s).")
                except Exception as e:
                    return ToolResult(success=False, output="", error=f"Execution Sandbox Crash : {str(e)}")