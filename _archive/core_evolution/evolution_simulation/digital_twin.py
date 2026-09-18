"""
E-ZZIO V7.35 — Digital Twin Evaluator
Simule l'impact d'une évolution en comparant ses performances par rapport à une baseline de référence.
"""

from core.evolution_simulation.sandbox_runner import sandbox_runner


class DigitalTwinEvaluator:
    def simulate_evolution(self, candidate_code: str, baseline_max_time: float = 0.05) -> dict:
        # Exécution empirique dans le jumeau numérique (sandbox)
        sandbox_res = sandbox_runner.execute_in_sandbox(candidate_code)

        if not sandbox_res["success"]:
            return {"simulation_passed": False, "reason": f"RUNTIME_CRASH_IN_SANDBOX: {sandbox_res['error']}", "performance_delta": None}

        exec_time = sandbox_res["execution_time_seconds"]

        # Évaluation du delta par rapport à la baseline
        performance_delta = round(exec_time - baseline_max_time, 6)
        regression_detected = exec_time > baseline_max_time

        if regression_detected:
            return {
                "simulation_passed": False,
                "reason": "PERFORMANCE_REGRESSION_DETECTED",
                "execution_time": exec_time,
                "performance_delta": performance_delta,
            }

        return {
            "simulation_passed": True,
            "reason": "SIMULATION_PASSED_WITHOUT_REGRESSION",
            "execution_time": exec_time,
            "performance_delta": performance_delta,
        }


digital_twin = DigitalTwinEvaluator()
