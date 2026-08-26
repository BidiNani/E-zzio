import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from runtime.hardware.memory_intelligence import MemoryIntelligenceEngine
from runtime.hardware.memory_actuator import ActiveMemoryActuator


class MockConcurrentEngine:
    """Mock léger simulant le comportement de ConcurrentSegmentedEngine."""

    def __init__(self):
        self.max_batch_size = 2000
        self.max_batch_delay = 0.01


def test_v52_active_memory_actuator():
    print("=============================================================", flush=True)
    print(" E-ZZIO V5.2 — Active Memory Actuator & Engine Coupling Test", flush=True)
    print("=============================================================", flush=True)

    engine = MockConcurrentEngine()
    mem_intelligence = MemoryIntelligenceEngine(budget_mb=10240.0)
    actuator = ActiveMemoryActuator(engine_ref=engine, memory_engine_ref=mem_intelligence)

    try:
        # --- PHASE 1 : État Nominal ---
        print("\n--- PHASE 1 : Vérification du Régime Nominal ---", flush=True)
        res1 = actuator.apply_regulation_tick()
        print(f"[NOMINAL] Tier : {res1['tier']} | Batch Size : {engine.max_batch_size} | Delay : {engine.max_batch_delay}s", flush=True)

        assert res1["tier"] == "NOMINAL", f"FAIL: Attendu NOMINAL, obtenu {res1['tier']}"
        assert engine.max_batch_size == 2000, f"FAIL: Batch size attendu 2000, obtenu {engine.max_batch_size}"
        assert engine.max_batch_delay == 0.01
        print("[SUCCESS] Régime nominal validé.", flush=True)

        # --- PHASE 2 : Injection de Pression RAM (Simulée & Commit Physique) ---
        print("\n--- PHASE 2 : Simulation d'Emballement RAM & Modération ---", flush=True)

        # Simulation d'un spike RAM
        dummy_allocation = bytearray(250 * 1024 * 1024)
        for i in range(0, len(dummy_allocation), 4096):
            dummy_allocation[i] = 1

        time.sleep(0.1)
        res2 = actuator.apply_regulation_tick()
        print(
            f"[CRITICAL SPIKE] Tier : {res2['tier']} | OOM Index : {res2['oom_index']} | Batch Size : {engine.max_batch_size} | Delay : {engine.max_batch_delay}s",
            flush=True,
        )

        assert res2["tier"] == "CRITICAL", f"FAIL: Attendu CRITICAL sous emballement, obtenu {res2['tier']}"
        assert engine.max_batch_size == 250, f"FAIL: Batch size aurait dû descendre à 250, obtenu {engine.max_batch_size}"
        assert engine.max_batch_delay == 0.05
        print("[SUCCESS] Étranglement actif sous pression OOM certifié.", flush=True)

        # --- PHASE 3 : Libération RAM et Retour au Calme ---
        print("\n--- PHASE 3 : Purge Mémoire & Restauration du Régime ---", flush=True)
        del dummy_allocation
        time.sleep(0.2)

        res3 = actuator.apply_regulation_tick()
        print(f"[RECOVERY] Tier : {res3['tier']} | Batch Size : {engine.max_batch_size} | Delay : {engine.max_batch_delay}s", flush=True)

        assert res3["tier"] == "NOMINAL", "FAIL: Le système aurait dû repasser en NOMINAL !"
        assert engine.max_batch_size == 2000
        print("[SUCCESS] Restauration du régime nominal certifiée.", flush=True)

    finally:
        actuator.stop()

    print("\n=============================================================", flush=True)
    print(" STATUS : V5.2 ACTIVE MEMORY ACTUATOR CERTIFIÉ ✅", flush=True)
    print("=============================================================", flush=True)


if __name__ == "__main__":
    test_v52_active_memory_actuator()
