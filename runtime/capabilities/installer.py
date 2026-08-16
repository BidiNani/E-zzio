"""
E-ZZIO V9.2.3 — Capability Installer
Installe de manière isolée un skill approuvé par l'Evaluator, 
initialise sa sandbox et l'enregistre dans le Capability Registry.
"""
import json
from pathlib import Path
from typing import Dict, Any
from runtime.capabilities.evaluator import CapabilityEvaluator
from runtime.capabilities.registry import CapabilityRegistry

ROOT_DIR = Path(r"G:\AI\E-zzio")
ACTIVE_SKILLS_DIR = ROOT_DIR / "runtime" / "skills" / "active"

class CapabilityInstaller:
    def __init__(self):
        self.evaluator = CapabilityEvaluator()
        self.registry = CapabilityRegistry()

    def install(self, manifest: dict) -> Dict[str, Any]:
        skill_id = manifest.get("skill_id")
        
        # 1. Évaluation sécuritaire préalable obligatoire
        eval_result = self.evaluator.evaluate(manifest)
        if eval_result.get("status") != "APPROVED":
            return {
                "skill_id": skill_id,
                "status": "INSTALL_ABORTED",
                "reason": f"Échec de l'évaluation préalable : {eval_result.get('reason')}"
            }

        # 2. Vérification d'unicité
        if self.registry.is_capability_active(skill_id):
            return {
                "skill_id": skill_id,
                "status": "ALREADY_INSTALLED",
                "reason": "La compétence est déjà active dans l'organisme."
            }

        # 3. Création de l'espace d'exécution isolé (Sandbox / Skill directory)
        ACTIVE_SKILLS_DIR.mkdir(parents=True, exist_ok=True)
        skill_dir = ACTIVE_SKILLS_DIR / skill_id
        skill_dir.mkdir(parents=True, exist_ok=True)

        # Écriture du manifeste de compétence local
        manifest_path = skill_dir / "manifest.json"
        manifest_path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")

        # 4. Enregistrement officiel dans le registre
        registered = self.registry.register_capability(manifest)
        if not registered:
            return {
                "skill_id": skill_id,
                "status": "REGISTRY_FAILED",
                "reason": "Erreur lors de l'enregistrement dans le Capability Registry."
            }

        return {
            "skill_id": skill_id,
            "status": "INSTALLED_SUCCESS",
            "path": str(skill_dir.relative_to(ROOT_DIR)),
            "reason": "Installation réussie, sandbox initialisée et registre mis à jour."
        }

if __name__ == "__main__":
    installer = CapabilityInstaller()
    test_manifest = {
        "skill_id": "test_cloud_helper",
        "version": "1.0",
        "permissions": ["network"],
        "memory_cost_mb": 30,
        "gpu_required": False,
        "rollback_available": True
    }
    print(json.dumps(installer.install(test_manifest), indent=2))
