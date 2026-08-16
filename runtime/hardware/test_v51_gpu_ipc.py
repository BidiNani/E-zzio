import sys
import time
import json
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from runtime.hardware.governor_service import HardwareGovernorService

def test_v51_gpu_ipc_integration():
    print("=============================================================", flush=True)
    print(" E-ZZIO V5.1 — Unified CPU/GPU Governor IPC Integration Test", flush=True)
    print("=============================================================", flush=True)

    hw_dir = Path(__file__).resolve().parent
    governor = HardwareGovernorService(state_dir=str(hw_dir))

    try:
        time.sleep(1.0)
        ipc_file = hw_dir / "state.json"
        assert ipc_file.exists(), "FAIL: Fichier state.json introuvable !"

        # --- TEST 1 : Vérification de la Structure V5.1.0 & GPU Telemetry ---
        print("\n--- TEST 1 : Validation de la Structure IPC V5.1.0 ---", flush=True)
        governor.set_profile("COMPUTE")
        time.sleep(0.5)

        state = governor.read_ipc_state()
        print(f"[IPC READ] Version : {state.get('version')}", flush=True)
        print(f"[IPC READ] Profil  : {state.get('active_profile')}", flush=True)
        print(f"[IPC READ] GPU     : {json.dumps(state.get('gpu_telemetry'), indent=2)}", flush=True)

        assert state.get("version") == "5.1.0", f"FAIL: Version attendue 5.1.0, obtenue {state.get('version')}"
        assert "gpu_telemetry" in state, "FAIL: gpu_telemetry absent du fichier IPC !"
        assert state.get("gpu_telemetry", {}).get("policy") == "ASSIST", "FAIL: Profil COMPUTE doit activer la politique GPU ASSIST !"
        print("[SUCCESS] Test 1 validé.", flush=True)

        # --- TEST 2 : Bascule de Profil & GPU Policy Mapping ---
        print("\n--- TEST 2 : Validation du Mapping GPU (GAMING vs EVOLUTION) ---", flush=True)
        
        # Mode GAMING -> GPU DISABLED
        state_gaming = governor.set_profile("GAMING")
        assert state_gaming.get("gpu_telemetry", {}).get("policy") == "DISABLED", "FAIL: GAMING doit désactiver le GPU (DISABLED) !"
        print("[OK] Profil GAMING -> GPU Policy: DISABLED validé.", flush=True)

        # Mode EVOLUTION -> GPU ACCELERATE
        governor.set_evolution_authorization(True)
        state_evo = governor.set_profile("EVOLUTION")
        assert state_evo.get("gpu_telemetry", {}).get("policy") == "ACCELERATE", "FAIL: EVOLUTION doit passer le GPU en ACCELERATE !"
        print("[OK] Profil EVOLUTION -> GPU Policy: ACCELERATE validé.", flush=True)

        print("[SUCCESS] Test 2 validé.", flush=True)

    finally:
        governor.stop()

    print("\n=============================================================", flush=True)
    print(" STATUS : E-ZZIO V5.1 UNIFIED CPU/GPU IPC CERTIFIÉ", flush=True)
    print("=============================================================", flush=True)

if __name__ == "__main__":
    test_v51_gpu_ipc_integration()
