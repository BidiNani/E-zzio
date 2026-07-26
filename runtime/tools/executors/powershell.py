import subprocess
import logging
import os
from runtime.contracts.execution_context import ExecutionContext
from runtime.contracts.tool_result import ToolResult
from runtime.execution.decorators import executor
from runtime.security.guard import OutputGuard

logger = logging.getLogger("Ezzio.PowerShellExecutor")

@executor
class PowerShellExecutor:
    TOOL_NAME = "system.powershell"
    SECURITY_LEVEL = "admin"
    VERSION = "2.2-industrial"
    AUDIT_SAFE = False

    def execute(self, context: ExecutionContext) -> ToolResult:
        arguments = context.arguments or {}
        script = arguments.get("script") or arguments.get("command")

        if not script:
            return ToolResult(success=False, error="Missing required 'script' or 'command' argument", exit_code=-1)

        process = None
        try:
            creation_flags = subprocess.CREATE_NEW_PROCESS_GROUP if os.name == 'nt' else 0
            
            logger.info(f"Executing PowerShell [Trace: {context.trace_id}]")
            process = subprocess.Popen(
                ["powershell", "-NoProfile", "-NonInteractive", "-Command", script],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                creationflags=creation_flags
            )

            try:
                stdout_data, stderr_data = process.communicate(timeout=60)
            except subprocess.TimeoutExpired:
                if os.name == 'nt' and process:
                    try:
                        subprocess.run(
                            ["taskkill", "/F", "/T", "/PID", str(process.pid)],
                            capture_output=True,
                            timeout=5
                        )
                    except Exception as tk_err:
                        logger.error(f"Taskkill tree termination failed: {tk_err}")
                else:
                    process.kill()
                
                return ToolResult(success=False, error="Execution timed out (Process Tree Hard Killed via TaskKill).", exit_code=-124)

            safe_output = OutputGuard.sanitize(stdout_data.strip()) if stdout_data else ""
            safe_error = OutputGuard.sanitize(stderr_data.strip()) if stderr_data else ""

            return ToolResult(
                success=(process.returncode == 0),
                output=safe_output,
                error=safe_error,
                exit_code=process.returncode
            )

        except Exception as e:
            logger.exception(f"PowerShell executor failed: {e}")
            if process and process.poll() is None:
                try:
                    process.kill()
                except:
                    pass
            return ToolResult(success=False, error=str(e), exit_code=-1)