"""
E-ZZIO V7.26.0 — Health Recovery Manager
Effectue des sondes de santé périodiques pour ramener progressivement
un provider défaillant de OPEN -> HALF_OPEN -> ONLINE.
"""

import asyncio
from providers.provider_registry import get_provider_instance
from core.routing.circuit_breaker import circuit_breaker


class HealthRecoveryManager:
    @staticmethod
    async def probe_provider_health(provider_name: str) -> bool:
        """Exécute un health check léger pour tester la ré-accessibilité d'un provider."""
        instance = get_provider_instance(provider_name)
        if not instance or not hasattr(instance, "health"):
            return False
        try:
            health_res = instance.health()
            return health_res.get("healthy", False)
        except Exception:
            return False

    @classmethod
    async def run_reconciliation_loop(cls, interval_sec: float = 30.0):
        """Boucle de fond d'auto-guérison (Kubernetes-like operator)."""
        while True:
            await asyncio.sleep(interval_sec)
            for prov in ["ollama", "gemini", "groq"]:
                if circuit_breaker.is_open(prov):
                    # Test de reconnexion
                    recovered = await cls.probe_provider_health(prov)
                    if recovered:
                        print(f"[Self-Healing] Succès de la sonde : le provider '{prov}' est rétabli. Fermeture du disjoncteur.")
                        circuit_breaker.record_success(prov)


health_manager = HealthRecoveryManager()
