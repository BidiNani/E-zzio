"""
E-ZZIO Test Suite — Contrat Unique & Paramétré du Pool Gemini (GeminiPool & GeminiProvider).
Regroupe l'ensemble des scénarios de résilience, classement par capacité, politiques de thinking et rotation multi-projets.
"""
from unittest.mock import patch

import httpx
import pytest

from core.models.gemini_pool import (
    GeminiKeySlot,
    GeminiPoolManager,
    GeminiProjectSlot,
)
from core.providers.gemini_provider import GeminiProvider
from core.routing.model_registry import canonical_model_registry


# -----------------------------------------------------------------------------
# 1. Contrat : Registre Officiel des Modèles (via CanonicalModelRegistry)
# -----------------------------------------------------------------------------
@pytest.mark.parametrize("expected_model", [
    "gemini-3.8-flash",
    "gemini-3.7-flash",
    "gemini-3.6-flash",
    "gemini-3.5-flash",
    "gemini-3.5-flash-lite",
])
def test_contract_registered_models(expected_model):
    registered_models = [m.name for m in canonical_model_registry.list_models() if m.source.name == "GEMINI"]
    assert expected_model in registered_models
    assert "gemini-3.7-flash-lite" not in registered_models
    assert "gemini-2.0-flash" not in registered_models


# -----------------------------------------------------------------------------
# 2. Contrat : Classement par Profil de Capacité
# -----------------------------------------------------------------------------
@pytest.mark.parametrize("capability,expected_top_model", [
    ("general", "gemini-3.8-flash"),
    ("coding", "gemini-3.7-flash"),
    ("reasoning", "gemini-3.8-flash"),
    ("architecture", "gemini-3.8-flash"),
])
def test_contract_capability_ranking(capability, expected_top_model):
    pool = GeminiPoolManager()
    candidates = pool.get_candidate_models(capability)
    assert candidates[0] == expected_top_model


# -----------------------------------------------------------------------------
# 3. Contrat : Politiques de Thinking (off / low / medium / high)
# -----------------------------------------------------------------------------
@pytest.mark.parametrize("model,thinking_level,expected_config", [
    # Gemini 2.5 -> thinkingBudget (int, 0 = off)
    ("gemini-3.5-flash-lite", "off",    None),    ("gemini-3.5-flash-lite", "low",    {"thinkingLevel": "low"}),    ("gemini-3.5-flash-lite", "medium", None),    ("gemini-3.5-flash-lite", "high",   {"thinkingLevel": "high"}),    # Gemini 3.x -> thinkingLevel (str, low/high uniquement)
    ("gemini-3.7-flash", "low",    {"thinkingLevel": "low"}),
    ("gemini-3.7-flash", "high",   {"thinkingLevel": "high"}),
    # Gemini 3.x -> off/medium : thinkingConfig entierement omis
    ("gemini-3.7-flash", "off",    None),
    ("gemini-3.7-flash", "medium", None),
])
def test_contract_thinking_policy(model, thinking_level, expected_config):
    provider = GeminiProvider(api_key="mock_key", model=model)
    payload = provider._build_generation_payload("Calcul complexe", thinking_level=thinking_level)
    gc = payload["generationConfig"]
    if expected_config is None:
        assert "thinkingConfig" not in gc, f"{model}/{thinking_level} : thinkingConfig ne doit pas etre present"
    else:
        assert gc.get("thinkingConfig") == expected_config, f"{model}/{thinking_level} : attendu {expected_config}, obtenu {gc.get('thinkingConfig')}"


# -----------------------------------------------------------------------------
# 4. Contrat : Résilience & Récupération sous Erreurs HTTP (Paramétré)
# -----------------------------------------------------------------------------
@pytest.mark.parametrize("error_status,headers,expected_state", [
    (429, {"retry-after": "30"}, "RATE_LIMITED"),
    (401, {}, "INVALID"),
    (403, {}, "INVALID"),
    (404, {}, "UNAVAILABLE"),
])
@pytest.mark.asyncio
async def test_contract_error_handling(error_status, headers, expected_state):
    pool = GeminiPoolManager()
    proj = GeminiProjectSlot(
        project_id="proj_contract",
        keys=[GeminiKeySlot(key="k1"), GeminiKeySlot(key="k2")]
    )
    pool.projects = [proj]

    model = "gemini-3.7-flash"
    pool.handle_error(project=proj, key="k1", model=model, status_code=error_status, headers=headers)

    if error_status == 429:
        assert not proj.is_available()
        assert proj.quota_exhaustions == 1
    elif error_status in (401, 403):
        assert proj.keys[0].is_valid is False
        assert proj.keys[1].is_valid is True
        key_idx, active_key = proj.get_active_key()
        assert active_key == "k2"
    elif error_status == 404:
        candidates = pool.get_candidate_models("coding")
        assert model not in candidates


# -----------------------------------------------------------------------------
# 5. Contrat : Rotation Multi-Projets Immédiate (Sans délai bloquant)
# -----------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_contract_dynamic_multiproject_rotation():
    pool = GeminiPoolManager()
    pool.projects = [
        GeminiProjectSlot(project_id="proj_A", keys=[GeminiKeySlot(key="key_A1")]),
        GeminiProjectSlot(project_id="proj_B", keys=[GeminiKeySlot(key="key_B1")])
    ]

    async def mock_post(url, **kwargs):
        key = kwargs.get("params", {}).get("key")
        if key == "key_A1":
            return httpx.Response(429, headers={"retry-after": "60"}, json={"error": "Rate limited"})
        elif key == "key_B1":
            return httpx.Response(200, json={"candidates": [{"content": {"parts": [{"text": "Succès Projet B"}]}}]})
        return httpx.Response(500)

    import core.providers.gemini_provider as gp_module
    orig_pool = gp_module.gemini_pool
    gp_module.gemini_pool = pool

    try:
        with patch.object(httpx.AsyncClient, "post", side_effect=mock_post):
            provider = GeminiProvider(api_key=None, model="gemini-3.7-flash")
            res = await provider.search("Prompt", capability="coding")

            assert res["data"]["text"] == "Succès Projet B"
            assert res["data"]["telemetry"]["project_id"] == "proj_B"
            assert res["data"]["telemetry"]["key_index"] == 0
    finally:
        gp_module.gemini_pool = orig_pool
