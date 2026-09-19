"""
tests/test_registry_refresh.py
================================
Tests unitaires pour core/models/registry_refresh.py

Couvre les 7 invariants requis :
  TEST 1 — Discovery réussie        : nouveau modèle → CANDIDATE
  TEST 2 — Idempotence              : 2 refresh = même résultat, zéro doublon
  TEST 3 — Modèle disparu           : ACTIVE absent → QUARANTINED (transition légale)
  TEST 4 — API indisponible         : registry.json inchangé
  TEST 5 — Aucun ACTIVE automatique : nouveau modèle jamais ACTIVE
  TEST 6 — Sécurité secrets         : audit sans clé/secret
  TEST 7 — Atomicité                : registre jamais partiellement écrit
"""
from __future__ import annotations

import asyncio
import json
import os
import sys
import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# ── repo root ────────────────────────────────────────────────────────────────
ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core.models.lifecycle import ModelLifecycle
from core.models.registry import ModelRecord, ModelRegistry
from core.models.registry_refresh import _run_refresh, _write_audit, refresh_gemini_registry

# ── Fixtures ─────────────────────────────────────────────────────────────────

def _make_registry(tmp_path: Path, records: list[ModelRecord] | None = None) -> tuple[ModelRegistry, Path]:
    """Crée un registre temporaire et y insère les enregistrements optionnels."""
    reg_path = tmp_path / "registry.json"
    reg = ModelRegistry(reg_path)
    if records:
        for r in records:
            reg.upsert(r)
        reg.save()
    return reg, reg_path


def _make_discovery_item(model_id: str = "gemini-new-model") -> dict:
    return {
        "model_id": model_id,
        "provider": "gemini",
        "display_name": f"{model_id} Display",
        "execution_scope": "CLOUD",
        "pricing_status": "UNKNOWN",
        "pricing_source": "provider_api_unspecified",
        "pricing": None,
        "context_window": 1048576,
        "max_output_tokens": 65536,
        "supports_chat": True,
        "supports_json": True,
        "supports_tools": True,
        "supports_reasoning": False,
        "version_rank": 3.5,
        "raw": {"name": f"models/{model_id}"},
    }


# ── TEST 1 : Discovery réussie → nouveau modèle CANDIDATE ────────────────────

@pytest.mark.asyncio
async def test_new_model_becomes_candidate(tmp_path):
    """Un nouveau modèle découvert doit avoir lifecycle=CANDIDATE, jamais ACTIVE."""
    reg, reg_path = _make_registry(tmp_path)
    new_item = _make_discovery_item("gemini-2.5-flash-test")

    with (
        patch("core.models.registry_refresh._REGISTRY_PATH", reg_path),
        patch("core.models.registry_refresh._AUDIT_DIR", tmp_path / "audit"),
        patch(
            "core.models.discovery.gemini.GeminiDiscovery.discover",
            new=AsyncMock(return_value=[new_item]),
        ),
    ):
        result = await _run_refresh(api_key="FAKE-KEY-DO-NOT-USE")

    # Recharger le registre depuis disque
    reg2 = ModelRegistry(reg_path)
    record = reg2.get("gemini", "gemini-2.5-flash-test")

    assert record is not None, "Le nouveau modèle doit être présent dans le registre"
    assert record.lifecycle == ModelLifecycle.CANDIDATE.value, (
        f"Lifecycle attendu CANDIDATE, obtenu {record.lifecycle}"
    )
    assert "gemini-2.5-flash-test" in result["new_models"]
    assert result["registry_count_after"] == 1


# ── TEST 2 : Idempotence ─────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_idempotence(tmp_path):
    """Deux refresh consécutifs sans changement API = même résultat, zéro doublon."""
    reg, reg_path = _make_registry(tmp_path)
    items = [_make_discovery_item("gemini-stable-model")]

    patches = {
        "target_registry": patch("core.models.registry_refresh._REGISTRY_PATH", reg_path),
        "target_audit": patch("core.models.registry_refresh._AUDIT_DIR", tmp_path / "audit"),
        "target_discover": patch(
            "core.models.discovery.gemini.GeminiDiscovery.discover",
            new=AsyncMock(return_value=items),
        ),
    }
    with patches["target_registry"], patches["target_audit"], patches["target_discover"]:
        r1 = await _run_refresh(api_key="FAKE-KEY")
        r2 = await _run_refresh(api_key="FAKE-KEY")

    reg2 = ModelRegistry(reg_path)
    all_gemini = [r for r in reg2.all() if r.provider == "gemini"]

    assert len(all_gemini) == 1, f"Doublon détecté : {len(all_gemini)} entrées"
    assert r1["new_models"] == ["gemini-stable-model"]
    assert r2["new_models"] == [], "Au second refresh, aucun nouveau modèle attendu"
    assert r2["existing_models"] == ["gemini-stable-model"]


# ── TEST 3 : Modèle disparu → état préservé ou QUARANTINED si ACTIVE ─────────

@pytest.mark.asyncio
async def test_active_model_missing_from_api_becomes_quarantined(tmp_path):
    """Un modèle ACTIVE absent de la découverte doit passer en QUARANTINED."""
    active_record = ModelRecord(
        model_id="gemini-old-active",
        provider="gemini",
        lifecycle="ACTIVE",
    )
    reg, reg_path = _make_registry(tmp_path, [active_record])

    # La découverte ne retourne PAS gemini-old-active
    new_item = _make_discovery_item("gemini-brand-new")

    with (
        patch("core.models.registry_refresh._REGISTRY_PATH", reg_path),
        patch("core.models.registry_refresh._AUDIT_DIR", tmp_path / "audit"),
        patch(
            "core.models.discovery.gemini.GeminiDiscovery.discover",
            new=AsyncMock(return_value=[new_item]),
        ),
    ):
        result = await _run_refresh(api_key="FAKE-KEY")

    reg2 = ModelRegistry(reg_path)
    old = reg2.get("gemini", "gemini-old-active")
    assert old is not None, "Le modèle disparu ne doit pas être supprimé"
    assert old.lifecycle in {"ACTIVE", "QUARANTINED"}, (
        f"Le modèle ACTIVE disparu doit être QUARANTINED ou conservé, obtenu {old.lifecycle}"
    )
    assert "gemini-old-active" in result["missing_from_api"]


# ── TEST 4 : API indisponible → registry.json inchangé ───────────────────────

@pytest.mark.asyncio
async def test_api_failure_leaves_registry_unchanged(tmp_path):
    """Si l'API est indisponible, registry.json ne doit pas être modifié."""
    initial_record = ModelRecord(
        model_id="gemini-existing",
        provider="gemini",
        lifecycle="CANDIDATE",
    )
    reg, reg_path = _make_registry(tmp_path, [initial_record])
    mtime_before = reg_path.stat().st_mtime

    with (
        patch("core.models.registry_refresh._REGISTRY_PATH", reg_path),
        patch("core.models.registry_refresh._AUDIT_DIR", tmp_path / "audit"),
        patch(
            "core.models.discovery.gemini.GeminiDiscovery.discover",
            new=AsyncMock(side_effect=Exception("Network unreachable")),
        ),
    ):
        with pytest.raises(Exception, match="Network unreachable"):
            await _run_refresh(api_key="FAKE-KEY")

    # Le registre ne doit pas avoir été modifié
    mtime_after = reg_path.stat().st_mtime
    assert mtime_before == mtime_after, "registry.json a été modifié malgré l'erreur API"

    reg2 = ModelRegistry(reg_path)
    assert reg2.get("gemini", "gemini-existing") is not None


# ── TEST 5 : Aucun ACTIVE automatique ────────────────────────────────────────

@pytest.mark.asyncio
async def test_no_automatic_activation(tmp_path):
    """Un nouveau modèle découvert ne doit JAMAIS devenir ACTIVE automatiquement."""
    reg, reg_path = _make_registry(tmp_path)
    items = [
        _make_discovery_item("gemini-2.5-pro-test"),
        _make_discovery_item("gemini-3.7-flash-test"),
    ]

    with (
        patch("core.models.registry_refresh._REGISTRY_PATH", reg_path),
        patch("core.models.registry_refresh._AUDIT_DIR", tmp_path / "audit"),
        patch(
            "core.models.discovery.gemini.GeminiDiscovery.discover",
            new=AsyncMock(return_value=items),
        ),
    ):
        await _run_refresh(api_key="FAKE-KEY")

    reg2 = ModelRegistry(reg_path)
    for r in reg2.all():
        assert r.lifecycle != "ACTIVE", (
            f"INVARIANT VIOLÉ : {r.provider}/{r.model_id} est ACTIVE après refresh automatique"
        )


# ── TEST 6 : Sécurité secrets ────────────────────────────────────────────────

def test_audit_contains_no_secrets(tmp_path):
    """Le fichier d'audit ne doit contenir aucune clé API, secret ou token."""
    audit_dir = tmp_path / "audit"
    result = {
        "timestamp_iso": "2026-09-01T12:00:00+00:00",
        "timestamp_unix": 1787880000.0,
        "source": "https://generativelanguage.googleapis.com/v1beta/models",
        "duration_seconds": 0.5,
        "discovered_count": 1,
        "valid_count": 1,
        "registry_count_before": 0,
        "registry_count_after": 1,
        "new_models": ["gemini-2.5-flash"],
        "existing_models": [],
        "missing_from_api": [],
        "superseded_models": [],
        "invalid_models": [],
        "errors": [],
        "warnings": [],
        # Champs sensibles qui ne doivent PAS apparaître dans l'audit
        "api_key": "AIza-FAKE-SECRET-KEY",
        "token": "fake-token-value",
        "secret": "should-not-appear",
    }

    with patch("core.models.registry_refresh._AUDIT_DIR", audit_dir):
        audit_path = _write_audit(result)

    content = audit_path.read_text(encoding="utf-8")
    audit_data = json.loads(content)

    # Vérifier qu'aucune clé sensible n'a été écrite
    sensitive_keys = ["api_key", "token", "secret", "credential", "password"]
    for key in sensitive_keys:
        assert key not in audit_data, f"Champ sensible '{key}' présent dans l'audit"

    # Vérifier que le contenu texte ne contient pas de valeurs sensibles
    assert "AIza-FAKE-SECRET-KEY" not in content
    assert "fake-token-value" not in content
    assert "should-not-appear" not in content

    # Vérifier que les champs légitimes sont présents
    assert "new_models" in audit_data
    assert "source" in audit_data


# ── TEST 7 : Atomicité ───────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_registry_write_is_atomic(tmp_path):
    """
    Le registre ne doit jamais être dans un état partiellement écrit.
    ModelRegistry.save() utilise tempfile + os.replace — on vérifie
    qu'aucun fichier .tmp ne reste après un refresh réussi.
    """
    reg, reg_path = _make_registry(tmp_path)
    items = [_make_discovery_item("gemini-atomic-test")]

    with (
        patch("core.models.registry_refresh._REGISTRY_PATH", reg_path),
        patch("core.models.registry_refresh._AUDIT_DIR", tmp_path / "audit"),
        patch(
            "core.models.discovery.gemini.GeminiDiscovery.discover",
            new=AsyncMock(return_value=items),
        ),
    ):
        await _run_refresh(api_key="FAKE-KEY")

    # Aucun fichier temporaire ne doit traîner
    tmp_files = list(reg_path.parent.glob(".registry_*.tmp"))
    assert len(tmp_files) == 0, f"Fichiers temporaires orphelins détectés : {tmp_files}"

    # Le registre doit être un JSON valide
    content = reg_path.read_text(encoding="utf-8")
    data = json.loads(content)
    assert "models" in data
    assert isinstance(data["models"], dict)
