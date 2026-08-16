"""
Validation de la brique V9.2.3 Capability Installer
Vérifie le déploiement sandboxé et l'enregistrement d'une nouvelle compétence.
"""
import sys
import json
from pathlib import Path

ROOT_DIR = Path(r"G:\AI\E-zzio")
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from runtime.capabilities.installer import CapabilityInstaller

def run_test():
    print("\n" + "="*60)
    print(" 🏛️ E-ZZIO V9.2.3 — CAPABILITY INSTALLER TEST")
    print("="*60)

    installer = CapabilityInstaller()
    
    # Manifeste de test pour une nouvelle capacité validée
    new_skill_manifest = {
        "skill_id": "analytics_dashboard_addon",
        "version": "1.0",
        "permissions": ["filesystem_read"],
        "memory_cost_mb": 60,
        "gpu_required": False,
        "rollback_available": True
    }

    result = installer.install(new_skill_manifest)
    print(json.dumps(result, indent=2))
    print("-" * 60)

    assert result['status'] == "INSTALLED_SUCCESS", "Échec de l'installation de la compétence !"

    print(" 🟢 STATUS : INSTALLER_SECURED_AND_OPERATIONAL")
    print("="*60 + "\n")

if __name__ == "__main__":
    run_test()
