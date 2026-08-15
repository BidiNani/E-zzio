"""
E-ZZIO V7.37 — Optimization Scorer
Calcule un score d'optimisation [0.0 - 1.0] basé sur le profilage CPU/RAM par rapport à une cible.
"""
class OptimizationScorer:
    @staticmethod
    def calculate_score(module_name: str, metrics: dict, target_time: float = 1.0, target_ram_mb: float = 50.0) -> dict:
        exec_time = metrics.get("execution_time", 999.0)
        mem_mb = metrics.get("memory_mb", 999.0)

        # Calcul d'efficience (plus c'est bas, mieux c'est. 1.0 = correspond à la cible)
        time_efficiency = max(0.0, 1.0 - (exec_time / target_time))
        mem_efficiency = max(0.0, 1.0 - (mem_mb / target_ram_mb))

        # Score pondéré : 60% temps d'exécution, 40% RAM
        optimization_score = round((time_efficiency * 0.6) + (mem_efficiency * 0.4), 3)

        return {
            "module": module_name,
            "execution_time": exec_time,
            "memory_mb": mem_mb,
            "optimization_score": optimization_score,
            "status": "OPTIMIZED" if optimization_score > 0.5 else "NEEDS_OPTIMIZATION"
        }

optimization_scorer = OptimizationScorer()
