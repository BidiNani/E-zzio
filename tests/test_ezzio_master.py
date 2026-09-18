"""Tests unitaires déterministes pour EzzioMaster — Dédoublonnage du contexte et continuité multi-tours."""

import asyncio
from unittest.mock import AsyncMock, MagicMock

import pytest

from core.ezzio_master import EzzioMaster
from core.providers.base_provider import CostClass, ProviderResponse


class FakeProvider:
    """Provider fake déterministe pour capturer l'ensemble des payloads envoyés au LLM."""

    def __init__(self):
        self.calls = []

    async def generate(
        self,
        prompt: str = "",
        system_prompt: str = None,
        model: str = "gemini-3.8-flash",
        temperature: float = 0.2,
        max_tokens: int = 512,
        thinking_level: str = "off",
        **kwargs
    ) -> ProviderResponse:
        self.calls.append({
            "prompt": prompt,
            "system_prompt": system_prompt,
            "model": model,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "thinking_level": thinking_level,
        })
        return ProviderResponse(
            content=f"Fake response for: {prompt[:30]}",
            model=model,
            provider="fake_provider",
            cost_class=CostClass.LOCAL,
        )


class InMemoryGateway:
    """Passerelle mémoire en mémoire simulée pour tests isolés sans SQLite."""

    def __init__(self):
        self.sessions = {}

    async def init(self):
        pass

    async def record_message(self, session_id: str, role: str, content: str, metadata=None):
        if session_id not in self.sessions:
            self.sessions[session_id] = []
        self.sessions[session_id].append({
            "role": role,
            "content": content,
            "metadata": metadata or {}
        })

    async def get_session_history(self, session_id: str, limit: int = 10):
        items = self.sessions.get(session_id, [])
        return items[-limit:]


@pytest.mark.asyncio
async def test_new_session_no_prompt_duplication():
    """Vérifie que pour une nouvelle session, le prompt courant n'apparaît qu'une seule fois (dans prompt, pas dans chat_system)."""
    fake_prov = FakeProvider()
    master = EzzioMaster(provider=fake_prov)
    master.memory = InMemoryGateway()
    master._memory_initialized = True

    user_q = "Quelle est la capitale de la France ?"
    res = await master.execute_intent(
        user_prompt=user_q,
        session_id="new-session-001",
        channel="discord"
    )

    assert res["ok"] is True
    assert len(fake_prov.calls) == 1
    call = fake_prov.calls[0]

    # Verification : prompt utilisateur dans le champ prompt
    assert call["prompt"] == user_q

    # Verification : system_prompt ne contient PAS le prompt courant
    sys_prompt = call["system_prompt"] or ""
    assert user_q not in sys_prompt

    # Nombre total d'occurrences du prompt courant dans les arguments passes au provider = 1
    total_occurrences = (call["prompt"].count(user_q)) + (sys_prompt.count(user_q))
    assert total_occurrences == 1


@pytest.mark.asyncio
async def test_existing_session_history_continuity_without_duplication():
    """Vérifie que pour une session existante :
    1. L'historique précédent est bien présent dans chat_system.
    2. Le prompt courant n'est présent qu'UNE SEULE FOIS (dans prompt, PAS dans chat_system).
    """
    fake_prov = FakeProvider()
    mem = InMemoryGateway()
    # Pré-remplir l'historique d'une conversation précédente
    await mem.record_message("exist-sess-002", "user", "Bonjour E-ZZIO")
    await mem.record_message("exist-sess-002", "assistant", "Bonjour ! En quoi puis-je t'aider ?")

    master = EzzioMaster(provider=fake_prov)
    master.memory = mem
    master._memory_initialized = True

    current_prompt = "Peux-tu analyser la météo de Paris ?"
    res = await master.execute_intent(
        user_prompt=current_prompt,
        session_id="exist-sess-002",
        channel="discord"
    )

    assert res["ok"] is True
    assert len(fake_prov.calls) == 1
    call = fake_prov.calls[0]

    sys_prompt = call["system_prompt"] or ""

    # L'historique précédent DOIT être présent dans le prompt système
    assert "Bonjour E-ZZIO" in sys_prompt
    assert "Bonjour ! En quoi puis-je t'aider ?" in sys_prompt

    # Le prompt courant NE DOIT PAS être présent dans le prompt système
    assert current_prompt not in sys_prompt

    # Le prompt courant DOIT être dans le champ prompt
    assert call["prompt"] == current_prompt

    # Total d'occurrences du prompt courant dans le payload LLM = 1
    total_occurrences = call["prompt"].count(current_prompt) + sys_prompt.count(current_prompt)
    assert total_occurrences == 1


@pytest.mark.asyncio
async def test_multi_turn_consecutive_exchanges():
    """Vérifie la continuité exacte sur 3 tours consécutifs d'une même session."""
    fake_prov = FakeProvider()
    mem = InMemoryGateway()
    master = EzzioMaster(provider=fake_prov)
    master.memory = mem
    master._memory_initialized = True

    tours = [
        "Tour 1 : Initialisation système",
        "Tour 2 : Analyse réseau",
        "Tour 3 : Synthèse finale"
    ]

    for idx, user_msg in enumerate(tours):
        fake_prov.calls.clear()
        res = await master.execute_intent(
            user_prompt=user_msg,
            session_id="multi-turn-003",
            channel="web"
        )
        assert res["ok"] is True
        call = fake_prov.calls[0]
        sys_prompt = call["system_prompt"] or ""

        # Pour chaque tour, le message courant ne doit pas être dans le system_prompt
        assert user_msg not in sys_prompt
        assert call["prompt"] == user_msg
        assert call["prompt"].count(user_msg) + sys_prompt.count(user_msg) == 1

        # Pour les tours > 0, les messages des tours précédents doivent figurer dans system_prompt
        for prev_msg in tours[:idx]:
            assert prev_msg in sys_prompt

    # En mémoire, la session doit contenir 6 messages (3 user + 3 assistant)
    hist = await mem.get_session_history("multi-turn-003", limit=10)
    assert len(hist) == 6
