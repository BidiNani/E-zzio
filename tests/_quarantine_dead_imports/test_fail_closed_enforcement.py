"""E-ZZIO — Fail-Closed Enforcement (F1/F2).

a) Modèle inconnu rejeté par la fédération (strict, sans drapeau).
b) Fédération épuisée/vide → GovernanceError, aucun appel de secours,
   réponse FAIL_CLOSED (ok=False, model=none).
"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from core.agent.coder_federation import (
    CoderModelFederationRouter,
    ProviderCandidate,
    RoutingIntegrityError,
    TaskProfile,
)
from core.ezzio_master import EzzioMaster, GovernanceError
from core.providers.base_provider import CostClass, ProviderResponse


def _local_candidate() -> ProviderCandidate:
    return ProviderCandidate(
        provider_name="ollama",
        model_name="qwen2.5-coder:7b-instruct-q4_K_M",
        cost_class=CostClass.LOCAL,
        capabilities=["CODING", "LOCAL"],
        is_local=True,
    )


def test_unknown_model_rejected_by_federation():
    router = CoderModelFederationRouter(providers={}, audit_ledger=None)
    plan = router.resolve_candidates(TaskProfile())
    plan.primary = ProviderCandidate(
        provider_name="rogue",
        model_name="rogue-unknown-model-zzz",
        cost_class=CostClass.UNKNOWN,
        capabilities=[],
        is_local=False,
    )
    plan.fallback_chain = []
    with pytest.raises(RoutingIntegrityError):
        router._enforce_model_governance(plan)


@pytest.mark.asyncio
async def test_federation_exhaustion_raises_without_fallback():
    empty = ProviderResponse(
        content="",
        model="qwen2.5-coder:7b-instruct-q4_K_M",
        provider="ollama",
        cost_class=CostClass.LOCAL,
    )
    fed = MagicMock()
    fed.execute_task = AsyncMock(return_value=empty)
    master = EzzioMaster(federation_router=fed)

    with patch(
        "core.cloud_brain_broker.cloud_chat",
        side_effect=AssertionError("secours interdit"),
    ):
        res = await master.execute_intent(user_prompt="Bonjour, comment vas-tu ?")

    assert res["ok"] is False
    assert res["model"] == "none"
    assert res["provider"] == "none"
    assert "FAIL-CLOSED" in res["response"]
    fed.execute_task.assert_awaited_once()


def test_no_cloud_fallback_reference_in_master():
    import core.ezzio_master as mod

    assert not hasattr(mod, "cloud_chat")
    assert hasattr(mod, "GovernanceError")
