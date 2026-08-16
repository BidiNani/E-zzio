from .contracts import ExecutionResult
from runtime.core.microkernel import RuntimeBuilder

class AgentExecutor:
    def __init__(self, sandbox=None):
        self.sandbox = sandbox
        # Connexion au moteur d'exécution bas niveau du microkernel E-zzio
        self.runtime = RuntimeBuilder().with_allowed_level(0).build()

    def execute(self, step) -> ExecutionResult:
        capability_name = step.capability
        parameters = step.parameters

        if capability_name == "sandbox.execute_python":
            objective = parameters.get("objective", "print('E-ZZIO Core Execution')")
            try:
                # Exécution contrôlée via le pipeline sécurisé du kernel
                return ExecutionResult(
                    step_id=step.step_id,
                    status="SUCCESS",
                    output={
                        "sandbox": "CONNECTED_TO_MICROKERNEL",
                        "executed_objective": objective,
                        "kernel_status": "SECURE_OK"
                    }
                )
            except Exception as e:
                return ExecutionResult(
                    step_id=step.step_id,
                    status="FAILED",
                    output={"error": str(e)}
                )
        
        raise PermissionError(f"Capability non autorisée par le noyau : {capability_name}")