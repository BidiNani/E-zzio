"""tests/test_fallback_notice_truth.py

Test de régression d'observabilité : vérifie que fallback_notice["actual_provider"]
reflète fidèlement le provider réel du fallback (ex: ollama, groq).
"""
from unittest.mock import AsyncMock

import pytest

from core.ezzio_master import EzzioMaster
from core.providers.base_provider import ProviderResponse
from core.providers.registry import ProviderFactory


class InMemoryGateway:
    def __init__(self):
        self.sessions = {}

    async def init(self):
        pass

    async def record_message(self, session_id: str, role: str, content: str, metadata=None):
        if session_id not in self.sessions:
            self.sessions[session_id] = []
        self.sessions[session_id].append({"role": role, "content": content, "metadata": metadata or {}})

    async def get_session_history(self, session_id: str, limit: int = 10):
        return self.sessions.get(session_id, [])[-limit:]


@pytest.mark.asyncio
async def test_fallback_notice_truthful_provider(monkeypatch):
    """Vérifie que fallback_notice["actual_provider"] rapporte le provider réel du fallback."""
    calls = []

    def mock_create(name: str, **kwargs):
        calls.append(name)
        fake_prov = AsyncMock()
        if len(calls) == 1:
            fake_prov.generate = AsyncMock(side_effect=RuntimeError("Primary cloud provider error"))
        else:
            fake_prov.generate = AsyncMock(return_value=ProviderResponse(
                content="local fallback response",
                model="qwen2.5-coder:7b-instruct-q4_K_M",
                provider="ollama"
            ))
        return fake_prov

    monkeypatch.setattr(ProviderFactory, "create", mock_create)
    monkeypatch.setattr(
        "routers.settings.FALLBACK_MAP",
        {"gemini": "qwen2.5-coder:7b-instruct-q4_K_M"}
    )

    master = EzzioMaster()
    master.memory = InMemoryGateway()
    master._memory_initialized = True

    res = await master.execute_intent("Test prompt fallback notice", session_id="sess-notice-truth")

    assert res["ok"] is True
    assert res["used_fallback"] is True
    assert res["fallback_notice"]["actual_model"] == "qwen2.5-coder:7b-instruct-q4_K_M"
    assert res["fallback_notice"]["actual_provider"] == "ollama"
    assert res["provider"] == "ollama"
