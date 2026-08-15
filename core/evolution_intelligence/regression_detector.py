"""
E-ZZIO V7.39 — Regression Intelligence
Compare empiriquement une version candidate avec l'historique pour bloquer toute dégradation.
"""
class RegressionDetector:
    @staticmethod
    def evaluate_regression(baseline_metrics: dict, candidate_metrics: dict, time_tolerance: float = 0.05, mem_tolerance: float = 0.05) -> dict:
        base_time = baseline_metrics.get("execution_time", 0.0)
        base_mem = baseline_metrics.get("memory_mb", 0.0)
        
        cand_time = candidate_metrics.get("execution_time", 0.0)
        cand_mem = candidate_metrics.get("memory_mb", 0.0)

        # Calcul des deltas (positif = dégradation, négatif = amélioration)
        time_delta_pct = ((cand_time - base_time) / base_time) if base_time > 0 else 0
        mem_delta_pct = ((cand_mem - base_mem) / base_mem) if base_mem > 0 else 0

        regression_time = time_delta_pct > time_tolerance
        regression_mem = mem_delta_pct > mem_tolerance

        is_regression = regression_time or regression_mem

        return {
            "performance_delta": f"{time_delta_pct * 100:+.2f}%",
            "memory_delta": f"{mem_delta_pct * 100:+.2f}%",
            "regression_detected": is_regression,
            "promotion_allowed": not is_regression,
            "details": {
                "time_regression": regression_time,
                "memory_regression": regression_mem
            }
        }

regression_detector = RegressionDetector()
