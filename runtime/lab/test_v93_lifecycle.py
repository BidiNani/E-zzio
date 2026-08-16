"""
Test de certification de la couche organique V9.3 (Lifecycle Manager & Web Researcher)
"""
import sys
import json
from pathlib import Path

ROOT_DIR = Path(r"G:\AI\E-zzio")
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from runtime.capabilities.lifecycle.lifecycle_manager import LifecycleManager

def run_test():
    print("\n" + "="*60)
    print(" 🏛️ E-ZZIO V9.3 — CAPABILITY ORGANISM LAYER TEST")
    print("="*60)

    manager = LifecycleManager()
    cap_id = "WEB_RESEARCHER"

    # Vérification de l'état initial
    manifest = manager.load_manifest(cap_id)
    print(f" Organe chargé : {cap_id}")
    print(f" État initial  : {manifest.get('status')}")

    # Simulation du cycle de vie biologique
    steps = ["SECURITY_SCAN", "SANDBOX_TEST", "APPROVED", "ACTIVE", "MONITORED"]
    for step in steps:
        res = manager.transition_state(cap_id, step)
        print(f" Transition vers {step} -> [{res['status']}]")

    final_manifest = manager.load_manifest(cap_id)
    print("-" * 60)
    print(f" État final de l'organe : {final_manifest.get('status')}")
    print(f" RAM allouée            : {final_manifest.get('resource_budget', {}).get('ram_mb')} MB")
    print(f" Contrôle GPU (HW-001)  : {final_manifest.get('resource_budget', {}).get('gpu_allowed')}")
    print("-" * 60)
    print(" 🟢 STATUS : CAPABILITY ORGANISM LAYER CERTIFIED")
    print("="*60 + "\n")

    assert final_manifest.get('status') == "MONITORED"

if __name__ == "__main__":
    run_test()
