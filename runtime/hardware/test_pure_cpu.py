import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from runtime.hardware.governor_service import HardwareGovernorService


def test_pure_cpu_governor():
    print("=============================================================", flush=True)
    print(" E-ZZIO V5.0 — Pure CPU/RAM Governor Restoration Test", flush=True)
    print("=============================================================", flush=True)

    hw_dir = Path(__file__).resolve().parent
    governor = HardwareGovernorService(state_dir=str(hw_dir))

    try:
        time.sleep(0.5)
        ipc_file = hw_dir / "state.json"
        assert ipc_file.exists(), "FAIL: state.json absent !"

        state = governor.set_profile("COMPUTE")
        print(
            f"[IPC STATE READ] Profile: {state.get('active_profile')} | Version: {state.get('version')} | Threads: {state.get('cpu_topology', {}).get('assigned_affinity_count')}",
            flush=True,
        )

        assert state.get("version") == "5.0.0-CPU"
        assert state.get("cpu_topology", {}).get("assigned_affinity_count") == 22

    finally:
        governor.stop()

    print("=============================================================", flush=True)
    print(" STATUS : ARCHITECTURE 100% CPU/RAM RESTAURÉE & REINSTALÉE", flush=True)
    print("=============================================================", flush=True)


if __name__ == "__main__":
    test_pure_cpu_governor()
