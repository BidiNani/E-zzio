import logging
from runtime.contracts.execution_context import ExecutionContext
from runtime.contracts.tool_result import ToolResult
from runtime.execution.registry import ExecutorRegistry

logger = logging.getLogger("Ezzio.Supervisor")


class ExecutionSupervisor:
    def __init__(self, registry: ExecutorRegistry = None):
        self.registry = registry or ExecutorRegistry()

    def execute_tool(self, context: ExecutionContext) -> ToolResult:
        executor_cls = self.registry.get_class(context.tool_name)
        if not executor_cls:
            error_msg = f"Runtime Error: No registered executor found for '{context.tool_name}'"
            logger.error(error_msg)
            return ToolResult(success=False, error=error_msg, exit_code=-1)

        try:
            instance = executor_cls()
            logger.info(f"Supervisor delegating to {executor_cls.__name__} [Trace: {context.trace_id}]")
            result = instance.execute(context)

            if not isinstance(result, ToolResult):
                error_msg = f"Contract Violation: {executor_cls.__name__} returned {type(result)} instead of ToolResult."
                logger.error(error_msg)
                return ToolResult(success=False, error=error_msg, exit_code=-3)

            return result

        except Exception as e:
            logger.exception(f"Critical execution failure in Supervisor: {e}")
            return ToolResult(success=False, error=str(e), exit_code=-2)
