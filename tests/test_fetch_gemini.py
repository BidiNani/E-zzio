"""Test verrou pour la classification free/paid des modèles Gemini."""
import sys
from unittest.mock import AsyncMock, patch

sys.path.insert(0, r"G:\AI\E-zzio")

import pytest

import routers.models as m

FAKE = {"models": [
    # --- FREE attendus ---
    {"name": "models/gemini-2.5-flash",           "displayName": "2.5 Flash",   "inputTokenLimit": 1000000},
    {"name": "models/gemini-2.5-pro",             "displayName": "2.5 Pro",     "inputTokenLimit": 2000000},
    {"name": "models/gemini-2.5-flash-preview-tts","displayName": "2.5 TTS",    "inputTokenLimit": 1000000},
    {"name": "models/gemini-3-flash-preview",     "displayName": "3 Flash prev","inputTokenLimit": 1000000},
    {"name": "models/gemini-3.5-flash",           "displayName": "3.5 Flash",   "inputTokenLimit": 1000000},
    {"name": "models/gemini-3.8-flash",           "displayName": "3.8 Flash",   "inputTokenLimit": 1000000},
    {"name": "models/gemini-3.1-pro-preview",     "displayName": "3.1 Pro prev","inputTokenLimit": 1000000},
    {"name": "models/gemini-flash-latest",        "displayName": "Flash latest","inputTokenLimit": 1000000},
    {"name": "models/gemini-pro-latest",          "displayName": "Pro latest",  "inputTokenLimit": 1000000},
    # --- PAID attendus ---
    {"name": "models/gemma-4-26b-a4b-it",         "displayName": "Gemma 4",     "inputTokenLimit": 8192},
    {"name": "models/gemini-3-pro-image-preview", "displayName": "3 Pro image", "inputTokenLimit": 8192},
    {"name": "models/gemini-3.1-flash-tts-preview","displayName": "TTS",        "inputTokenLimit": 8192},
    {"name": "models/gemini-embedding-001",       "displayName": "Embed",       "inputTokenLimit": 2048},
    {"name": "models/veo-3.1-generate-preview",   "displayName": "Veo",         "inputTokenLimit": 0},
    {"name": "models/lyria-3-pro-preview",        "displayName": "Lyria",       "inputTokenLimit": 0},
]}


class _FakeResp:
    def raise_for_status(self): pass
    def json(self): return FAKE


@pytest.mark.asyncio
async def test_free_vs_paid_strict():
    with patch("routers.models.httpx.AsyncClient") as cls:
        inst = cls.return_value.__aenter__.return_value
        inst.get = AsyncMock(return_value=_FakeResp())
        out = await m._fetch_gemini("fake-key")

    by_id = {x["id"]: x for x in out}

    FREE = [
        "gemini-2.5-flash", "gemini-2.5-pro",
        "gemini-3-flash-preview", "gemini-3.5-flash", "gemini-3.8-flash",
        "gemini-3.1-pro-preview", "gemini-flash-latest", "gemini-pro-latest",
    ]
    PAID = [
        "gemma-4-26b-a4b-it",
        "gemini-3-pro-image-preview",
        "gemini-embedding-001",
        "veo-3.1-generate-preview",
        "lyria-3-pro-preview",
    ]

    for mid in FREE:
        assert by_id[mid]["free"] is True, f"{mid} devrait être free"
        assert by_id[mid]["pricing"]["prompt"] == "0", mid
        assert by_id[mid]["pricing"]["completion"] == "0", mid

    for mid in PAID:
        assert by_id[mid]["free"] is False, f"{mid} devrait être paid"
        assert by_id[mid]["pricing"]["prompt"] == "paid", mid


@pytest.mark.asyncio
async def test_tts_variants_paid():
    """Les variantes -tts-* de 3.x ne doivent PAS être free (ce sont des API payantes)."""
    with patch("routers.models.httpx.AsyncClient") as cls:
        inst = cls.return_value.__aenter__.return_value
        inst.get = AsyncMock(return_value=_FakeResp())
        out = await m._fetch_gemini("fake-key")
    by_id = {x["id"]: x for x in out}
    # gemini-3.1-flash-tts-preview : contient "flash" mais suivi de "-tts", PAS "-lite"
    assert by_id["gemini-3.1-flash-tts-preview"]["free"] is False
