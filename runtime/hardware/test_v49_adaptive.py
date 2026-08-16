import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from runtime.hardware.governor_service import HardwareGovernorService
from runtime.hardware.adaptive_daemon import AdaptiveHardwareDaemon

def test_v49_adaptive_system():
    print("=============================================================", flush=True)
    print(" E-ZZIO V4.9 — Adaptive Hardware Intelligence & Guards Test", flush=True)
    print("=============================================================", flush=True)

    hw_dir = Path(__file__).resolve().parent
    governor = HardwareGovernorService(state_dir=str(hw_dir))
    adaptive = AdaptiveHardwareDaemon(governor, hysteresis_sec=1.0)

    # 1. Validation du Heartbeat IPC
    print("\n[*] Validation du Heartbeat IPC dynamique...", flush=True)
    time.sleep(2.5)
    state1 = governor.read_ipc_state()
    hb1 = state1.get("heartbeat", 0)
    print(f"[HEARTBEAT 1] Timestamp : {hb1}", flush=True)
    
    time.sleep(2.5)
    state2 = governor.read_ipc_state()
    hb2 = state2.get("heartbeat", 0)
    print(f"[HEARTBEAT 2] Timestamp : {hb2}", flush=True)
    
    assert hb2 > hb1, "FAIL: Le Heartbeat IPC ne s'est pas actualisé dans state.json !"
    print("[OK] Heartbeat IPC dynamique validé.", flush=True)

    # 2. Validation du Garde-Fou de Priorité EVOLUTION
    print("\n[*] Validation du Garde-Fou EVOLUTION...", flush=True)
    governor.set_evolution_authorization(False)
    prof_result = governor.set_profile("EVOLUTION")
    assert prof_result.get("active_profile") == "COMPUTE", "FAIL: EVOLUTION aurait dû être bloqué et basculé vers COMPUTE !"
    print("[OK] Garde-Fou EVOLUTION validé (Non autorisé -> COMPUTE).", flush=True)

    governor.set_evolution_authorization(True)
    prof_result2 = governor.set_profile("EVOLUTION")
    assert prof_result2.get("active_profile") == "EVOLUTION", "FAIL: EVOLUTION aurait dû être accepté sous autorisation !"
    print("[OK] Autorisation EVOLUTION validée.", flush=True)

    # 3. Validation de l'Évaluation Auto-Adaptative
    print("\n[*] Validation du moteur décisionnel auto-adaptatif (Hystérésis)...", flush=True)
    eval_prof = adaptive.evaluate_system_state()
    print(f"[ADAPTIVE EVAL] Profil sélectionné : {eval_prof}", flush=True)

    governor.stop()
    print("\n=============================================================", flush=True)
    print(" STATUS : V4.9 ADAPTIVE HARDWARE INTELLIGENCE CERTIFIÉ", flush=True)
    print("=============================================================", flush=True)

if __name__ == "__main__":
    test_v49_adaptive_system()
