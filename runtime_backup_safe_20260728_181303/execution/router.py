from runtime.contracts.execution_context import ExecutionContext
from runtime.tools.tool_schema import ToolResult
from runtime.execution.sandbox import ExecutionSandbox
from runtime.external.base import ExternalExecutorBase
from runtime.external.supervisor import WorkerSupervisor

class ExecutionRouter:
    """Route de façon aveugle vers le monde Python Interne ou le monde OS Externe."""
    
    @staticmethod
    def route(context: ExecutionContext, executor_cls, project_root: str, **kwargs) -> ToolResult:
        mode = context.capability.execution_mode
        
        if mode == "external":
            if not issubclass(executor_cls, ExternalExecutorBase):
                raise TypeError(f"L'exécuteur {executor_cls.__name__} revendique 'external' mais n'hérite pas de ExternalExecutorBase.")
            instance = executor_cls()
            return WorkerSupervisor.run_worker(instance, context, project_root, **kwargs)
            
        elif mode == "internal":
            return ExecutionSandbox.run(context, executor_cls.execute, project_root, **kwargs)
            
        raise RuntimeError(f"Execution mode inconnu ou falsifié : {mode}")