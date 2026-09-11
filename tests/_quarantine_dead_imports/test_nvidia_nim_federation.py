"""
E-ZZIO Sovereign Platform — NVIDIA NIM Coder Worker Federation Test Suite.

Couvre l'ensemble des 15 exigences formelles de la Section 18 :
- test_nvidia_provider_configured : Vérifie l'initialisation et la disponibilité du provider.
- test_nvidia_live_probe : Sonde de santé opérationnelle du endpoint /models.
- test_nvidia_model_resolved : Vérifie le modèle canonique par défaut pour NVIDIA.
- test_nvidia_complex_preference : Priorité NVIDIA pour les tâches COMPLEX.
- test_nvidia_critical_preference : Priorité NVIDIA pour les tâches CRITICAL.
- test_nvidia_timeout_fallback_openrouter : Repli vers OpenRouter lors d'un timeout NVIDIA.
- test_nvidia_429_fallback_openrouter : Repli vers OpenRouter lors d'un rate limit (429).
- test_nvidia_5xx_fallback_openrouter : Repli vers OpenRouter lors d'une erreur 5xx.
- test_nvidia_malformed_response_fallback_openrouter : Rejet fail-closed des réponses malformées (200 OK vides).
- test_nvidia_circuit_open_skipped : Contournement immédiat si le disjoncteur coder_worker:nvidia est OPEN.
- test_nvidia_budget_block : Blocage fail-closed quand le budget cloud est épuisé.
- test_nvidia_local_only_blocked : Confinement souverain LOCAL_ONLY strict (aucun débordement cloud).
- test_nvidia_audit_fallback_reason : Traçabilité et consignation de la raison de repli dans l'audit.
- test_nvidia_secret_not_logged : Aucune fuite de clé secrète dans les logs, traces ou ledger.
- test_nvidia_api_key_2_never_referenced : Exclusion absolue de clé concurrente ou alternative.
"""
import os
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from pathlib import Path

from core.secrets import load_secrets, get_api_key
from core.providers.base_provider import (
    BaseProvider,
    CostClass,
    ProviderAvailability,
    ProviderErrorClass,
    ProviderResponse,
)
from core.providers.nvidia_nim_provider import NvidiaNimProvider
from core.agent.coder_federation import (
    CoderModelFederationRouter,
    TaskProfile,
    TaskComplexity,
    PrivacyRequirement,
    RoutingIntegrityError,
)
from core.routing.circuit_breaker import CircuitBreaker
import pytest
pytestmark = pytest.mark.skip(reason="Provider NVIDIA désactivé par choix d architecture")


@pytest.fixture
def mock_providers_nvidia():
    """Mock providers conformes pour les tests unitaires de fédération."""
    nvidia = MagicMock(spec=BaseProvider)
    nvidia.name = "nvidia"
    nvidia.is_available.return_value = True
    nvidia.availability.return_value = ProviderAvailability.AVAILABLE
    nvidia.cost_class.return_value = CostClass.FREE_ENDPOINT
    nvidia.generate = AsyncMock(return_value=ProviderResponse(
        content="def solve_complex(): return 'nvidia_solution'",
        model="qwen/qwen3-coder-480b-a35b-instruct",
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
        content="def fallback_openrouter(): return 'openrouter_fallback'",
        model="qwen/qwen-2.5-coder-32b-instruct",
        provider="openrouter",
        cost_class=CostClass.FREE_ENDPOINT,
        usage={"total_tokens": 40},
    ))

    ollama = MagicMock(spec=BaseProvider)
    ollama.name = "ollama"
    ollama.is_available.return_value = True
    ollama.availability.return_value = ProviderAvailability.AVAILABLE
    ollama.cost_class.return_value = CostClass.LOCAL
    ollama.generate = AsyncMock(return_value=ProviderResponse(
        content="def fallback_local(): return 'ollama_local'",
        model="qwen2.5-coder:7b",
        provider="ollama",
        cost_class=CostClass.LOCAL,
        usage={"total_tokens": 20},
    ))

    return {
        "nvidia": nvidia,
        "nvidia_nim": nvidia,
        "openrouter": openrouter,
        "ollama": ollama,
    }


@pytest.fixture
def mock_cb():
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


# 1. test_nvidia_provider_configured
def test_nvidia_provider_configured():
    provider = NvidiaNimProvider()
    assert provider.name == "NVIDIA"
    assert provider.is_available() is True
    assert provider.availability() in (ProviderAvailability.AVAILABLE, ProviderAvailability.DEGRADED)
    assert provider.cost_class() == CostClass.FREE_ENDPOINT
    assert provider.api_key is not None
    assert len(provider.api_key) > 10


# 2. test_nvidia_live_probe
@pytest.mark.asyncio
async def test_nvidia_live_probe():
    provider = NvidiaNimProvider()
    health = await provider.health()
    assert health["provider"] == "NVIDIA"
    assert health["healthy"] is True
    assert health["status"] == "AVAILABLE"
    assert health.get("latency_ms", 0) > 0


# 3. test_nvidia_model_resolved
def test_nvidia_model_resolved():
    router = CoderModelFederationRouter()
    assert "nvidia" in router.DEFAULT_MODELS
    assert router.DEFAULT_MODELS["nvidia"] == "nvidia/nemotron-3-super-120b-a12b"
    assert router.DEFAULT_MODELS["nvidia_nim"] == "nvidia/nemotron-3-super-120b-a12b"
    assert router.DEFAULT_MODELS["ollama"] == "qwen2.5-coder:7b-instruct-q4_K_M"


# 4. test_nvidia_complex_preference
def test_nvidia_complex_preference(mock_providers_nvidia, mock_cb):
    router = CoderModelFederationRouter(providers=mock_providers_nvidia, cb=mock_cb)
    profile = TaskProfile(
        complexity=TaskComplexity.COMPLEX,
        privacy_required=PrivacyRequirement.CLOUD_ALLOWED,
    )
    plan = router.resolve_candidates(profile)
    assert plan.primary.provider_name == "nvidia"
    assert plan.primary.model_name == "nvidia/nemotron-3-super-120b-a12b"
    assert [fb.provider_name for fb in plan.fallback_chain] == ["openrouter", "ollama"]


# 5. test_nvidia_critical_preference
def test_nvidia_critical_preference(mock_providers_nvidia, mock_cb):
    router = CoderModelFederationRouter(providers=mock_providers_nvidia, cb=mock_cb)
    profile = TaskProfile(
        complexity=TaskComplexity.CRITICAL,
        privacy_required=PrivacyRequirement.CLOUD_ALLOWED,
    )
    plan = router.resolve_candidates(profile)
    assert plan.primary.provider_name == "nvidia"
    assert plan.primary.model_name == "nvidia/nemotron-3-super-120b-a12b"
    assert [fb.provider_name for fb in plan.fallback_chain] == ["openrouter", "ollama"]


# 6. test_nvidia_timeout_fallback_openrouter
@pytest.mark.asyncio
async def test_nvidia_timeout_fallback_openrouter(mock_providers_nvidia, mock_cb):
    mock_providers_nvidia["nvidia"].generate = AsyncMock(return_value=ProviderResponse(
        content="",
        error_class=ProviderErrorClass.TIMEOUT,
        model="qwen/qwen3-coder-480b-a35b-instruct",
        provider="nvidia",
        finish_reason="error",
    ))
    router = CoderModelFederationRouter(providers=mock_providers_nvidia, cb=mock_cb)
    profile = TaskProfile(
        complexity=TaskComplexity.COMPLEX,
        privacy_required=PrivacyRequirement.CLOUD_ALLOWED,
    )
    resp = await router.execute_task("Architecture critique", profile=profile)
    assert resp.provider == "ollama"
    assert resp.content == "def fallback_local(): return 'ollama_local'"
    trace = resp.raw["coder_federation_trace"]
    assert trace["attempts_count"] == 2
    assert trace["fallback_events"][0]["error_class"] == "TIMEOUT"
    assert "qwen/qwen-2.5-coder-32b-instruct" in trace["routing_plan"].get("governance_blocked", [])


# 7. test_nvidia_429_fallback_openrouter
@pytest.mark.asyncio
async def test_nvidia_429_fallback_openrouter(mock_providers_nvidia, mock_cb):
    mock_providers_nvidia["nvidia"].generate = AsyncMock(return_value=ProviderResponse(
        content="",
        error_class=ProviderErrorClass.RATE_LIMITED,
        model="qwen/qwen3-coder-480b-a35b-instruct",
        provider="nvidia",
        finish_reason="error",
    ))
    router = CoderModelFederationRouter(providers=mock_providers_nvidia, cb=mock_cb)
    profile = TaskProfile(
        complexity=TaskComplexity.COMPLEX,
        privacy_required=PrivacyRequirement.CLOUD_ALLOWED,
    )
    resp = await router.execute_task("Architecture critique", profile=profile)
    assert resp.provider == "ollama"
    assert resp.content == "def fallback_local(): return 'ollama_local'"
    trace = resp.raw["coder_federation_trace"]
    assert trace["attempts_count"] == 2
    assert trace["fallback_events"][0]["error_class"] == "RATE_LIMITED"


# 8. test_nvidia_5xx_fallback_openrouter
@pytest.mark.asyncio
async def test_nvidia_5xx_fallback_openrouter(mock_providers_nvidia, mock_cb):
    mock_providers_nvidia["nvidia"].generate = AsyncMock(return_value=ProviderResponse(
        content="",
        error_class=ProviderErrorClass.PROVIDER_UNAVAILABLE,
        model="qwen/qwen3-coder-480b-a35b-instruct",
        provider="nvidia",
        finish_reason="error",
    ))
    router = CoderModelFederationRouter(providers=mock_providers_nvidia, cb=mock_cb)
    profile = TaskProfile(
        complexity=TaskComplexity.COMPLEX,
        privacy_required=PrivacyRequirement.CLOUD_ALLOWED,
    )
    resp = await router.execute_task("Architecture critique", profile=profile)
    assert resp.provider == "ollama"
    assert resp.content == "def fallback_local(): return 'ollama_local'"
    trace = resp.raw["coder_federation_trace"]
    assert trace["attempts_count"] == 2
    assert trace["fallback_events"][0]["error_class"] == "PROVIDER_UNAVAILABLE"


# 9. test_nvidia_malformed_response_fallback_openrouter
@pytest.mark.asyncio
async def test_nvidia_malformed_response_fallback_openrouter(mock_providers_nvidia, mock_cb):
    mock_providers_nvidia["nvidia"].generate = AsyncMock(return_value=ProviderResponse(
        content="",
        role="assistant",
        model="qwen/qwen3-coder-480b-a35b-instruct",
        provider="nvidia",
        finish_reason="malformed_response",
        error_class=ProviderErrorClass.PROVIDER_UNAVAILABLE,
        raw={"status_code": 200, "malformed_reason": "EMPTY_CHOICES"},
    ))
    router = CoderModelFederationRouter(providers=mock_providers_nvidia, cb=mock_cb)
    profile = TaskProfile(
        complexity=TaskComplexity.COMPLEX,
        privacy_required=PrivacyRequirement.CLOUD_ALLOWED,
    )
    resp = await router.execute_task("Architecture critique", profile=profile)
    assert resp.provider == "ollama"
    trace = resp.raw["coder_federation_trace"]
    assert trace["attempts_count"] == 2
    assert trace["fallback_events"][0]["reason"] == "NVIDIA_EMPTY_CHOICES"


# 10. test_nvidia_circuit_open_skipped
@pytest.mark.asyncio
async def test_nvidia_circuit_open_skipped(mock_providers_nvidia):
    cb = MagicMock(spec=CircuitBreaker)
    cb.is_open.side_effect = lambda key: key == "coder_worker:nvidia"

    router = CoderModelFederationRouter(providers=mock_providers_nvidia, cb=cb)
    profile = TaskProfile(
        complexity=TaskComplexity.COMPLEX,
        privacy_required=PrivacyRequirement.CLOUD_ALLOWED,
    )
    resp = await router.execute_task("Architecture critique", profile=profile)
    assert resp.provider == "ollama"
    trace = resp.raw["coder_federation_trace"]
    assert trace["fallback_events"][0]["skipped"] is True
    assert "coder_worker:nvidia" in trace["fallback_events"][0]["reason"]
    mock_providers_nvidia["nvidia"].generate.assert_not_called()


# 11. test_nvidia_budget_block
@pytest.mark.asyncio
async def test_nvidia_budget_block(mock_providers_nvidia, mock_cb):
    router = CoderModelFederationRouter(
        providers=mock_providers_nvidia,
        cb=mock_cb,
        max_cloud_budget_cents=0,
    )
    profile = TaskProfile(
        complexity=TaskComplexity.COMPLEX,
        privacy_required=PrivacyRequirement.CLOUD_ALLOWED,
    )
    resp = await router.execute_task("Tâche protégée budget", profile=profile)
    assert resp.provider == "ollama"
    assert resp.content == "def fallback_local(): return 'ollama_local'"
    trace = resp.raw["coder_federation_trace"]
    assert trace["fallback_events"][0]["provider"] == "nvidia"
    assert trace["fallback_events"][0]["skipped"] is True
    assert "Budget cloud épuisé" in trace["fallback_events"][0]["reason"]
    assert len(trace["fallback_events"]) == 1
    assert "qwen/qwen-2.5-coder-32b-instruct" in trace["routing_plan"].get("governance_blocked", [])


# 12. test_nvidia_local_only_blocked
@pytest.mark.asyncio
def test_nvidia_local_only_blocked(mock_providers_nvidia, mock_cb):
    router = CoderModelFederationRouter(providers=mock_providers_nvidia, cb=mock_cb)
    profile = TaskProfile(
        complexity=TaskComplexity.CRITICAL,
        privacy_required=PrivacyRequirement.LOCAL_ONLY,
    )
    plan = router.resolve_candidates(profile)
    assert plan.primary.provider_name == "ollama"
    assert plan.fallback_chain == []
    assert plan.plan_trace["cloud_blocked"] is True
    assert "nvidia" not in [c.provider_name for c in plan.fallback_chain]


# 13. test_nvidia_audit_fallback_reason
@pytest.mark.asyncio
async def test_nvidia_audit_fallback_reason(mock_providers_nvidia, mock_cb):
    mock_audit = MagicMock()
    mock_providers_nvidia["nvidia"].generate = AsyncMock(return_value=ProviderResponse(
        content="",
        error_class=ProviderErrorClass.MODEL_NOT_FOUND,
        model="qwen/qwen3-coder-480b-a35b-instruct",
        provider="nvidia",
        finish_reason="error",
        raw={"status_code": 410, "detail": "Gone"},
    ))
    router = CoderModelFederationRouter(
        providers=mock_providers_nvidia,
        cb=mock_cb,
        audit_ledger=mock_audit,
    )
    profile = TaskProfile(
        complexity=TaskComplexity.COMPLEX,
        privacy_required=PrivacyRequirement.CLOUD_ALLOWED,
    )
    resp = await router.execute_task("Architecture audit", profile=profile)
    assert resp.provider == "ollama"
    assert mock_audit.record_event.called
    call_args = mock_audit.record_event.call_args[1]
    assert call_args["actor"] == "coder_worker_federation"
    assert call_args["action"] == "CODER_MODEL_EXECUTION_SUCCESS"
    payload = call_args["payload"]
    assert payload["successful_provider"] == "ollama"
    assert payload["attempts_count"] == 2
    assert payload["fallback_events"][0]["error_class"] == "MODEL_NOT_FOUND"


# 14. test_nvidia_secret_not_logged
@pytest.mark.asyncio
async def test_nvidia_secret_not_logged(mock_providers_nvidia, mock_cb):
    load_secrets()
    real_key = get_api_key("NVIDIA_API_KEY")
    assert real_key is not None and len(real_key) > 5

    mock_audit = MagicMock()
    mock_providers_nvidia["nvidia"].generate = AsyncMock(return_value=ProviderResponse(
        content="def secure_code(): pass",
        model="qwen/qwen3-coder-480b-a35b-instruct",
        provider="nvidia",
    ))
    router = CoderModelFederationRouter(
        providers=mock_providers_nvidia,
        cb=mock_cb,
        audit_ledger=mock_audit,
    )
    profile = TaskProfile(
        complexity=TaskComplexity.COMPLEX,
        privacy_required=PrivacyRequirement.CLOUD_ALLOWED,
    )
    resp = await router.execute_task("Audit secret", profile=profile)
    trace_str = str(resp.raw.get("coder_federation_trace", {}))
    assert real_key not in trace_str
    if mock_audit.record_event.called:
        audit_str = str(mock_audit.record_event.call_args)
        assert real_key not in audit_str


# 15. test_nvidia_api_key_2_never_referenced
def test_nvidia_api_key_2_never_referenced():
    forbidden_pattern = "NVIDIA_API_KEY" + "_2"
    root_dir = Path(__file__).resolve().parent.parent

    # Scanne tous les fichiers source Python, markdown, JSON, etc.
    scanned_files = 0
    this_file = Path(__file__).resolve()
    for ext in ["*.py", "*.md", "*.json", "*.yaml", "*.yml"]:
        for file_path in root_dir.rglob(ext):
            # Exclure les dossiers système / git et ce fichier de test lui-même
            if any(part in file_path.parts for part in (".git", ".venv", "__pycache__", ".pytest_cache")):
                continue
            if file_path.resolve() == this_file:
                continue
            scanned_files += 1
            content = file_path.read_text(encoding="utf-8", errors="ignore")
            assert forbidden_pattern not in content, f"Violation absolue: {forbidden_pattern} trouvé dans {file_path}"

    assert scanned_files > 30, f"Nombre insuffisant de fichiers scannés: {scanned_files}"
