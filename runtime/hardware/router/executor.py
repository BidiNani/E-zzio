import psutil
import os
from runtime.hardware.router.gate import AllocationIntegrityGate


class AffinityExecutor:
    def __init__(self, pid: int = None):
        # Par défaut, cible le processus courant (ou un PID spécifique supervisé)
        self.pid = pid or os.getpid()

    def execute_plan(self, plan: dict) -> dict:
        """
        Exécute et vérifie réellement l'affinité OS selon le cycle sécurisé :
        PLAN -> VALIDATE -> EXECUTE -> VERIFY
        """
        # 1. Vérification stricte du statut du plan de routage
        if plan.get("status") != "APPROVED":
            return {"execution_status": "SKIPPED_NOT_APPROVED", "reason": f"Plan status is '{plan.get('status')}'"}

        # 2. Respect absolu du mode Dry-Run (Zéro effet de bord)
        if plan.get("mode") == "DRY_RUN":
            return {"execution_status": "DRY_RUN_SKIPPED", "plan_target": plan.get("target"), "affinity_mask": plan.get("affinity_mask")}

        affinity_mask = plan.get("affinity_mask", [])

        # 3. Validation de l'intégrité du masque au moment exact de l'exécution
        max_threads = psutil.cpu_count(logical=True) or 1
        if not AllocationIntegrityGate.validate_allocation(affinity_mask, max_threads):
            return {"execution_status": "EXECUTION_FAILED", "reason": "INVALID_AFFINITY_MASK_AT_EXECUTION"}

        # 4. Vérification de l'existence et de la vitalité du processus cible
        try:
            p = psutil.Process(self.pid)
            if not p.is_running():
                return {"execution_status": "EXECUTION_FAILED", "reason": "TARGET_PROCESS_NOT_RUNNING"}
        except psutil.NoSuchProcess:
            return {"execution_status": "EXECUTION_FAILED", "reason": "PROCESS_NOT_FOUND"}
        except Exception as e:
            return {"execution_status": "EXECUTION_FAILED", "reason": f"PROCESS_ACCESS_ERROR: {str(e)}"}

        # 5. Tentative d'exécution OS (EXECUTION_ATTEMPTED -> OS_RESULT)
        try:
            p.cpu_affinity(affinity_mask)
        except Exception as e:
            return {"execution_status": "EXECUTION_FAILED", "reason": f"OS_AFFINITY_APPLICATION_ERROR: {str(e)}"}

        # 6. Vérification post-exécution (POST_EXECUTION_VERIFY -> EXECUTED_VERIFIED)
        try:
            actual_affinity = p.cpu_affinity()
            # Comparaison stricte des ensembles (sets) pour s'affranchir de l'ordre brut
            if set(actual_affinity) == set(affinity_mask):
                return {"execution_status": "EXECUTED_VERIFIED", "requested": affinity_mask, "applied": actual_affinity, "pid": self.pid}
            else:
                return {
                    "execution_status": "VERIFICATION_FAILED",
                    "reason": "MISMATCH_BETWEEN_REQUESTED_AND_ACTUAL_AFFINITY",
                    "requested": affinity_mask,
                    "applied": actual_affinity,
                }
        except Exception as e:
            return {"execution_status": "VERIFICATION_FAILED", "reason": f"READBACK_ERROR: {str(e)}"}
