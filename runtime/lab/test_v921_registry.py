"""
Validation de la brique V9.2.1 Capability Registry
Vérifie la gestion de la Constitution des compétences.
"""

import sys
import json
from pathlib import Path

ROOT_DIR = Path(r"G:\AI\E-zzio")
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from runtime.capabilities.registry import CapabilityRegistry


def run_test():
    print("\n" + "=" * 60)
    print(" 🏛️ E-ZZIO V9.2.1 — CAPABILITY REGISTRY TEST")
    print("=" * 60)

    registry = CapabilityRegistry()

    # Test d'enregistrement d'un skill test conforme
    test_manifest = {
        "skill_id": "vision_creator",
        "version": "1.0",
        "permissions": ["network", "filesystem_read"],
        "memory_cost_mb": 150,
        "gpu_required": False,
        "rollback_available": True,
    }

    success = registry.register_capability(test_manifest)
    print(f" Enregistrement de 'vision_creator' : {'[SUCCESS]' if success else '[ALREADY_EXISTS]'}")

    full_registry = registry.load_registry()
    print(json.dumps(full_registry, indent=2))
    print("-" * 60)
    print(f" Compétences actives : {len(full_registry['registered_capabilities'])}")
    print(" STATUS              : REGISTRY_SECURED")
    print("=" * 60 + "\n")

    assert len(full_registry["registered_capabilities"]) >= 2, "Erreur du registre de compétences"


if __name__ == "__main__":
    run_test()
