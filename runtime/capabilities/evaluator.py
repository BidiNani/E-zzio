"""
E-ZZIO V9.2.2 — Capability Evaluator
Évalue un manifeste de compétence par rapport aux contraintes matérielles 
(Règle HW-001 : sanctuarisation de la GTX 1650) et aux budgets de l'organisme.
"""
import json
from typing import Dict, Any

class CapabilityEvaluator:
    def __init__(self):
        # Limites et politiques de l'organisme
        self.max_allowed_ram_mb = 1024  # 1 Go max par skill individuel
        self.gpu_sanctuary_rule = "HW-001"  # Interdiction d'allouer la GTX 1650 à des processus IA lourds non gérés

    def evaluate(self, capability_manifest: dict) -> Dict[str, Any]:
        skill_id = capability_manifest.get("skill_id", "unknown")
        memory_cost = capability_manifest.get("memory_cost_mb", 0)
        gpu_required = capability_manifest.get("gpu_required", False)
        permissions = capability_manifest.get("permissions", [])

        # 1. Vérification de la règle matérielle HW-001 (GPU Sanctuary)
        if gpu_required:
            return {
                "skill_id": skill_id,
                "status": "REJECTED",
                "reason": f"Violation de la politique matérielle [{self.gpu_sanctuary_rule}] : La compétence exige un GPU local, compromettant la sanctuarisation de la GTX 1650 pour le jeu/système."
            }

        # 2. Vérification du budget mémoire
        if memory_cost > self.max_allowed_ram_mb:
            return {
                "skill_id": skill_id,
                "status": "REJECTED",
                "reason": f"Dépassement de budget : Le coût mémoire ({memory_cost} MB) dépasse la limite autorisée ({self.max_allowed_ram_mb} MB)."
            }

        # 3. Vérification des permissions dangereuses
        forbidden_perms = ["kernel_override", "raw_disk_write"]
        for perm in permissions:
            if perm in forbidden_perms:
                return {
                    "skill_id": skill_id,
                    "status": "REJECTED",
                    "reason": f"Violation de sécurité ECOL : Permission interdite détectée ('{perm}')."
                }

        # Évaluation réussie
        return {
            "skill_id": skill_id,
            "status": "APPROVED",
            "reason": "Évaluation validée : Conforme à la politique HW-001, aux budgets mémoire et aux règles ECOL."
        }

if __name__ == "__main__":
    evaluator = CapabilityEvaluator()
    # Test avec un skill conforme et un skill non conforme
    print(evaluator.evaluate({"skill_id": "safe_cloud_api", "memory_cost_mb": 50, "gpu_required": False, "permissions": ["network"]}))
    print(evaluator.evaluate({"skill_id": "heavy_local_llm", "memory_cost_mb": 8000, "gpu_required": True, "permissions": ["network"]}))
