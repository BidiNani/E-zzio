"""Test verrou pour la politique de fallback intelligent.

Contrat E-ZzIO :
- Si le provider principal leve une exception -> bascule vers FALLBACK_MAP
- Si le provider principal renvoie vide       -> bascule vers FALLBACK_MAP
- La reponse contient fallback_notice avec requested/actual + message utilisateur
- Si le fallback echoue aussi -> FAIL-CLOSED
- Si le provider principal reussit -> pas de fallback_notice
"""
from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from core.ezzio_master import EzzioMaster
from core.providers.base_provider import CostClass, ProviderResponse
from routers.settings import FALLBACK_MAP


def _make_provider(response):
    """Cree un MagicMock provider qui retourne response ou raise si Exception."""
    p = MagicMock()
    if isinstance(response, Exception):
        p.generate = AsyncMock(side_effect=response)
    else:
        p.generate = AsyncMock(return_value=response)
    return p


def _make_master(provider):
    m = EzzioMaster(provider=provider)
    m._memory_initialized = True
    m.memory = MagicMock()
    m.memory.get_session_history = AsyncMock(return_value=[])
    m.memory.record_message = AsyncMock()
    m.memory.init = AsyncMock()
    return m


@pytest.mark.asyncio
async def test_fallback_on_exception():
    """Provider principal raise -> fallback Gemini repond -> notice present."""
    primary = _make_provider(RuntimeError("groq down"))
    fb_resp = ProviderResponse(
        content="Reponse de secours",
        model="gemini-3.5-flash",
        provider="gemini",
        cost_class=CostClass.FREE_ENDPOINT,
    )
    master = _make_master(primary)

    with patch(
        "core.providers.gemini_provider.GeminiProvider.generate",
        new_callable=AsyncMock,
        return_value=fb_resp,
    ):
        res = await master.execute_intent(
            user_prompt="test",
            session_id="",
            model_target="groq/llama-3.3-70b",
        )

    assert res["ok"] is True
    assert res["response"] == "Reponse de secours"
    assert res["used_fallback"] is True
    notice = res.get("fallback_notice")
    assert notice is not None
    assert notice["fallback_used"] is True
    assert notice["requested_model"] == "groq/llama-3.3-70b"
    assert notice["actual_model"] == FALLBACK_MAP["groq"]
    assert "reessayer" in notice["message"] or "Continuer" in notice["message"]


@pytest.mark.asyncio
async def test_fallback_on_empty_response():
    """Provider principal renvoie vide -> fallback Gemini repond -> notice present."""
    primary = _make_provider(ProviderResponse(
        content="",
        model="groq/llama-3.3-70b",
        provider="groq",
        cost_class=CostClass.FREE_ENDPOINT,
    ))
    fb_resp = ProviderResponse(
        content="Reponse de secours",
        model="gemini-3.5-flash",
        provider="gemini",
        cost_class=CostClass.FREE_ENDPOINT,
    )
    master = _make_master(primary)

    with patch(
        "core.providers.gemini_provider.GeminiProvider.generate",
        new_callable=AsyncMock,
        return_value=fb_resp,
    ):
        res = await master.execute_intent(
            user_prompt="test",
            session_id="",
            model_target="groq/llama-3.3-70b",
        )

    assert res["ok"] is True
    assert res["used_fallback"] is True
    assert res["fallback_notice"]["reason"] == "empty_response"


@pytest.mark.asyncio
async def test_fail_closed_when_fallback_also_fails():
    """Provider principal ET fallback echouent -> reponse FAIL-CLOSED.

    Note : on force _detect_provider_from_model a "gemini" pour que le code
    utilise master.provider (mocke) au lieu d'instancier un vrai GroqProvider.
    Le contrat E-ZzIO est de retourner {ok: False} avec un message [FAIL-CLOSED]
    plutot que de propager une exception au client HTTP.
    """
    primary = _make_provider(RuntimeError("primary down"))
    master = _make_master(primary)

    with patch.object(master, "_try_fallback", return_value=(None, None)):
        with patch(
            "core.providers.gemini_provider.GeminiProvider.generate",
            new_callable=AsyncMock,
            side_effect=RuntimeError("gemini down too"),
        ):
            res = await master.execute_intent(
                user_prompt="test",
                session_id="",
                model_target="gemini-3.5-flash",
            )

    assert res["ok"] is False
    assert "FAIL-CLOSED" in str(res.get("response", ""))


@pytest.mark.asyncio
async def test_no_fallback_when_primary_succeeds():
    """Provider principal OK -> pas de fallback_notice.

    Note : on force _detect_provider_from_model a "gemini" pour que le code
    utilise master.provider (mocke) au lieu d'instancier un vrai GroqProvider.
    """
    primary = _make_provider(ProviderResponse(
        content="Reponse normale",
        model="gemini-3.5-flash",
        provider="gemini",
        cost_class=CostClass.FREE_ENDPOINT,
    ))
    master = _make_master(primary)

    with patch.object(master, "_try_fallback", return_value=(None, None)):
        res = await master.execute_intent(
            user_prompt="test",
            session_id="",
            model_target="gemini-3.5-flash",
        )

    assert res["ok"] is True
    assert res["used_fallback"] is False
    assert res.get("fallback_notice") is None
