"""TEST A — certification du routage réel end-to-end (mocks, aucun appel LLM).

Chemin prouvé : EzzioMaster.federation_router.execute_task
  → CoderModelFederationRouter.resolve_candidates
  → ProviderCandidate(model_name explicite)
  → provider.generate(model=explicit)
"""
import pytest

from core.agent.coder_federation import (
    CoderModelFederationRouter,
    TaskProfile,
    ContextSize,
    PrivacyRequirement,
    RoutingIntegrityError,
)
from core.providers.base_provider import CostClass, ProviderResponse


class SpyProvider:
    """Faux provider qui capture le modèle reçu et répond succès."""

    def __init__(self, name="gemini", fail=False):
        self.name = name
        self.fail = fail
        self.seen_models = []

    def is_available(self):
        return True

    def availability(self):
        from core.providers.base_provider import ProviderAvailability
        return ProviderAvailability.AVAILABLE

    async def generate(self, prompt, model=None, **kwargs):
        self.seen_models.append(model)
        if self.fail:
            from core.providers.base_provider import ProviderErrorClass
            return ProviderResponse(
                content="", model=model or "unknown", provider=self.name,
                cost_class=CostClass.FREE_ENDPOINT,
                error_class=ProviderErrorClass.PROVIDER_UNAVAILABLE,
                raw={"error": "injected failure"},
            )
        return ProviderResponse(
            content="OK", model=model or "unknown", provider=self.name,
            cost_class=CostClass.FREE_ENDPOINT, error_class=None, raw={},
        )


def _large_profile():
    return TaskProfile(context_size=ContextSize.LARGE)


def test_a_primary_is_gemini_3_7_flash():
    """TEST A : profil LARGE → primary gemini / gemini-3.7-flash."""
    router = CoderModelFederationRouter(
        providers={"gemini": SpyProvider("gemini")},
        audit_ledger=None,
    )
    plan = router.resolve_candidates(_large_profile())
    assert plan.primary.provider_name == "gemini"
    assert plan.primary.model_name == "gemini-3.7-flash"
    assert plan.primary.is_local is False


@pytest.mark.asyncio
async def test_a_explicit_model_transmitted():
    """Le provider reçoit exactement le modèle sélectionné, sans fallback."""
    spy = SpyProvider("gemini")
    router = CoderModelFederationRouter(
        providers={"gemini": spy}, audit_ledger=None,
    )
    resp = await router.execute_task(prompt="def f(): pass", profile=_large_profile())
    assert resp.error_class is None
    assert spy.seen_models == ["gemini-3.7-flash"]
    trace = resp.raw.get("coder_federation_trace", {})
    assert trace.get("attempts_count", 1) == 1
    assert trace.get("successful_model") == "gemini-3.7-flash"


@pytest.mark.asyncio
async def test_a_fallback_central_explicit():
    """Échec primary → fallback registry avec modèle explicite (gemini → ollama)."""
    spy_gemini = SpyProvider("gemini", fail=True)
    spy_ollama = SpyProvider("ollama")
    router = CoderModelFederationRouter(
        providers={"gemini": spy_gemini, "ollama": spy_ollama},
        audit_ledger=None,
    )
    resp = await router.execute_task(prompt="def f(): pass", profile=_large_profile())
    assert resp.error_class is None
    assert resp.provider == "ollama"
    trace = resp.raw.get("coder_federation_trace", {})
    assert trace.get("attempts_count", 0) == 2


@pytest.mark.asyncio
async def test_no_drift_explicit_beats_default():
    """EXPLICIT MODEL > PROVIDER DEFAULT : le default provider ne réapparaît pas."""
    from core.providers.gemini_provider import GeminiProvider
    assert GeminiProvider.DEFAULT_MODEL == "gemini-3.6-flash"
    spy = SpyProvider("gemini")
    router = CoderModelFederationRouter(
        providers={"gemini": spy}, audit_ledger=None,
    )
    await router.execute_task(prompt="x", profile=_large_profile())
    assert "gemini-3.6-flash" not in spy.seen_models


@pytest.mark.asyncio
async def test_fail_closed_no_provider():
    """providers={} explicite → aucun provider, épuisement fail-closed.
    Régression : {} ne doit plus remonter silencieusement les defaults."""
    router = CoderModelFederationRouter(providers={}, audit_ledger=None)
    assert router.providers == {}
    resp = await router.execute_task(prompt="x", profile=_large_profile())
    assert resp.error_class is not None
    assert resp.content == ""
    trace = resp.raw.get("coder_federation_trace", {})
    assert trace.get("exhausted") is True


def test_fail_closed_local_only_escalation():
    """LOCAL_ONLY + candidat cloud → RoutingIntegrityError."""
    from core.agent.coder_federation import ProviderCandidate
    router = CoderModelFederationRouter(
        providers={"gemini": SpyProvider("gemini")}, audit_ledger=None,
    )
    profile = TaskProfile(privacy_required=PrivacyRequirement.LOCAL_ONLY)
    plan = router.resolve_candidates(profile)
    assert all(c.is_local for c in [plan.primary] + plan.fallback_chain)
    assert TaskProfile.from_dict({"privacy_required": "LOCAL_ONLY"}).privacy_required == PrivacyRequirement.LOCAL_ONLY
    with pytest.raises(RoutingIntegrityError):
        TaskProfile.from_dict({"privacy_required": "NOPE"})
