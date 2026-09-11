"""E-ZZIO Phase 18.1 — Tests déterministes des blockers R-01 / R-02 / E2E-03.

Aucun appel LLM : providers mockés, ledger d'audit temporaire, rejet Master
sans inférence. Couvre :
- R-01 : target explicite inconnu -> rejet Fail-Closed, aucune inférence.
- R-02 : succès et échec fédérés -> lignes d'audit persistées (SUCCESS / FAILED).
- E2E-03 A : cloud/primary disponible -> pas de fallback (attempts_count == 1).
- E2E-03 B : primary KO -> fallback autorisé utilisé, raisons présentes.
- E2E-03 C : LOCAL_ONLY + local KO -> échec contrôlé, aucun appel cloud.
"""
import asyncio
from unittest.mock import AsyncMock, MagicMock

import pytest

from core.agent.coder_federation import (
    CoderModelFederationRouter,
    TaskComplexity,
    TaskProfile,
    PrivacyRequirement,
)
from core.ezzio_master import EzzioMaster, UnknownModelTargetError
from core.providers.base_provider import (
    BaseProvider,
    CostClass,
    ProviderAvailability,
    ProviderErrorClass,
    ProviderResponse,
)
from core.routing.circuit_breaker import CircuitBreaker
from core.security.audit_ledger import AuditLedger


def _mock_provider(name, content=None, error=None, available=True):
    mock = MagicMock(spec=BaseProvider)
    mock.name = name
    mock.is_available.return_value = available
    mock.availability.return_value = (
        ProviderAvailability.AVAILABLE if available else ProviderAvailability.UNAVAILABLE
    )
    if error is not None:
        mock.generate = AsyncMock(return_value=ProviderResponse(
            content="",
            model=f"{name}-model",
            provider=name,
            cost_class=CostClass.FREE_ENDPOINT,
            error_class=error,
        ))
    else:
        mock.generate = AsyncMock(return_value=ProviderResponse(
            content=content or f"ok from {name}",
            model=f"{name}-model",
            provider=name,
            cost_class=CostClass.LOCAL if name == "ollama" else CostClass.FREE_ENDPOINT,
        ))
    return mock


@pytest.fixture
def mock_cb():
    cb = MagicMock(spec=CircuitBreaker)
    cb.is_open.return_value = False
    return cb


@pytest.fixture
def standard_profile():
    return TaskProfile(
        complexity=TaskComplexity.STANDARD,
        privacy_required=PrivacyRequirement.LOCAL_PREFERRED,
    )


# ---------------- R-01 : validation du target ----------------

def test_r01_unknown_target_raises():
    master = EzzioMaster.__new__(EzzioMaster)
    with pytest.raises(UnknownModelTargetError):
        EzzioMaster._resolve_task_profile(
            master, mission_profile="STANDARD", model_target="modele_inexistant_xyz_123"
        )


def test_r01_known_and_auto_targets_accepted():
    master = EzzioMaster.__new__(EzzioMaster)
    for target in ("auto", None, "", "ollama", "local", "gemini", "gemini_cloud"):
        EzzioMaster._resolve_task_profile(
            master, mission_profile="STANDARD", model_target=target
        )


def test_r01_nvidia_target_rejected():
    # NVIDIA désactivé : toute demande explicite est refusée (fail-closed).
    master = EzzioMaster.__new__(EzzioMaster)
    for target in ("nvidia", "nvidia_nim"):
        with pytest.raises(UnknownModelTargetError):
            EzzioMaster._resolve_task_profile(
                master, mission_profile="STANDARD", model_target=target
            )


def test_r01_execute_intent_rejects_without_inference():
    master = EzzioMaster.__new__(EzzioMaster)
    fake_router = MagicMock()
    fake_router.execute_task = AsyncMock()
    fake_router._record_audit = MagicMock()
    master.federation_router = fake_router
    master._memory_initialized = True
    master.memory = MagicMock()
    res = asyncio.run(master.execute_intent(
        "Test rejet", model_target="modele_inexistant_xyz_123", session_id="",
    ))
    assert res["ok"] is False
    assert res["provider"] == "none"
    assert res["model"] == "none"
    assert "FAIL-CLOSED" in res["error"]
    fake_router.execute_task.assert_not_called()
    fake_router._record_audit.assert_called_once()
    action = fake_router._record_audit.call_args.kwargs.get("action")
    assert action == "MASTER_TARGET_REJECTED"


# ---------------- R-02 : audit persisté ----------------

def test_r02_success_records_audit(tmp_path, mock_cb):
    ledger = AuditLedger(db_path=str(tmp_path / "audit.db"))
    router = CoderModelFederationRouter(
        providers={"ollama": _mock_provider("ollama", content="ok local")},
        cb=mock_cb,
        audit_ledger=ledger,
    )
    profile = TaskProfile(
        complexity=TaskComplexity.STANDARD,
        privacy_required=PrivacyRequirement.LOCAL_ONLY,
    )
    resp = asyncio.run(router.execute_task(prompt="test", profile=profile))
    assert resp.content == "ok local"
    ok, count, _ = ledger.verify_chain_integrity()
    assert ok and count == 1


def test_r02_failure_records_audit(tmp_path, mock_cb):
    ledger = AuditLedger(db_path=str(tmp_path / "audit.db"))
    router = CoderModelFederationRouter(
        providers={"ollama": _mock_provider("ollama", available=False)},
        cb=mock_cb,
        audit_ledger=ledger,
    )
    profile = TaskProfile(
        complexity=TaskComplexity.STANDARD,
        privacy_required=PrivacyRequirement.LOCAL_ONLY,
    )
    resp = asyncio.run(router.execute_task(prompt="test", profile=profile))
    assert resp.error_class == ProviderErrorClass.PROVIDER_UNAVAILABLE
    ok, count, _ = ledger.verify_chain_integrity()
    assert ok and count == 1


# ---------------- E2E-03 : Cloud First / fallback déterministes ----------------

def test_e2e03_a_primary_available_no_fallback(mock_cb, standard_profile):
    router = CoderModelFederationRouter(
        providers={
            "ollama": _mock_provider("ollama", content="ok local"),
            "nvidia": _mock_provider("nvidia", content="ok nvidia"),
            "openrouter": _mock_provider("openrouter", content="ok or"),
        },
        cb=mock_cb,
    )
    resp = asyncio.run(router.execute_task(prompt="test", profile=standard_profile))
    trace = resp.raw["coder_federation_trace"]
    assert resp.provider == "ollama"
    assert trace["attempts_count"] == 1
    assert trace["fallback_events"] == []


def test_e2e03_b_cloud_ko_fallback_allowed(mock_cb, standard_profile):
    ollama = _mock_provider("ollama", available=False)
    gemini = _mock_provider("gemini", content="ok gemini")
    router = CoderModelFederationRouter(
        providers={"ollama": ollama, "gemini": gemini},
        cb=mock_cb,
    )
    resp = asyncio.run(router.execute_task(prompt="test", profile=standard_profile))
    trace = resp.raw["coder_federation_trace"]
    assert resp.provider == "gemini"
    assert trace["attempts_count"] > 1
    assert len(trace["fallback_events"]) >= 1
    assert all("reason" in ev or "error" in ev for ev in trace["fallback_events"])


def test_e2e03_c_local_only_no_cloud_call(tmp_path, mock_cb):
    openrouter = _mock_provider("openrouter", content="ok or")
    router = CoderModelFederationRouter(
        providers={
            "ollama": _mock_provider("ollama", available=False),
            "openrouter": openrouter,
        },
        cb=mock_cb,
        audit_ledger=AuditLedger(db_path=str(tmp_path / "audit.db")),
    )
    profile = TaskProfile(
        complexity=TaskComplexity.STANDARD,
        privacy_required=PrivacyRequirement.LOCAL_ONLY,
    )
    resp = asyncio.run(router.execute_task(prompt="test", profile=profile))
    openrouter.generate.assert_not_called()
    assert resp.error_class == ProviderErrorClass.PROVIDER_UNAVAILABLE
    assert resp.raw["coder_federation_trace"]["exhausted"] is True
