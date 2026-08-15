"""
E-ZZIO V7.37 — Runtime Profiler
Mesure le temps d'exécution et la consommation mémoire (RAM) d'un module ou d'une fonction.
"""
import time
import tracemalloc
from typing import Callable

class RuntimeProfiler:
    @staticmethod
    def profile_execution(func: Callable, *args, **kwargs) -> dict:
        tracemalloc.start()
        start_time = time.perf_counter()

        try:
            result = func(*args, **kwargs)
            error = None
        except Exception as e:
            result = None
            error = str(e)

        exec_time = time.perf_counter() - start_time
        current_mem, peak_mem = tracemalloc.get_traced_memory()
        tracemalloc.stop()

        peak_mb = peak_mem / (1024 * 1024)

        return {
            "result": result,
            "error": error,
            "metrics": {
                "execution_time": round(exec_time, 6),
                "memory_mb": round(peak_mb, 4)
            }
        }

runtime_profiler = RuntimeProfiler()
