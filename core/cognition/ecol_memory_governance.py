"""
E-ZZIO Core — Memory Governance Layer (V7.68)
Gouverne les écritures en mémoire, les injections de contexte et la persistance
des états de l'agent en s'appuyant sur l'intercepteur runtime ECOL V7.67.
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


class EcolMemoryGovernor:
    def __init__(self, interceptor: EcolRuntimeInterceptor = None):
        self.interceptor = interceptor if interceptor is not None else EcolRuntimeInterceptor()

    def create_memory_write_guard(self, risk_level: str = "low", estimated_tokens: int = 50):
        """Fournit un décorateur spécialisé pour gouverner l'écriture ou la mise à jour de mémoire."""
        return self.interceptor.guarded_execution(
            source_component="memory_subsystem",
            action="MEMORY_WRITE",
            priority="normal",
            risk_level=risk_level,
            estimated_cost=estimated_tokens,
        )

    def create_context_injection_guard(self, risk_level: str = "medium", estimated_tokens: int = 150):
        """Fournit un décorateur spécialisé pour gouverner l'injection de contexte externe."""
        return self.interceptor.guarded_execution(
            source_component="memory_subsystem",
            action="CONTEXT_INJECT",
            priority="normal",
            risk_level=risk_level,
            estimated_cost=estimated_tokens,
        )


def test_memory_governance():
    print("[*] Test de la Memory Governance Layer (V7.68)...")
    mem_gov = EcolMemoryGovernor()

    # 1. Simulation d'une écriture mémoire standard (ex: sauvegarde d'un résumé de session)
    @mem_gov.create_memory_write_guard(risk_level="low", estimated_tokens=80)
    def persist_session_memory(memory_key: str, memory_data: str) -> bool:
        print(f"    -> [STOCKAGE MÉMOIRE] Écriture de la clé '{memory_key}' ({len(memory_data)} caractères)")
        return True

    print("\n--- Test 1 : Écriture mémoire nominale autorisée ---")
    try:
        success = persist_session_memory("session_summary_01", "L'utilisateur a validé l'architecture ECOL V7.65.")
        print(f"  [PASS] Mémoire persistée avec succès : {success}")
    except Exception as e:
        print(f"  [FAIL] Échec inattendu : {e}")

    # 2. Simulation d'une injection de contexte critique ou à haut risque (ex: prompt injection externe)
    @mem_gov.create_context_injection_guard(risk_level="critical", estimated_tokens=5000)
    def inject_external_context(source_url: str, raw_content: str) -> str:
        print(f"    -> [CONTEXT INJECTION] Injection de contenu depuis {source_url}")
        return raw_content

    print("\n--- Test 2 : Blocage actif d'une injection de contexte à haut risque (Fail-Closed) ---")
    try:
        inject_external_context("https://untrusted-source.com/payload", "Instructions cachées malveillantes...")
        print("  [FAIL] Alerte : L'injection de contexte non sécurisée a été autorisée !")
    except ExecutionBlockedByEcolError as e:
        print(f"  [PASS] Interception réussie (FAIL CLOSED actif sur la mémoire) : {e}")

    print("\n" + "=" * 65)
    print(" MEMORY GOVERNANCE LAYER (V7.68) : DEPLOYED & ENFORCED")
    print("=" * 65)


if __name__ == "__main__":
    test_memory_governance()
