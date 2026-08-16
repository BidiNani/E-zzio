import uuid
import time
import psutil
from runtime.hardware.router.executor import AffinityExecutor

class TransactionalAffinityManager:
    def __init__(self, executor: AffinityExecutor):
        self.executor = executor

    def execute_transaction(self, plan: dict) -> dict:
        """
        Exécute un plan d'affinité sous forme de transaction atomique :
        BEGIN -> EXECUTE -> VERIFY -> COMMIT (ou ROLLBACK automatique)
        """
        op_id = str(uuid.uuid4())
        start_time = time.time()
        pid = self.executor.pid

        # 1. Capture de l'état initial (Baseline avant modification)
        try:
            p = psutil.Process(pid)
            initial_affinity = p.cpu_affinity()
        except Exception as e:
            return {
                "tx_status": "ROLLED_BACK",
                "operation_id": op_id,
                "duration_ms": round((time.time() - start_time) * 1000, 3),
                "reason": f"INITIAL_STATE_CAPTURE_FAILED: {str(e)}"
            }

        # 2. Exécution via l'Execution Safety Layer (PLAN -> VALIDATE -> EXECUTE -> VERIFY)
        exec_result = self.executor.execute_plan(plan)

        # 3. Évaluation de l'issue (COMMIT ou ROLLBACK)
        duration = round((time.time() - start_time) * 1000, 3)

        if exec_result.get("execution_status") == "EXECUTED_VERIFIED":
            return {
                "tx_status": "COMMITTED",
                "operation_id": op_id,
                "duration_ms": duration,
                "initial_affinity": initial_affinity,
                "applied_affinity": exec_result.get("applied"),
                "execution_details": exec_result
            }
        else:
            # 4. ROLLBACK D'URGENCE (Restauration stricte de l'état initial)
            rollback_success = False
            rollback_error = None
            try:
                p.cpu_affinity(initial_affinity)
                current_after_rollback = p.cpu_affinity()
                rollback_success = (set(current_after_rollback) == set(initial_affinity))
            except Exception as rb_e:
                rollback_error = str(rb_e)

            return {
                "tx_status": "ROLLED_BACK",
                "operation_id": op_id,
                "duration_ms": duration,
                "reason": exec_result.get("reason", "EXECUTION_VERIFICATION_FAILED"),
                "rollback_verified": rollback_success,
                "rollback_error": rollback_error,
                "execution_details": exec_result
            }
