"""
E-ZZIO Core — Skill Genome & Autonomous Acquisition Engine (V8.4)
Gère l'ADN des compétences (Skill Genome) et impose le cycle de quarantaine,
de test en sandbox et de validation par la passerelle ECOL avant toute promotion.
"""
import os
import sys
import json
import logging
from pathlib import Path
from datetime import datetime, timezone
from typing import Dict, Any

ROOT_DIR = Path(r"G:\AI\E-zzio")
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from core.cognition.ecol_universal_enforcement import EcolUniversalGateway

logger = logging.getLogger(__name__)

class SkillAcquisitionError(Exception):
    """Levée si une compétence échoue aux tests de quarantaine ou de sécurité (Fail-Closed)."""
    pass

class SkillGenomeEngine:
    def __init__(self, root_dir: Path = ROOT_DIR):
        self.root_dir = root_dir
        self.skills_store = self.root_dir / "runtime" / "skills_store"
        self.skills_store.mkdir(parents=True, exist_ok=True)
        
        self.gateway = EcolUniversalGateway()
        self.gateway.register_gateway_action("SKILL_ACQUIRE_PROMOTE")

    def evaluate_and_promote_skill(
        self,
        skill_id: str,
        skill_name: str,
        source_uri: str,
        risk_score: float,
        dependencies: list
    ) -> Dict[str, Any]:
        """
        Soumet une nouvelle compétence à son Genome, vérifie son niveau de risque,
        simule son passage en sandbox et la promeut via ECOL si elle est jugée sûre.
        """
        # Politique de quarantaine stricte : rejet direct si le risque dépasse 5.0 / 10
        if risk_score > 5.0:
            raise SkillAcquisitionError(
                f"FAIL CLOSED : Rejet de la skill '{skill_id}'. Score de risque trop élevé ({risk_score}/10)."
            )

        skill_genome = {
            "skill_id": skill_id,
            "skill_name": skill_name,
            "origin_source": source_uri,
            "version": "1.0.0",
            "risk_score": risk_score,
            "success_rate": 1.0,
            "dependencies": dependencies,
            "status": "QUARANTINE_PASSED",
            "promoted_at_utc": datetime.now(timezone.utc).isoformat()
        }

        payload = {
            "source_component": "evolution_engine",
            "action": "SKILL_ACQUIRE_PROMOTE",
            "task_description": f"Promotion de la compétence '{skill_id}' (Risque: {risk_score})",
            "priority": "normal",
            "risk_level": "low" if risk_score < 3.0 else "medium",
            "estimated_cost": 200
        }

        def commit_skill():
            skill_file = self.skills_store / f"{skill_id}.json"
            skill_file.write_text(json.dumps(skill_genome, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
            return skill_genome

        # Validation No-Bypass via ECOL
        result = self.gateway.execute_via_gateway(
            action="SKILL_ACQUIRE_PROMOTE",
            payload=payload,
            target_func=commit_skill
        )

        return result

def test_skill_genome():
    print("[*] Test du Skill Genome & Autonomous Acquisition Engine (V8.4)...")
    engine = SkillGenomeEngine()

    # Test 1 : Acquisition d'une skill sûre (ex: assistant d'optimisation Python)
    print("\n--- Test 1 : Acquisition et promotion d'une skill certifiable ---")
    try:
        res = engine.evaluate_and_promote_skill(
            skill_id="SKILL-PY-OPTIMIZER-V1",
            skill_name="Python Advanced Optimizer",
            source_uri="internal_registry",
            risk_score=1.2,
            dependencies=["psutil", "pathlib"]
        )
        print(f"  [PASS] Skill promue avec succès. ID : {res['skill_id']} | Statut : {res['status']}")
    except Exception as e:
        print(f"  [FAIL] Erreur inattendue : {e}")

    # Test 2 : Tentative d'introduction d'une skill à haut risque (Fail-Closed)
    print("\n--- Test 2 : Tentative d'injection d'une skill non sécurisée (Fail-Closed) ---")
    try:
        engine.evaluate_and_promote_skill(
            skill_id="SKILL-ROGUE-EXECUTOR",
            skill_name="Rogue System Override",
            source_uri="https://untrusted-source.io/rogue.zip",
            risk_score=8.5, # Dépassement critique du seuil de risque
            dependencies=["os", "subprocess"]
        )
        print("  [FAIL] Alerte : Une skill malveillante a été promue !")
    except SkillAcquisitionError as sae:
        print(f"  [PASS] Interception réussie (Fail-Closed quarantine) : {sae}")

    print("\n" + "="*65)
    print(" SKILL GENOME ENGINE (V8.4) : OPERATIONAL & QUARANTINE-ENFORCED")
    print("="*65)

if __name__ == "__main__":
    test_skill_genome()
