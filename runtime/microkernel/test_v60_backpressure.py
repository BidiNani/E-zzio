import sys
import time
from pathlib import Path

script_path = Path(__file__).resolve()
runtime_dir = script_path.parent.parent
sys.path.insert(0, str(runtime_dir.parent))

from runtime.hardware.cognitive_memory_governor import GuardianCognitiveGovernorV56
from runtime.microkernel.backpressure_controller import SemanticBackpressureController

class MockEngine:
    def __init__(self):
        self.max_batch_size = 2000
        self.max_batch_delay = 0.01

class MockMemoryEngine:
    def __init__(self):
        self.budget_mb = 10240.0
        self.state = {
            "oom_index": 0.2,
            "d_rss_dt_mbs": 0.0,
            "rss_mb": 2048.0,
            "critical_oom_risk": False
        }
    def evaluate_state(self):
        return self.state

def test_v60_semantic_backpressure_certification():
    print("=============================================================", flush=True)
    print(" E-ZZIO V6.0 — Semantic Backpressure Integration Test", flush=True)
    print("=============================================================", flush=True)

    hw_dir = runtime_dir / "hardware"
    engine = MockEngine()
    mem_engine = MockMemoryEngine()
    governor = GuardianCognitiveGovernorV56(engine, mem_engine, state_dir=str(hw_dir))
    controller = SemanticBackpressureController(governor_ref=governor)

    try:
        # --- TEST 1 : Régime Nominal ---
        print("\n--- TEST 1 : Régime Nominal Applicatif ---", flush=True)
        state1 = controller.update_backpressure_state()
        print(f"[NOMINAL] N_ctx LLM: {controller.get_llm_context_budget()} | Agents Arrière-plan Autorisés: {controller.is_agent_execution_allowed(True)}", flush=True)
        
        assert controller.get_llm_context_budget() == 16384, "FAIL: Fenêtre de contexte nominale attendue à 16384 !"
        assert controller.is_agent_execution_allowed(True) == True, "FAIL: Les agents d'arrière-plan doivent être autorisés !"
        assert controller.acquire_ingestion_slot() == 0.0, "FAIL: Ingestion sans délai attendue !"
        print("[SUCCESS] Régime nominal applicatif certifié.", flush=True)

        # --- TEST 2 : Provocation de Pression & Bridage Sémantique ---
        print("\n--- TEST 2 : Injection de Pression Mémoire & Backpressure ---", flush=True)
        mem_engine.state["oom_index"] = 0.82  # Dépasse le seuil 0.80
        
        state2 = controller.update_backpressure_state()
        print(f"[THROTTLED] Tier: {state2['regulation_tier']} | N_ctx LLM: {controller.get_llm_context_budget()} | Ingestion Delay: {controller.acquire_ingestion_slot()}s", flush=True)
        
        assert state2['regulation_tier'] == "CRITICAL"
        assert controller.get_llm_context_budget() == 2048, "FAIL: La fenêtre de contexte LLM aurait dû être réduite à 2048 !"
        assert controller.is_agent_execution_allowed(True) == False, "FAIL: Les agents d'arrière-plan auraient dû être suspendus !"
        assert controller.acquire_ingestion_slot() == 0.05, "FAIL: Le délai d'ingestion devait passer à 0.05s !"
        print("[SUCCESS] Backpressure sémantique certifiée.", flush=True)

    finally:
        controller.stop()
        governor.stop()

    print("\n=============================================================", flush=True)
    print(" STATUS : E-ZZIO V6.0 SEMANTIC BACKPRESSURE CERTIFIÉ ✅", flush=True)
    print("=============================================================", flush=True)

if __name__ == "__main__":
    test_v60_semantic_backpressure_certification()
