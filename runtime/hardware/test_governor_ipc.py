import sys
import time
import json
from pathlib import Path

# S'assure de l'importabilité directe du module hardware
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from runtime.hardware.governor_service import HardwareGovernorService

def test_hardware_governor_ipc():
    print("=============================================================", flush=True)
    print(" E-ZZIO V4.8.1 — Autonomous Hardware Governor & IPC Test", flush=True)
    print("=============================================================", flush=True)

    hw_dir = Path(__file__).resolve().parent
    governor = HardwareGovernorService(state_dir=str(hw_dir))

    # 1. Vérification du fichier d'état IPC initial
    ipc_file = hw_dir / "state.json"
    assert ipc_file.exists(), "FAIL: Le fichier d'état IPC state.json n'a pas été créé !"
    print("[OK] Fichier d'état IPC initial détecté.", flush=True)

    # 2. Basculement de profils et vérification de la persistance IPC
    profiles_to_test = ["GAMING", "COMPUTE", "EVOLUTION"]

    for profile in profiles_to_test:
        print(f"\n[*] Basculement vers le profil {profile}...", flush=True)
        governor.set_profile(profile)
        time.sleep(0.1)

        state = governor.read_ipc_state()
        print(f"[IPC STATE READ] Profile: {state.get('active_profile')} | Affinity Threads: {state.get('cpu_topology', {}).get('assigned_affinity_count')} | Priority: {state.get('win32_priority')}", flush=True)

        assert state.get("active_profile") == profile, f"FAIL: Profil IPC attendu {profile}, trouvé {state.get('active_profile')}"
        
        if profile == "GAMING":
            assert state.get("cpu_topology", {}).get("assigned_affinity_count") == 12, "FAIL: GAMING doit utiliser exactement 12 threads (CCD1)"
        elif profile == "COMPUTE":
            assert state.get("cpu_topology", {}).get("assigned_affinity_count") == 22, "FAIL: COMPUTE doit utiliser 22 threads (2-23)"
        elif profile == "EVOLUTION":
            assert state.get("cpu_topology", {}).get("assigned_affinity_count") == 24, "FAIL: EVOLUTION doit utiliser 24 threads"

    print("\n=============================================================", flush=True)
    print(" STATUS : GOVERNOR AUTONOME & IPC V4.8.1 CERTIFIÉS", flush=True)
    print("=============================================================", flush=True)

if __name__ == "__main__":
    test_hardware_governor_ipc()
