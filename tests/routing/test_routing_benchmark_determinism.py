"""
E-ZZIO Core — Routing Benchmark & Determinism Suite (Phase 8).
Matrice exhaustive de 20 cas de test couvrant simplicité, complexité,
contraintes de latence, contraintes de coût, résilience aux pannes et déterminisme strict.
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
def mock_federation_stack():
    local = MagicMock(spec=BaseProvider)
    local.name = "ollama"
    local.is_available.return_value = True
    local.availability.return_value = ProviderAvailability.AVAILABLE
    local.generate = AsyncMock(return_value=ProviderResponse(
        content="Réponse Local",
        model="qwen3:8b",
        provider="ollama",
        cost_class=CostClass.LOCAL,
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
    ))

    providers = {
        ModelSource.LOCAL: local,
        ModelSource.GEMINI: gemini,
        ModelSource.GROQ: groq,
        ModelSource.NVIDIA: nvidia,
    }
    return FederatedRouter(registry=canonical_model_registry, providers=providers)


# =============================================================================
# GROUPE 1 : REQUÊTES SIMPLES & FACTUELLES (Cas 1 à 5)
# =============================================================================

def test_case_01_simple_greeting(mock_federation_stack):
    dec = mock_federation_stack.select_route("Bonjour, comment vas-tu ?")
    assert dec.primary_model.cost_class in (CostClass.LOCAL, CostClass.FREE_ENDPOINT)


def test_case_02_factual_lookup(mock_federation_stack):
    dec = mock_federation_stack.select_route("Quelle est la capitale de la France ?")
    assert dec.primary_model.cost_class in (CostClass.LOCAL, CostClass.FREE_ENDPOINT)


def test_case_03_short_definition(mock_federation_stack):
    dec = mock_federation_stack.select_route("Définis le mot récursivité en une phrase")
    assert dec.primary_model.qualification_status == ModelQualificationStatus.QUALIFIED


def test_case_04_ping_test(mock_federation_stack):
    dec = mock_federation_stack.select_route("Ping", task_type="fast")
    assert dec.primary_model.latency_tier in (LatencyTier.FAST, LatencyTier.MEDIUM)


def test_case_05_simple_arithmetic(mock_federation_stack):
    dec = mock_federation_stack.select_route("Combien font 2 + 2 ?")
    assert dec.primary_model is not None


# =============================================================================
# GROUPE 2 : REQUÊTES COMPLEXES & SPÉCIALISÉES (Cas 6 à 10)
# =============================================================================

def test_case_06_coding_function(mock_federation_stack):
    dec = mock_federation_stack.select_route("def compute_sha256(data: bytes) -> str:\n    pass", policy=RoutingPolicy.PERFORMANCE_FIRST)
    assert any(c in dec.primary_model.capabilities for c in ["CODING", "CODE"])


def test_case_07_architectural_analysis(mock_federation_stack):
    dec = mock_federation_stack.select_route("Analyse et explique le diagramme d'architecture distribuée", policy=RoutingPolicy.PERFORMANCE_FIRST)
    assert any(c in dec.primary_model.capabilities for c in ["REASONING", "ARCHITECTURE"])


def test_case_08_deep_logical_proof(mock_federation_stack):
    dec = mock_federation_stack.select_route("Démontre par récurrence que la somme des n premiers entiers vaut n(n+1)/2", policy=RoutingPolicy.PERFORMANCE_FIRST)
    assert "REASONING" in dec.primary_model.capabilities


def test_case_09_multimodal_vision(mock_federation_stack):
    dec = mock_federation_stack.select_route("Décris les anomalies sur cette photo de composant visuel")
    assert any(c in dec.primary_model.capabilities for c in ["VISION", "MULTIMODAL"])


def test_case_10_forensic_investigation(mock_federation_stack):
    dec = mock_federation_stack.select_route("Audite ce dump de trace mémoire pour y déceler une fuite", policy=RoutingPolicy.PERFORMANCE_FIRST)
    assert any(c in dec.primary_model.capabilities for c in ["REASONING", "CODING"])


# =============================================================================
# GROUPE 3 : CONTRAINTES DE LATENCE (Cas 11 à 13)
# =============================================================================

def test_case_11_realtime_lowest_latency(mock_federation_stack):
    dec = mock_federation_stack.select_route("Notification temps réel", policy=RoutingPolicy.LOWEST_LATENCY)
    assert dec.primary_model.latency_tier == LatencyTier.FAST


def test_case_12_fast_gateway(mock_federation_stack):
    dec = mock_federation_stack.select_route("Tâche ultra-rapide", task_type="fast", policy=RoutingPolicy.LOWEST_LATENCY)
    assert dec.primary_model.latency_tier == LatencyTier.FAST


def test_case_13_batch_throughput(mock_federation_stack):
    dec = mock_federation_stack.select_route("Batch de 100 documents", max_latency=LatencyTier.SLOW)
    assert dec.primary_model is not None


# =============================================================================
# GROUPE 4 : CONTRAINTES DE COÛT & SOUVERAINETÉ (Cas 14 à 15)
# =============================================================================

def test_case_14_free_only_zero_euro(mock_federation_stack):
    dec = mock_federation_stack.select_route("Prompt avec contrainte de coût absolu", policy=RoutingPolicy.FREE_ONLY)
    assert dec.primary_model.cost_class in (CostClass.LOCAL, CostClass.FREE_ENDPOINT)


def test_case_15_offline_fail_closed_guarantee(mock_federation_stack):
    dec = mock_federation_stack.select_route("Données classifiées souveraines", policy=RoutingPolicy.OFFLINE)
    assert dec.primary_model.source == ModelSource.LOCAL
    for fb in dec.fallback_chain:
        assert fb.source == ModelSource.LOCAL


# =============================================================================
# GROUPE 5 : PANNES SIMULÉES & RÉSILIENCE DU FALLBACK (Cas 16 à 18)
# =============================================================================

@pytest.mark.asyncio
async def test_case_16_rate_limited_fallback_event(mock_federation_stack):
    # Simuler 429 sur le premier modèle
    mock_federation_stack.providers[ModelSource.LOCAL].generate = AsyncMock(return_value=ProviderResponse(
        content="",
        error_class=ProviderErrorClass.RATE_LIMITED,
        model="qwen3:8b",
        provider="ollama",
    ))
    resp = await mock_federation_stack.complete("Test fallback 429", policy=RoutingPolicy.LOCAL_FIRST)
    trace = resp.raw.get("routing_decision_trace", {})
    assert len(trace.get("fallback_events", [])) >= 1
    assert trace["fallback_events"][0]["error_class"] == "RATE_LIMITED"


@pytest.mark.asyncio
async def test_case_17_timeout_fallback_event(mock_federation_stack):
    # Simuler timeout sur le premier modèle
    mock_federation_stack.providers[ModelSource.LOCAL].generate = AsyncMock(return_value=ProviderResponse(
        content="",
        error_class=ProviderErrorClass.TIMEOUT,
        model="qwen3:8b",
        provider="ollama",
    ))
    resp = await mock_federation_stack.complete("Test fallback timeout", policy=RoutingPolicy.LOCAL_FIRST)
    trace = resp.raw.get("routing_decision_trace", {})
    assert len(trace.get("fallback_events", [])) >= 1
    assert trace["fallback_events"][0]["error_class"] == "TIMEOUT"


@pytest.mark.asyncio
async def test_case_18_all_failed_fail_closed(mock_federation_stack):
    for p in mock_federation_stack.providers.values():
        p.generate = AsyncMock(return_value=ProviderResponse(
            content="",
            error_class=ProviderErrorClass.PROVIDER_UNAVAILABLE,
            model="mock",
            provider="mock",
        ))
    resp = await mock_federation_stack.complete("Passe critique", policy=RoutingPolicy.FREE_ONLY)
    assert resp.content == ""
    assert resp.error_class == ProviderErrorClass.PROVIDER_UNAVAILABLE
    assert resp.raw.get("routing_decision_trace", {}).get("exhausted") is True


# =============================================================================
# GROUPE 6 : DÉTERMINISME STRICT & REPRODUCTIBILITÉ (Cas 19 à 20)
# =============================================================================

def test_case_19_determinism_repeatability(mock_federation_stack):
    query = "Optimisation d'un algorithme de graphe en Python"
    decisions = [
        mock_federation_stack.select_route(query, policy=RoutingPolicy.PERFORMANCE_FIRST)
        for _ in range(10)
    ]
    # Les 10 décisions doivent avoir le même modèle primaire et la même chaîne
    primary_ids = [d.primary_model.model_id for d in decisions]
    assert len(set(primary_ids)) == 1, "Le routage n'est pas déterministe"


def test_case_20_determinism_trace_consistency(mock_federation_stack):
    query = "Calcul matriciel"
    d1 = mock_federation_stack.select_route(query, policy=RoutingPolicy.FREE_ONLY)
    d2 = mock_federation_stack.select_route(query, policy=RoutingPolicy.FREE_ONLY)
    assert d1.primary_model.model_id == d2.primary_model.model_id
    assert [m.model_id for m in d1.fallback_chain] == [m.model_id for m in d2.fallback_chain]
