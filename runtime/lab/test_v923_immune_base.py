"""
Test de certification du socle immunitaire V9.2.3 (Registry & Manifest Validator)
"""
import sys
import json
from pathlib import Path

ROOT_DIR = Path(r"G:\AI\E-zzio")
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from runtime.capabilities.registry.registry_core import RegistryCore
from runtime.capabilities.security.manifest_validator import ManifestValidator

def run_test():
    print("\n" + "="*60)
    print(" 🏛️ E-ZZIO V9.2.3 — CAPABILITY IMMUNE SYSTEM BASELINE")
    print("="*60)

    registry = RegistryCore()
    validator = ManifestValidator()

    state = registry.get_state()
    print(f" Registre initialisé : {len(state['capabilities'])} compétences actives.")

    # Test A : Manifeste corrompu (doit aller en quarantaine)
    bad_manifest = {"capability_id": "MALICIOUS_TOOL"}
    res_bad = validator.validate_and_inspect(bad_manifest)
    print(f" Test Manifeste Invalide : [{res_bad['status']}] -> {res_bad['reason']}")

    # Test B : Manifeste violant HW-001 (doit aller en quarantaine)
    gpu_manifest = {
        "capability_id": "HEAVY_GPU_AI",
        "version": "1.0",
        "origin": {"source": "external"},
        "behavior": {},
        "resource_budget": {"gpu_allowed": True},
        "rollback": {"snapshot_required": True}
    }
    res_gpu = validator.validate_and_inspect(gpu_manifest)
    print(f" Test Violation HW-001   : [{res_gpu['status']}] -> {res_gpu['reason']}")

    # Test C : Manifeste parfaitement conforme
    good_manifest = {
        "capability_id": "WEB_RESEARCHER",
        "version": "1.0",
        "origin": {"source": "verified_registry"},
        "behavior": {"network": True},
        "resource_budget": {"ram_mb": 100, "gpu_allowed": False},
        "rollback": {"snapshot_required": True}
    }
    res_good = validator.validate_and_inspect(good_manifest)
    print(f" Test Manifeste Conforme : [{res_good['status']}] -> {res_good['reason']}")

    print("-" * 60)
    print(" 🟢 STATUS : IMMUNE BASELINE CERTIFIED")
    print("="*60 + "\n")

    assert res_bad['status'] == "REJECTED"
    assert res_gpu['status'] == "REJECTED"
    assert res_good['status'] == "VALIDATED"

if __name__ == "__main__":
    run_test()
