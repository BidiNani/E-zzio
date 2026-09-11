"""
Tests unitaires pour le Routeur Fédéré E-ZzIO (Phases 6D, 6E, 6F).
"""
import pytest
from unittest.mock import AsyncMock, MagicMock
from core.providers.base_provider import (
    BaseProvider,
    CostClass,
    ProviderAvailability,
    ProviderErrorClass,
    ProviderResponse,
)
from core.routing.model_registry import (
    ModelSource,
    LatencyTier,
    ModelQualificationStatus,
    canonical_model_registry,
)
from core.routing.federated_router import (
    FederatedRouter,
    RoutingPolicy,
    RoutingDecision,
)


@pytest.fixture
def mock_providers():
    local = MagicMock(spec=BaseProvider)
    local.name = "ollama"
    local.is_available.return_value = True
    local.availability.return_value = ProviderAvailability.AVAILABLE
    local.generate = AsyncMock(return_value=ProviderResponse(
        content="Réponse Locale",
        model="qwen3:8b",
        provider="ollama",
        cost_class=CostClass.LOCAL,
        usage={"total_tokens": 25},
    ))

    gemini = MagicMock(spec=BaseProvider)
    gemini.name = "gemini"
    gemini.is_available.return_value = True
    gemini.availability.return_value = ProviderAvailability.AVAILABLE
    gemini.generate = AsyncMock(return_value=ProviderResponse(
        content="Réponse Gemini",
        model="gemini-3.5-flash",
        provider="gemini",
        cost_class=CostClass.FREE_ENDPOINT,
        usage={"total_tokens": 40},
    ))

    groq = MagicMock(spec=BaseProvider)
    groq.name = "groq"
    groq.is_available.return_value = True
    groq.availability.return_value = ProviderAvailability.AVAILABLE
    groq.generate = AsyncMock(return_value=ProviderResponse(
        content="Réponse Groq",
        model="llama-3.3-70b-versatile",
        provider="groq",
        cost_class=CostClass.FREE_ENDPOINT,
        usage={"total_tokens": 30},
    ))

    nvidia = MagicMock(spec=BaseProvider)
    nvidia.name = "nvidia"
    nvidia.is_available.return_value = True
    nvidia.availability.return_value = ProviderAvailability.AVAILABLE
    nvidia.generate = AsyncMock(return_value=ProviderResponse(
        content="Réponse NVIDIA",
        model="nvidia/nemotron-3.5-lightning-30b-a3b",
        provider="nvidia",
        cost_class=CostClass.FREE_ENDPOINT,
        usage={"total_tokens": 50},
    ))

    return {
        ModelSource.LOCAL: local,
        ModelSource.GEMINI: gemini,
        ModelSource.GROQ: groq,
        ModelSource.NVIDIA: nvidia,
    }


def test_select_route_policy_offline(mock_providers):
    router = FederatedRouter(providers=mock_providers)
    decision = router.select_route("Calcul simple", policy=RoutingPolicy.OFFLINE)
    assert decision.primary_model.source == ModelSource.LOCAL
    assert decision.policy == RoutingPolicy.OFFLINE
    for fb in decision.fallback_chain:
        assert fb.source == ModelSource.LOCAL


def test_select_route_policy_free_only(mock_providers):
    router = FederatedRouter(providers=mock_providers)
    decision = router.select_route("Explique les fonctions Python", policy=RoutingPolicy.FREE_ONLY)
    assert decision.primary_model.cost_class in (CostClass.LOCAL, CostClass.FREE_ENDPOINT)
    assert "0€ garanti" in decision.reason


def test_select_route_policy_lowest_latency(mock_providers):
    router = FederatedRouter(providers=mock_providers)
    decision = router.select_route("Ping rapide", policy=RoutingPolicy.LOWEST_LATENCY)
    assert decision.primary_model.latency_tier == LatencyTier.FAST
    assert decision.policy == RoutingPolicy.LOWEST_LATENCY


def test_select_route_policy_performance_first(mock_providers):
    router = FederatedRouter(providers=mock_providers)
    decision = router.select_route("Preuve formelle mathématique", policy=RoutingPolicy.PERFORMANCE_FIRST)
    assert any(c in decision.primary_model.capabilities for c in ["REASONING", "CODING"])


@pytest.mark.asyncio
async def test_complete_primary_success(mock_providers):
    router = FederatedRouter(providers=mock_providers)
    resp = await router.complete("Bonjour", policy=RoutingPolicy.FREE_ONLY)
    assert isinstance(resp, ProviderResponse)
    assert resp.content != ""
    assert "routing_decision_trace" in resp.raw
    trace = resp.raw["routing_decision_trace"]
    assert "successful_model_id" in trace
    assert trace["attempts_count"] == 1


@pytest.mark.asyncio
async def test_complete_fallback_on_error(mock_providers):
    # Forcer échec sur le premier provider (LOCAL) pour déclencher le fallback
    mock_providers[ModelSource.LOCAL].generate = AsyncMock(return_value=ProviderResponse(
        content="",
        error_class=ProviderErrorClass.RATE_LIMITED,
        model="qwen3:8b",
        provider="ollama",
    ))

    router = FederatedRouter(providers=mock_providers)
    resp = await router.complete("Bonjour", policy=RoutingPolicy.LOCAL_FIRST)

    assert isinstance(resp, ProviderResponse)
    trace = resp.raw.get("routing_decision_trace", {})
    assert trace.get("attempts_count", 0) >= 2
    assert len(trace.get("fallback_events", [])) >= 1
    assert trace["fallback_events"][0]["error_class"] == "RATE_LIMITED"


@pytest.mark.asyncio
async def test_complete_all_failed_fail_closed(mock_providers):
    # Forcer tous les providers en échec
    for p in mock_providers.values():
        p.generate = AsyncMock(return_value=ProviderResponse(
            content="",
            error_class=ProviderErrorClass.PROVIDER_UNAVAILABLE,
            model="mock",
            provider="mock",
        ))

    router = FederatedRouter(providers=mock_providers)
    resp = await router.complete("Requête critique", policy=RoutingPolicy.FREE_ONLY)

    assert resp.content == ""
    assert resp.error_class == ProviderErrorClass.PROVIDER_UNAVAILABLE
    trace = resp.raw.get("routing_decision_trace", {})
    assert trace.get("exhausted") is True


@pytest.mark.asyncio
async def test_stream_dispatch(mock_providers):
    async def mock_stream_tokens(*args, **kwargs):
        yield "Token1 "
        yield "Token2"

    mock_providers[ModelSource.LOCAL].stream = mock_stream_tokens

    router = FederatedRouter(providers=mock_providers)
    tokens = []
    async for token in router.stream("Test stream", policy=RoutingPolicy.OFFLINE):
        tokens.append(token)

    assert tokens == ["Token1 ", "Token2"]
