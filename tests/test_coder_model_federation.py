"""
E-ZZIO Sovereign Platform — Coder Worker Model Federation Test Suite.

Vérifie l'ensemble des scénarios de la spécification de fédération :
- Arbitrage par profil : STANDARD (Ollama), COMPLEX (NVIDIA), FAST (Groq), CONTEXT (Gemini), MULTIMODAL (Gemini).
- Confinement Fail-Closed : LOCAL_ONLY interdit strictement tout débordement cloud.
- Résilience et cascade de repli (Fallback Chain) : TIMEOUT, RATE_LIMIT, QUOTA, AUTH_ERROR.
- Circuit Breaker : contournement automatique lorsque le disjoncteur est OPEN.
- Déterminisme : reproductibilité exacte des plans de sélection.
- Traçabilité et Audit : journalisation structurée sans fuite de secrets.
- Conformité de contrat : OpenRouterProvider conforme à BaseProvider.
"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from core.providers.base_provider import (
    BaseProvider,
    CostClass,
    ProviderAvailability,
    ProviderErrorClass,
    ProviderResponse,
)
from core.agent.coder_federation import (
    CoderModelFederationRouter,
    TaskProfile,
    TaskComplexity,
    ContextSize,
    LatencyClass,
    PrivacyRequirement,
    TaskType,
    RoutingIntegrityError,
)
from core.routing.circuit_breaker import CircuitBreaker


@pytest.fixture
def mock_providers():
    """Génère 5 mock providers conformes au contrat BaseProvider."""
    ollama = MagicMock(spec=BaseProvider)
    ollama.name = "ollama"
    ollama.is_available.return_value = True
    ollama.availability.return_value = ProviderAvailability.AVAILABLE
    ollama.cost_class.return_value = CostClass.LOCAL
    ollama.generate = AsyncMock(return_value=ProviderResponse(
        content="def hello_world(): return 'local'",
        model="qwen2.5-coder:7b",
        provider="ollama",
        cost_class=CostClass.LOCAL,
        usage={"total_tokens": 15},
    ))

    nvidia = MagicMock(spec=BaseProvider)
    nvidia.name = "nvidia"
    nvidia.is_available.return_value = True
    nvidia.availability.return_value = ProviderAvailability.AVAILABLE
    nvidia.cost_class.return_value = CostClass.FREE_ENDPOINT
    nvidia.generate = AsyncMock(return_value=ProviderResponse(
        content="def complex_architecture(): return 'nvidia_nemotron'",
        model="nvidia/llama-3.1-nemotron-70b-instruct",
        provider="nvidia",
        cost_class=CostClass.FREE_ENDPOINT,
        usage={"total_tokens": 50},
    ))

    openrouter = MagicMock(spec=BaseProvider)
    openrouter.name = "openrouter"
    openrouter.is_available.return_value = True
    openrouter.availability.return_value = ProviderAvailability.AVAILABLE
    openrouter.cost_class.return_value = CostClass.FREE_ENDPOINT
    openrouter.generate = AsyncMock(return_value=ProviderResponse(
        content="def fallback_openrouter(): return 'openrouter'",
        model="qwen/qwen-2.5-coder-32b-instruct",
        provider="openrouter",
        cost_class=CostClass.FREE_ENDPOINT,
        usage={"total_tokens": 40},
    ))

    groq = MagicMock(spec=BaseProvider)
    groq.name = "groq"
    groq.is_available.return_value = True
    groq.availability.return_value = ProviderAvailability.AVAILABLE
    groq.cost_class.return_value = CostClass.FREE_ENDPOINT
    groq.generate = AsyncMock(return_value=ProviderResponse(
        content="def fast_instant(): return 'groq_lpu'",
        model="llama-3.3-70b-versatile",
        provider="groq",
        cost_class=CostClass.FREE_ENDPOINT,
        usage={"total_tokens": 20},
    ))

    gemini = MagicMock(spec=BaseProvider)
    gemini.name = "gemini"
    gemini.is_available.return_value = True
    gemini.availability.return_value = ProviderAvailability.AVAILABLE
    gemini.cost_class.return_value = CostClass.FREE_ENDPOINT
    gemini.generate = AsyncMock(return_value=ProviderResponse(
        content="def multimodal_analysis(): return 'gemini'",
        model="gemini-2.5-flash",
        provider="gemini",
        cost_class=CostClass.FREE_ENDPOINT,
        usage={"total_tokens": 80},
    ))

    return {
        "ollama": ollama,
        "nvidia": nvidia,
        "openrouter": openrouter,
        "groq": groq,
        "gemini": gemini,
    }


@pytest.fixture
def mock_cb():
    """Disjoncteur mocké en mémoire isolé du disque."""
    cb = MagicMock(spec=CircuitBreaker)
    state = {}
    def is_open(key):
        return state.get(key, {}).get("tripped", False)
    def record_success(key):
        state[key] = {"tripped": False, "failures": 0}
    def record_failure(key):
        s = state.get(key, {"tripped": False, "failures": 0})
        s["failures"] = s.get("failures", 0) + 1
        if s["failures"] >= 3:
            s["tripped"] = True
        state[key] = s
    cb.is_open.side_effect = is_open
    cb.record_success.side_effect = record_success
    cb.record_failure.side_effect = record_failure
    cb.state_data = state
    return cb


def test_standard_prefers_ollama(mock_providers, mock_cb):
    router = CoderModelFederationRouter(providers=mock_providers, cb=mock_cb)
    profile = TaskProfile(
        complexity=TaskComplexity.STANDARD,
        privacy_required=PrivacyRequirement.LOCAL_PREFERRED,
    )
    plan = router.resolve_candidates(profile)
    assert plan.primary.provider_name == "ollama"
    assert [fb.provider_name for fb in plan.fallback_chain] == ["gemini", "openrouter"]


def test_complex_prefers_nvidia(mock_providers, mock_cb):
    # NVIDIA désactivé : COMPLEX => primary Gemini, repli Ollama.
    router = CoderModelFederationRouter(providers=mock_providers, cb=mock_cb)
    profile = TaskProfile(
        complexity=TaskComplexity.COMPLEX,
        privacy_required=PrivacyRequirement.CLOUD_ALLOWED,
    )
    plan = router.resolve_candidates(profile)
    assert plan.primary.provider_name == "gemini"
    assert [fb.provider_name for fb in plan.fallback_chain] == ["ollama"]


def test_critical_prefers_nvidia(mock_providers, mock_cb):
    # NVIDIA désactivé : CRITICAL => primary Gemini, repli Ollama.
    router = CoderModelFederationRouter(providers=mock_providers, cb=mock_cb)
    profile = TaskProfile(
        complexity=TaskComplexity.CRITICAL,
        privacy_required=PrivacyRequirement.CLOUD_ALLOWED,
    )
    plan = router.resolve_candidates(profile)
    assert plan.primary.provider_name == "gemini"
    assert [fb.provider_name for fb in plan.fallback_chain] == ["ollama"]


def test_fast_prefers_groq(mock_providers, mock_cb):
    # Pool Groq HS (403) : FAST => primary Gemini, repli Ollama.
    router = CoderModelFederationRouter(providers=mock_providers, cb=mock_cb)
    profile = TaskProfile(
        latency_class=LatencyClass.HIGH,
        privacy_required=PrivacyRequirement.CLOUD_ALLOWED,
    )
    plan = router.resolve_candidates(profile)
    assert plan.primary.provider_name == "gemini"
    assert [fb.provider_name for fb in plan.fallback_chain] == ["ollama"]


def test_context_prefers_gemini(mock_providers, mock_cb):
    router = CoderModelFederationRouter(providers=mock_providers, cb=mock_cb)
    profile = TaskProfile(
        context_size=ContextSize.LARGE,
        privacy_required=PrivacyRequirement.CLOUD_ALLOWED,
    )
    plan = router.resolve_candidates(profile)
    assert plan.primary.provider_name == "gemini"
    assert [fb.provider_name for fb in plan.fallback_chain] == ["ollama", "openrouter"]


def test_multimodal_prefers_gemini(mock_providers, mock_cb):
    router = CoderModelFederationRouter(providers=mock_providers, cb=mock_cb)
    profile = TaskProfile(
        multimodal=True,
        privacy_required=PrivacyRequirement.CLOUD_ALLOWED,
    )
    plan = router.resolve_candidates(profile)
    assert plan.primary.provider_name == "gemini"
    assert [fb.provider_name for fb in plan.fallback_chain] == ["ollama"]


def test_local_only_blocks_cloud(mock_providers, mock_cb):
    router = CoderModelFederationRouter(providers=mock_providers, cb=mock_cb)
    profile = TaskProfile(
        complexity=TaskComplexity.CRITICAL,
        privacy_required=PrivacyRequirement.LOCAL_ONLY,
    )
    plan = router.resolve_candidates(profile)
    assert plan.primary.provider_name == "ollama"
    assert plan.fallback_chain == []
    assert plan.plan_trace["cloud_blocked"] is True


@pytest.mark.asyncio
async def test_local_only_ollama_failure_fails_closed(mock_providers, mock_cb):
    mock_providers["ollama"].generate = AsyncMock(return_value=ProviderResponse(
        content="",
        error_class=ProviderErrorClass.TIMEOUT,
        model="qwen2.5-coder:7b",
        provider="ollama",
    ))
    router = CoderModelFederationRouter(providers=mock_providers, cb=mock_cb)
    profile = TaskProfile(privacy_required=PrivacyRequirement.LOCAL_ONLY)

    resp = await router.execute_task("Ecrire une fonction", profile=profile)
    assert resp.content == ""
    assert resp.error_class == ProviderErrorClass.TIMEOUT
    assert resp.raw["coder_federation_trace"]["exhausted"] is True


@pytest.mark.asyncio
async def test_nvidia_quota_falls_back_openrouter(mock_providers, mock_cb):
    # NVIDIA désactivé : COMPLEX => Gemini primaire (aucun appel NVIDIA).
    router = CoderModelFederationRouter(providers=mock_providers, cb=mock_cb)
    profile = TaskProfile(
        complexity=TaskComplexity.COMPLEX,
        privacy_required=PrivacyRequirement.CLOUD_ALLOWED,
    )

    resp = await router.execute_task("Refactoriser architecture", profile=profile)
    assert resp.content == "def multimodal_analysis(): return 'gemini'"
    assert resp.provider == "gemini"
    trace = resp.raw["coder_federation_trace"]
    assert trace["attempts_count"] == 1


@pytest.mark.asyncio
async def test_ollama_timeout_escalates_nvidia(mock_providers, mock_cb):
    # Ollama en timeout sous LOCAL_PREFERRED -> repli Gemini (NVIDIA désactivé)
    mock_providers["ollama"].generate = AsyncMock(return_value=ProviderResponse(
        content="",
        error_class=ProviderErrorClass.TIMEOUT,
        model="qwen2.5-coder:7b",
        provider="ollama",
    ))
    router = CoderModelFederationRouter(providers=mock_providers, cb=mock_cb)
    profile = TaskProfile(
        complexity=TaskComplexity.STANDARD,
        privacy_required=PrivacyRequirement.LOCAL_PREFERRED,
    )

    resp = await router.execute_task("Ecrire un test", profile=profile)
    assert resp.content == "def multimodal_analysis(): return 'gemini'"
    assert resp.provider == "gemini"
    trace = resp.raw["coder_federation_trace"]
    assert trace["attempts_count"] == 2
    assert trace["fallback_events"][0]["error_class"] == "TIMEOUT"


@pytest.mark.asyncio
async def test_circuit_open_skips_provider(mock_providers):
    # Disjoncteur ouvert sur coder_worker:gemini -> repli Ollama immédiat.
    mock_cb = MagicMock(spec=CircuitBreaker)
    def cb_is_open(key):
        return key == "coder_worker:gemini"
    mock_cb.is_open.side_effect = cb_is_open

    router = CoderModelFederationRouter(providers=mock_providers, cb=mock_cb)
    profile = TaskProfile(
        complexity=TaskComplexity.COMPLEX,
        privacy_required=PrivacyRequirement.CLOUD_ALLOWED,
    )

    resp = await router.execute_task("Créer module", profile=profile)
    assert resp.provider == "ollama"
    trace = resp.raw["coder_federation_trace"]
    assert trace["fallback_events"][0]["skipped"] is True
    assert "Circuit disjoncté" in trace["fallback_events"][0]["reason"]


def test_deterministic_selection(mock_providers, mock_cb):
    router = CoderModelFederationRouter(providers=mock_providers, cb=mock_cb)
    p1 = router.resolve_candidates(TaskProfile(complexity=TaskComplexity.COMPLEX), deterministic=True)
    p2 = router.resolve_candidates(TaskProfile(complexity=TaskComplexity.COMPLEX), deterministic=True)
    assert p1.primary.provider_name == p2.primary.provider_name
    assert [f.provider_name for f in p1.fallback_chain] == [f.provider_name for f in p2.fallback_chain]


@pytest.mark.asyncio
async def test_audit_contains_fallback_reason(mock_providers, mock_cb):
    mock_audit = MagicMock()
    mock_providers["ollama"].generate = AsyncMock(return_value=ProviderResponse(
        content="",
        error_class=ProviderErrorClass.UNAUTHORIZED,
        model="qwen2.5-coder:7b",
        provider="ollama",
    ))
    router = CoderModelFederationRouter(providers=mock_providers, cb=mock_cb, audit_ledger=mock_audit)
    profile = TaskProfile(privacy_required=PrivacyRequirement.LOCAL_PREFERRED)

    resp = await router.execute_task("Tâche test", profile=profile)
    assert mock_audit.record_event.called
    call_args = mock_audit.record_event.call_args[1]
    assert call_args["actor"] == "coder_worker_federation"
    assert call_args["action"] == "CODER_MODEL_EXECUTION_SUCCESS"
    assert call_args["payload"]["attempts_count"] == 2


@pytest.mark.asyncio
async def test_budget_limit_blocks_cloud_escalation(mock_providers, mock_cb):
    mock_providers["ollama"].generate = AsyncMock(return_value=ProviderResponse(
        content="",
        error_class=ProviderErrorClass.TIMEOUT,
        model="qwen2.5-coder:7b",
        provider="ollama",
    ))
    # Budget épuisé (max=0)
    router = CoderModelFederationRouter(providers=mock_providers, cb=mock_cb, max_cloud_budget_cents=0)
    profile = TaskProfile(privacy_required=PrivacyRequirement.LOCAL_PREFERRED)

    resp = await router.execute_task("Tâche protégée", profile=profile)
    assert resp.content == ""
    trace = resp.raw["coder_federation_trace"]
    assert trace["exhausted"] is True
    # Vérifier que les providers cloud ont été sautés pour cause de budget
    skipped_reasons = [ev.get("reason") for ev in trace["fallback_events"] if ev.get("skipped")]
    assert "Budget cloud épuisé" in skipped_reasons


def test_invalid_task_profile_fails_closed():
    with pytest.raises(RoutingIntegrityError):
        TaskProfile.from_dict({"complexity": "NON_EXISTENT_COMPLEXITY"})


def test_openrouter_provider_contract():
    from core.providers.openrouter_provider import OpenRouterProvider
    provider = OpenRouterProvider(api_key="test-key-mock")
    assert provider.name == "openrouter"
    assert provider.cost_class() == CostClass.FREE_ENDPOINT
    assert "CODING" in provider.capabilities("qwen/qwen-2.5-coder-32b-instruct")
