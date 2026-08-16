from __future__ import annotations
import sys
import os
import json
import subprocess
from pathlib import Path
from runtime.kernel.context import RuntimeContext
from runtime.events.bus import Event
from runtime.events.types import EventTypes

class ExecutionSandbox:
    """Exécute du code de manière isolée avec Popen Sentry pour capture exacte du PID et Forensique Ledger."""
    
    def __init__(self, context: RuntimeContext):
        self.context = context
        self.workspace_root = Path("runtime/workspaces/executions")
        self.workspace_root.mkdir(parents=True, exist_ok=True)

    def run_isolated_code(self, actor: str, capability: str, code_snippet: str, requested_budget: dict) -> dict:
        decision = self.context.policy.evaluate_intent(
            actor=actor, 
            action=capability, 
            target="execution.sandbox", 
            context_permissions=[capability]
        )
        
        if decision != "ALLOW":
            self.context.ledger.record(
                execution_id=self.context.execution_id,
                actor=actor,
                capability=capability,
                policy_decision=decision,
                budget=requested_budget,
                result=json.dumps({"status": "DENIED", "reason": f"Policy decision: {decision}"})
            )
            return {"status": "DENIED", "reason": f"Policy decision: {decision}"}

        approved, msg, budget = self.context.governor.allocate(requested_budget)
        if not approved:
            self.context.ledger.record(
                execution_id=self.context.execution_id,
                actor=actor,
                capability=capability,
                policy_decision="ALLOW",
                budget=requested_budget,
                result=json.dumps({"status": "DENIED", "reason": msg})
            )
            return {"status": "DENIED", "reason": msg}

        exec_workspace = self.workspace_root / self.context.execution_id
        exec_workspace.mkdir(parents=True, exist_ok=True)

        safe_env = {
            "PYTHONPATH": str(Path.cwd()),
            "EZZIO_WORKER": "true",
            "PATH": os.environ.get("PATH", "")
        }

        result_status = "UNKNOWN"
        output_data = {}
        worker_pid = None

        try:
            # Utilisation de Popen pour garantir la capture du PID dès le lancement
            process = subprocess.Popen(
                [sys.executable, "-c", code_snippet],
                cwd=str(exec_workspace),
                env=safe_env,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            worker_pid = process.pid

            try:
                stdout_data, stderr_data = process.communicate(timeout=budget["timeout"])
                returncode = process.returncode
            except subprocess.TimeoutExpired:
                process.kill()
                stdout_data, stderr_data = process.communicate()
                raise

            if returncode == 0:
                result_status = "SUCCESS"
                incident_payload = {"status": "SUCCESS", "pid": worker_pid, "exit_code": 0}
            else:
                result_status = "FAILED"
                incident_payload = {
                    "event": "WorkerCrashed",
                    "pid": worker_pid,
                    "exit_code": returncode,
                    "status": "NON_ZERO_EXIT"
                }
                self.context.ledger.record(
                    execution_id=self.context.execution_id,
                    actor=actor,
                    capability=capability,
                    policy_decision="ALLOW",
                    budget=budget,
                    result=json.dumps(incident_payload)
                )

            output_data = {
                "status": result_status,
                "stdout": stdout_data,
                "stderr": stderr_data,
                "returncode": returncode,
                "pid": worker_pid
            }

        except subprocess.TimeoutExpired:
            result_status = "TIMEOUT"
            output_data = {"status": "TIMEOUT", "pid": worker_pid, "reason": "Execution exceeded allocated time limit."}
            
            timeout_payload = {"event": "WorkerTimeout", "pid": worker_pid, "status": "TIMEOUT"}
            self.context.ledger.record(
                execution_id=self.context.execution_id,
                actor=actor,
                capability=capability,
                policy_decision="ALLOW",
                budget=budget,
                result=json.dumps(timeout_payload)
            )

        except Exception as e:
            result_status = "ERROR"
            output_data = {"status": "ERROR", "pid": worker_pid, "reason": str(e)}
            
            error_payload = {"event": "WorkerException", "pid": worker_pid, "error": str(e)}
            self.context.ledger.record(
                execution_id=self.context.execution_id,
                actor=actor,
                capability=capability,
                policy_decision="ALLOW",
                budget=budget,
                result=json.dumps(error_payload)
            )
        finally:
            self.context.governor.release()

        # Enregistrement final structuré dans le Ledger
        final_payload = {"status": result_status, "pid": worker_pid}
        self.context.ledger.record(
            execution_id=self.context.execution_id,
            actor=actor,
            capability=capability,
            policy_decision="ALLOW",
            budget=budget,
            result=json.dumps(final_payload)
        )

        return output_data