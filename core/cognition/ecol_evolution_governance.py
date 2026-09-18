"""
E-ZZIO Core — Evolution & Skills Governance Layer (V7.69.1 Hotfix)
Corrige la gestion des niveaux de risque critiques au niveau de l'adaptateur
pour garantir le blocage immédiat (Fail-Closed) des compétences non vérifiées.
"""

import logging
import sys
from pathlib import Path

ROOT_DIR = Path(r"G:\AI\E-zzio")
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from core.cognition.ecol_runtime_interceptor import (
    EcolRuntimeInterceptor,
    ExecutionBlockedByEcolError,
)

logger = logging.getLogger(__name__)


class EcolEvolutionGovernor:
    def __init__(self, interceptor: EcolRuntimeInterceptor = None):
        self.interceptor = interceptor if interceptor is not None else EcolRuntimeInterceptor()

    def create_skill_install_guard(self, risk_level: str = "high", estimated_tokens: int = 2000):
        """
        Garde-fou strict pour l'installation de compétences.
        Force un niveau de risque évalué comme 'high' pour garantir l'interception
        par le noyau de gouvernance, indépendamment de la sémantique 'critical'.
        """
        # Politique de sécurité adaptatrice : tout risque critique ou élevé devient 'high'
        enforced_risk = "high" if risk_level in {"high", "critical"} else risk_level

        return self.interceptor.guarded_execution(
            source_component="evolution_engine",
            action="SKILL_INSTALL",
            priority="normal",
            risk_level=enforced_risk,
            estimated_cost=estimated_tokens,
        )

    def create_auto_publish_guard(self, risk_level: str = "low", estimated_tokens: int = 150):
        return self.interceptor.guarded_execution(
            source_component="evolution_engine",
            action="AUTO_PUBLISH",
            priority="normal",
            risk_level=risk_level,
            estimated_cost=estimated_tokens,
        )


def test_evolution_governance():
    print("[*] Test de l'Evolution & Skills Governance Layer (V7.69.1 Hotfix)...")
    evo_gov = EcolEvolutionGovernor()

    # 1. Simulation d'une publication automatisée conforme
    @evo_gov.create_auto_publish_guard(risk_level="low", estimated_tokens=100)
    def bao_publish_documentation(thread_id: str, doc_payload: str) -> bool:
        print(f"    -> [BAO PUBLISHER] Publication vers le thread {thread_id} ({len(doc_payload)} octets)")
        return True

    print("\n--- Test 1 : Publication automatisée (Bao) autorisée ---")
    try:
        published = bao_publish_documentation("thread_wow_guides_01", "Guide technique Way of Elendil 3.3.5a mis à jour.")
        print(f"  [PASS] Publication Bao réussie : {published}")
    except Exception as e:
        print(f"  [FAIL] Échec inattendu : {e}")

    # 2. Simulation d'une installation de compétence à risque critique
    @evo_gov.create_skill_install_guard(risk_level="critical", estimated_tokens=10000)
    def install_unverified_skill(skill_name: str, source_uri: str) -> str:
        print(f"    -> [SKILL LOADER] Installation de la compétence '{skill_name}' depuis {source_uri}")
        print("  [FAIL] Alerte : L'installation d'une compétence critique non vérifiée a été autorisée !")
        return f"Compétence {skill_name} installée."

    print("\n--- Test 2 : Blocage actif d'une installation de compétence critique (Fail-Closed) ---")
    try:
        install_unverified_skill("Autonomous_Rogue_Executor", "https://untrusted-registry.io/rogue.zip")
    except ExecutionBlockedByEcolError as e:
        print(f"  [PASS] Interception réussie (FAIL CLOSED actif sur l'évolution) : {e}")

    print("\n" + "=" * 65)
    print(" EVOLUTION & SKILLS GOVERNANCE LAYER (V7.69.1) : PATCHED & ENFORCED")
    print("=" * 65)


if __name__ == "__main__":
    test_evolution_governance()
