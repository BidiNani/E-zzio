"""
E-ZZIO Router wrapper - extrait de core/models/router.py (DORMANT).

Original : core/models/router.py (810 lignes, 97% de types LiteLLM recopies).
Actif : EzzioRouter (13 lignes) + 3 attributs d'instance.
"""
from litellm import Router as LiteLLM_BaseRouter


class EzzioRouter(LiteLLM_BaseRouter):
    """
    E-ZZIO Router wrapper extending LiteLLM Router.
    """

    def __init__(self, registry=None, key_pool=None, telemetry=None, **kwargs):
        super().__init__(**kwargs)
        self.registry = registry
        self.key_pool = key_pool
        self.telemetry = telemetry

    def invalidate_cache(self, *args, **kwargs) -> None:
        if hasattr(super(), "invalidate_cache"):
            super().invalidate_cache(*args, **kwargs)

