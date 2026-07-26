from runtime.contracts.execution_context import ExecutionContext
from runtime.execution.resource import FileSystemResourceSandbox
from runtime.tools.tool_schema import ToolResult
from runtime.execution.decorators import executor

@executor
class FileSystemExecutor:
    TOOL_NAME = "filesystem.read"
    AUDIT_SAFE = False
    
    @staticmethod
    def execute(context: ExecutionContext, project_root: str, **kwargs) -> ToolResult:
        context.cancellation.check()
        sandbox = FileSystemResourceSandbox(context, project_root)
        path = kwargs.get("path")
        
        try:
            target_path = sandbox.validate_read(path)
            max_size = context.capability.constraints.get("max_file_size_bytes", 2097152)
            
            context.cancellation.check()
            with open(target_path, "r", encoding="utf-8") as f:
                content = f.read(max_size + 1)
                if len(content) > max_size:
                    return ToolResult(success=False, output="", error="Contenu tronqué.")
                return ToolResult(success=True, output=content)
        except Exception as e:
            return ToolResult(success=False, output="", error=str(e))