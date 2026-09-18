"""
E-ZZIO — tests/test_registry_auto_refresh.py
=============================================
Tests unitaires du mécanisme d'auto-refresh du registre Gemini.

Phases testées (selon spec PHASE 11) :
  TEST 1 — Startup success
  TEST 2 — Startup Google failure (E-ZzIO continue)
  TEST 3 — Manual trigger
  TEST 4 — Daily scheduler (tick simulé)
  TEST 5 — Scheduler resilience (refresh #1 fail → refresh #2 OK)
  TEST 6 — Concurrent refresh (lock — pas de corruption)
  TEST 7 — No auto-activation (nouveaux modèles restent CANDIDATE)
  TEST 8 — Routing isolation (gemini_pool non modifié, fichiers attendus présents)
  TEST 9 — Secret safety (réponses et stats)

NB : on teste GeminiRegistryRefreshService en isolation totale.
On ne lance PAS le vrai web_server ni le vrai refresh Gemini.
"""
from __future__ import annotations

import asyncio
from typing import Any
from unittest.mock import AsyncMock, patch

import pytest

from core.models.registry_refresh_service import GeminiRegistryRefreshService

# ── Résultat factice sans secret ──────────────────────────────────────────────
_FAKE_SUCCESS_RESULT: dict[str, Any] = {
    "timestamp_iso": "2026-09-01T12:00:00+00:00",
    "timestamp_unix": 1756728000.0,
    "source": "https://generativelanguage.googleapis.com/v1beta/models",
    "duration_seconds": 0.42,
    "discovered_count": 38,
    "valid_count": 38,
    "registry_count_before": 71,
    "registry_count_after": 71,
    "new_models": [],
    "existing_models": ["gemini-2.5-flash", "gemini-2.5-pro"],
    "missing_from_api": [],
    "superseded_models": [],
    "invalid_models": [],
    "errors": [],
    "warnings": [],
    "audit_path": "/state/audit/discovery/gemini_2026-09-01.json",
}

_SECRET_SENTINEL = "sk-abc123-SHOULD_NOT_APPEAR"

# Patch à la source : refresh_gemini_registry_async est importé localement
# dans _do_refresh(), donc on le patch dans registry_refresh, pas dans le service.
_PATCH_TARGET = "core.models.registry_refresh.refresh_gemini_registry_async"


def _make_service(interval: float = 3600.0) -> GeminiRegistryRefreshService:
    """Crée une instance isolée (pas le singleton applicatif)."""
    return GeminiRegistryRefreshService(scheduler_interval=interval)


# ─────────────────────────────────────────────────────────────────────────────
# TEST 1 : Startup success
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_startup_success():
    """Startup réussi → status=success, scheduler démarré."""
    svc = _make_service()
    with patch(_PATCH_TARGET, new=AsyncMock(return_value=_FAKE_SUCCESS_RESULT)):
        result = await svc.startup()

    assert result["status"] == "success"
    assert result["trigger"] == "startup"
    assert result["provider"] == "gemini"
    assert result["discovered_count"] == 38

    assert svc._scheduler_task is not None
    assert not svc._scheduler_task.done()

    await svc.shutdown()


# ─────────────────────────────────────────────────────────────────────────────
# TEST 2 : Startup Google failure → E-ZzIO continue
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_startup_google_failure_does_not_block():
    """
    Google API indisponible → WARNING, status=failure, mais startup() retourne.
    CRITIQUE : NE DOIT PAS lever d'exception.
    """
    svc = _make_service()
    with patch(_PATCH_TARGET, new=AsyncMock(side_effect=ConnectionError("Google unreachable"))):
        result = await svc.startup()

    assert result["status"] == "failure"
    assert "error" in result
    assert _SECRET_SENTINEL not in str(result)
    # Le scheduler est quand même démarré
    assert svc._scheduler_task is not None
    await svc.shutdown()


# ─────────────────────────────────────────────────────────────────────────────
# TEST 3 : Manual trigger
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_manual_trigger():
    """trigger() appelle refresh et retourne un résultat structuré."""
    svc = _make_service()
    mock = AsyncMock(return_value=_FAKE_SUCCESS_RESULT)
    with patch(_PATCH_TARGET, new=mock):
        result = await svc.trigger()

    assert result["status"] == "success"
    assert result["trigger"] == "manual"
    assert result["provider"] == "gemini"
    mock.assert_awaited_once()


# ─────────────────────────────────────────────────────────────────────────────
# TEST 4 : Scheduler — tick simulé
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_scheduler_fires_after_interval():
    """Scheduler déclenche un refresh après l'intervalle (simulé à 50ms)."""
    svc = _make_service(interval=0.05)
    call_count = 0

    async def fake_refresh(**_):
        nonlocal call_count
        call_count += 1
        return _FAKE_SUCCESS_RESULT

    with patch(_PATCH_TARGET, new=AsyncMock(side_effect=fake_refresh)):
        await svc.startup()
        await asyncio.sleep(0.25)
        await svc.shutdown()

    # startup (1) + au moins 1 tick scheduler
    assert call_count >= 2


# ─────────────────────────────────────────────────────────────────────────────
# TEST 5 : Scheduler resilience
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_scheduler_survives_refresh_failure():
    """
    Refresh tick #1 échoue → scheduler continue, tick #2 réussit.
    """
    svc = _make_service(interval=0.05)
    call_count = 0

    async def alternating(**_):
        nonlocal call_count
        call_count += 1
        if call_count == 2:
            raise RuntimeError("Simulated Gemini failure")
        return _FAKE_SUCCESS_RESULT

    with patch(_PATCH_TARGET, new=AsyncMock(side_effect=alternating)):
        await svc.startup()
        await asyncio.sleep(0.35)
        await svc.shutdown()

    assert call_count >= 3
    stats = svc.stats()
    assert stats["gemini_registry_refresh_failure"] >= 1
    assert stats["gemini_registry_refresh_success"] >= 2


# ─────────────────────────────────────────────────────────────────────────────
# TEST 6 : Concurrent refresh — lock
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_concurrent_refresh_uses_lock():
    """
    Refresh déjà en cours → trigger() retourne status=skipped.
    Pas de corruption, pas de doublons.
    """
    svc = _make_service()
    barrier = asyncio.Event()
    refresh_started = asyncio.Event()

    async def slow_refresh(**_):
        refresh_started.set()
        await barrier.wait()
        return _FAKE_SUCCESS_RESULT

    with patch(_PATCH_TARGET, new=AsyncMock(side_effect=slow_refresh)):
        task = asyncio.create_task(svc._do_refresh(trigger="test"))
        await refresh_started.wait()

        result = await svc.trigger()
        assert result["status"] == "skipped"
        assert result["reason"] == "refresh_already_running"

        barrier.set()
        await task

    assert svc.stats()["gemini_registry_refresh_total"] == 1


# ─────────────────────────────────────────────────────────────────────────────
# TEST 7 : No auto-activation
# ─────────────────────────────────────────────────────────────────────────────

def test_no_auto_activation():
    """
    Tous les modèles Gemini dans le registre réel sont CANDIDATE, jamais ACTIVE.
    """
    from pathlib import Path

    from core.models.registry import ModelRegistry

    registry = ModelRegistry(Path("G:/AI/E-zzio/data/models/registry.json"))
    gemini = [r for r in registry.all() if r.provider.lower() == "gemini"]

    active = [r for r in gemini if r.lifecycle == "ACTIVE"]
    assert active == [], f"Modèles ACTIVE inattendus : {[r.model_id for r in active]}"


# ─────────────────────────────────────────────────────────────────────────────
# TEST 8 : Routing isolation
# ─────────────────────────────────────────────────────────────────────────────

def test_routing_isolation():
    """
    gemini_pool.py non modifié.
    Nos fichiers créés existent.
    """
    import subprocess
    from pathlib import Path

    # gemini_pool.py ne doit pas avoir été modifié par nos changements
    result = subprocess.run(
        ["git", "diff", "--name-only", "--", "core/models/gemini_pool.py"],
        capture_output=True, text=True, cwd="G:/AI/E-zzio",
    )
    modified = [l.strip() for l in result.stdout.splitlines() if l.strip()]
    assert modified == [], f"gemini_pool.py modifié : {modified}"

    # Nos fichiers doivent exister
    repo = Path("G:/AI/E-zzio")
    expected = [
        "core/models/registry_refresh_service.py",
        "routers/registry.py",
        "tests/test_registry_auto_refresh.py",
        "web_server.py",
    ]
    for f in expected:
        assert (repo / f).exists(), f"Fichier manquant : {f}"


# ─────────────────────────────────────────────────────────────────────────────
# TEST 9 : Secret safety
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_secret_safety_in_response():
    """trigger() ne propage pas de champs secrets dans sa réponse."""
    svc = _make_service()
    poisoned = {**_FAKE_SUCCESS_RESULT, "api_key": _SECRET_SENTINEL}
    with patch(_PATCH_TARGET, new=AsyncMock(return_value=poisoned)):
        result = await svc.trigger()

    assert _SECRET_SENTINEL not in str(result), "SECRET LEAK dans trigger()"
    assert _SECRET_SENTINEL not in str(svc.stats()), "SECRET LEAK dans stats()"


@pytest.mark.asyncio
async def test_secret_safety_startup_failure():
    """startup() ne propage pas les détails d'exception (potentiels secrets) dans sa réponse."""
    svc = _make_service()
    exc = ConnectionError(f"Auth error key={_SECRET_SENTINEL}")
    with patch(_PATCH_TARGET, new=AsyncMock(side_effect=exc)):
        result = await svc.startup()

    assert result["status"] == "failure"
    assert _SECRET_SENTINEL not in str(result)
    await svc.shutdown()
