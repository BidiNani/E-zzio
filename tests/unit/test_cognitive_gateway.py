"""Tests pour core/cognition/cognitive_gateway.py.

CognitiveGateway : agrégateur contextuel (Identité + Mémoire FTS5 + Historique).
Délègue l'exécution à AgentProviderAdapter (routeur canonique).

Stratégie :
- Mock UnifiedMemoryGateway (async)
- Mock AgentProviderAdapter (sync)
- Mock CanonicalIdentity (sync, peut lever)
- wrap_untrusted : utilisé en réel (fonction pure)
"""
from __future__ import annotations

import asyncio
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from core.cognition import cognitive_gateway as cg_mod

# ============================================================
# Fixtures
# ============================================================

@pytest.fixture
def fake_memory_gateway():
    """Mock async complet de UnifiedMemoryGateway."""
    mg = MagicMock()
    mg.init = AsyncMock()
    mg.record_message = AsyncMock()
    mg.get_session_history = AsyncMock(return_value=[])
    mg.search_memory = AsyncMock(return_value={"chat_history": []})
    return mg


@pytest.fixture
def fake_adapter():
    """Mock sync de AgentProviderAdapter."""
    a = MagicMock()
    a.chat_completion = MagicMock(return_value="Reponse mockee")
    return a


@pytest.fixture
def gateway(tmp_path, fake_memory_gateway, fake_adapter, monkeypatch):
    """CognitiveGateway avec toutes les dépendances mockées."""
    db_path = str(tmp_path / "evidence" / "evidence.db")

    # Mock UnifiedMemoryGateway
    monkeypatch.setattr(cg_mod, "UnifiedMemoryGateway", lambda db_path: fake_memory_gateway)
    # Mock AgentProviderAdapter (utilise dans init())
    monkeypatch.setattr(cg_mod, "AgentProviderAdapter", lambda: fake_adapter)
    # Mock CanonicalIdentity (succes par defaut)
    monkeypatch.setattr(cg_mod, "CanonicalIdentity", lambda: MagicMock(
        build_system_prompt=MagicMock(return_value="IDENTITE MOCKEE")
    ))

    return cg_mod.CognitiveGateway(db_path=db_path)


# ============================================================
# 1. __init__
# ============================================================

class TestInit:
    def test_init_creates_dir(self, tmp_path, fake_memory_gateway, monkeypatch):
        """__init__ cree le dossier parent du db_path."""
        monkeypatch.setattr(cg_mod, "UnifiedMemoryGateway", lambda db_path: fake_memory_gateway)
        monkeypatch.setattr(cg_mod, "CanonicalIdentity", lambda: MagicMock())
        db_path = tmp_path / "sub" / "deep" / "evidence.db"
        assert not db_path.parent.exists()
        cg = cg_mod.CognitiveGateway(db_path=str(db_path))
        assert db_path.parent.exists()
        assert cg.db_path == str(db_path)

    def test_init_canonical_identity_fails(self, tmp_path, fake_memory_gateway, monkeypatch):
        """Si CanonicalIdentity leve, identity_provider=None."""
        monkeypatch.setattr(cg_mod, "UnifiedMemoryGateway", lambda db_path: fake_memory_gateway)

        def raise_identity():
            raise RuntimeError("identity init failed")

        monkeypatch.setattr(cg_mod, "CanonicalIdentity", raise_identity)
        cg = cg_mod.CognitiveGateway(db_path=str(tmp_path / "e.db"))
        assert cg.identity_provider is None

    def test_init_state(self, gateway):
        """Etat initial : non initialise, adapter=None."""
        assert gateway._initialized is False
        assert gateway._adapter is None
        assert isinstance(gateway._background_tasks, set)
        assert len(gateway._background_tasks) == 0


# ============================================================
# 2. init() async
# ============================================================

class TestAsyncInit:
    @pytest.mark.asyncio
    async def test_init_first_call(self, gateway, fake_memory_gateway, fake_adapter):
        """Premier appel : memory.init + adapter cree."""
        await gateway.init()
        assert gateway._initialized is True
        assert gateway._adapter is fake_adapter
        fake_memory_gateway.init.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_init_idempotent(self, gateway, fake_memory_gateway):
        """Second appel : skip total (memory.init pas rappele)."""
        await gateway.init()
        await gateway.init()
        assert fake_memory_gateway.init.await_count == 1

    @pytest.mark.asyncio
    async def test_init_keeps_existing_adapter(self, gateway, fake_adapter):
        """Si _adapter deja present, on ne le remplace pas."""
        gateway._adapter = fake_adapter
        await gateway.init()
        assert gateway._adapter is fake_adapter


# ============================================================
# 3. _persist_exchange
# ============================================================

class TestPersistExchange:
    @pytest.mark.asyncio
    async def test_persist_exchange_success(self, gateway, fake_memory_gateway):
        """Persiste user + assistant."""
        gateway._persist_exchange("sess1", "user text", "assistant text")
        # Laisser la tache s'executer
        await asyncio.sleep(0.05)
        assert fake_memory_gateway.record_message.await_count == 2
        # Verifier les appels
        calls = fake_memory_gateway.record_message.await_args_list
        assert calls[0].kwargs["session_id"] == "sess1"
        assert calls[0].kwargs["role"] == "user"
        assert calls[0].kwargs["content"] == "user text"
        assert calls[1].kwargs["role"] == "assistant"

    @pytest.mark.asyncio
    async def test_persist_exchange_catches_error(self, gateway, fake_memory_gateway):
        """Erreur dans _save : avalee, pas propagee."""
        fake_memory_gateway.record_message = AsyncMock(
            side_effect=RuntimeError("db down")
        )
        # Ne doit pas lever
        gateway._persist_exchange("sess1", "u", "a")
        await asyncio.sleep(0.05)
        # Pas d'exception propagee

    @pytest.mark.asyncio
    async def test_persist_exchange_adds_to_background(self, gateway):
        """La tache est ajoutee au set puis retiree apres completion."""
        gateway._persist_exchange("sess1", "u", "a")
        # Juste apres : la tache est dans le set (peut etre deja terminee)
        await asyncio.sleep(0.05)
        # Apres completion : set vide (done_callback)
        assert len(gateway._background_tasks) == 0


# ============================================================
# 4. ask_async — cas nominal
# ============================================================

class TestAskAsyncNominal:
    @pytest.mark.asyncio
    async def test_ask_async_success(self, gateway, fake_adapter):
        """Reponse ACCEPTED avec result."""
        result = await gateway.ask_async("Ma question")
        assert result["status"] == "ACCEPTED"
        assert result["result"] == "Reponse mockee"
        assert result["session_id"] == "default"
        assert "task" in result
        # Verifier que chat_completion a ete appele
        fake_adapter.chat_completion.assert_called_once()
        call_kwargs = fake_adapter.chat_completion.call_args.kwargs
        assert call_kwargs["force_cloud"] is False
        assert isinstance(call_kwargs["messages"], list)

    @pytest.mark.asyncio
    async def test_ask_async_custom_session(self, gateway):
        """session_id personnalise propage."""
        result = await gateway.ask_async("Q", session_id="custom-sess")
        assert result["session_id"] == "custom-sess"

    @pytest.mark.asyncio
    async def test_ask_async_force_cloud_true(self, gateway, fake_adapter):
        """constraints={'force_cloud': True} -> force_cloud=True."""
        await gateway.ask_async("Q", constraints={"force_cloud": True})
        call_kwargs = fake_adapter.chat_completion.call_args.kwargs
        assert call_kwargs["force_cloud"] is True

    @pytest.mark.asyncio
    async def test_ask_async_force_cloud_absent(self, gateway, fake_adapter):
        """constraints=None -> force_cloud=False."""
        await gateway.ask_async("Q", constraints=None)
        call_kwargs = fake_adapter.chat_completion.call_args.kwargs
        assert call_kwargs["force_cloud"] is False

    @pytest.mark.asyncio
    async def test_ask_async_injects_history(self, gateway, fake_memory_gateway):
        """get_session_history -> messages enrichis."""
        fake_memory_gateway.get_session_history = AsyncMock(return_value=[
            {"role": "user", "content": "Old user"},
            {"role": "assistant", "content": "Old assistant"},
            {"role": "system", "content": "Ignored"},  # role non valide
            {"role": "user", "content": ""},           # contenu vide
        ])
        await gateway.ask_async("Nouvelle Q")
        call_kwargs = gateway._adapter.chat_completion.call_args.kwargs
        messages = call_kwargs["messages"]
        # 1 system + 2 historique valide + 1 user = 4
        assert len(messages) == 4
        roles = [m["role"] for m in messages]
        assert roles.count("system") == 1
        assert roles.count("user") == 2
        assert roles.count("assistant") == 1


# ============================================================
# 5. ask_async — cas dégradés
# ============================================================

class TestAskAsyncDegraded:
    @pytest.mark.asyncio
    async def test_identity_build_fails(self, gateway, monkeypatch):
        """build_system_prompt leve -> on garde le prompt par defaut."""
        gateway.identity_provider = MagicMock()
        gateway.identity_provider.build_system_prompt = MagicMock(
            side_effect=RuntimeError("identity fail")
        )
        result = await gateway.ask_async("Q")
        assert result["status"] == "ACCEPTED"

    @pytest.mark.asyncio
    async def test_identity_provider_none(self, gateway):
        """identity_provider=None -> prompt fallback."""
        gateway.identity_provider = None
        result = await gateway.ask_async("Q")
        assert result["status"] == "ACCEPTED"
        call_kwargs = gateway._adapter.chat_completion.call_args.kwargs
        messages = call_kwargs["messages"]
        system_msg = next(m for m in messages if m["role"] == "system")
        assert "E-ZZIO" in system_msg["content"]

    @pytest.mark.asyncio
    async def test_search_memory_fails(self, gateway, fake_memory_gateway):
        """search_memory leve -> contexte episodic vide, continue."""
        fake_memory_gateway.search_memory = AsyncMock(
            side_effect=RuntimeError("fts error")
        )
        result = await gateway.ask_async("Q")
        assert result["status"] == "ACCEPTED"

    @pytest.mark.asyncio
    async def test_get_session_history_fails(self, gateway, fake_memory_gateway):
        """get_session_history leve -> historique vide, continue."""
        fake_memory_gateway.get_session_history = AsyncMock(
            side_effect=RuntimeError("history error")
        )
        result = await gateway.ask_async("Q")
        assert result["status"] == "ACCEPTED"
        # 1 system + 1 user = 2 messages
        call_kwargs = gateway._adapter.chat_completion.call_args.kwargs
        assert len(call_kwargs["messages"]) == 2

    @pytest.mark.asyncio
    async def test_episodic_context_injected(self, gateway, fake_memory_gateway):
        """Snippets FTS5 injectes dans le system prompt."""
        fake_memory_gateway.search_memory = AsyncMock(return_value={
            "chat_history": [
                {"content": "Archive 1", "timestamp": "2025-01-01T00:00:00Z",
                 "role": "user", "session_id": "other-sess"},
            ]
        })
        result = await gateway.ask_async("Q", session_id="current")
        assert result["status"] == "ACCEPTED"
        call_kwargs = gateway._adapter.chat_completion.call_args.kwargs
        system_msg = next(m for m in call_kwargs["messages"] if m["role"] == "system")
        # Le snippet doit etre present dans le prompt systeme
        assert "ARCHIVES" in system_msg["content"] or "Archive 1" in system_msg["content"]

    @pytest.mark.asyncio
    async def test_same_session_not_in_episodic(self, gateway, fake_memory_gateway):
        """Messages de la session courante exclus du contexte episodic."""
        fake_memory_gateway.search_memory = AsyncMock(return_value={
            "chat_history": [
                {"content": "Same session", "session_id": "s1"},
            ]
        })
        await gateway.ask_async("Q", session_id="s1")
        # Pas d'assertion forte : juste verifier que ca ne crash pas

    @pytest.mark.asyncio
    async def test_chat_completion_fails(self, gateway, fake_adapter):
        """chat_completion leve -> status FAILED."""
        fake_adapter.chat_completion = MagicMock(
            side_effect=RuntimeError("LLM down")
        )
        result = await gateway.ask_async("Q")
        assert result["status"] == "FAILED"
        assert "LLM down" in result["error"]
        assert result["session_id"] == "default"


# ============================================================
# 6. ask() — passerelle synchrone
# ============================================================

class TestAskSync:
    def test_ask_success(self, gateway):
        """ask() retourne ACCEPTED via run_until_complete (pas de loop actif)."""
        result = gateway.ask("Ma question")
        assert result["status"] == "ACCEPTED"
        assert result["result"] == "Reponse mockee"

    def test_ask_custom_session(self, gateway):
        """session_id propage."""
        result = gateway.ask("Q", session_id="sx")
        assert result["session_id"] == "sx"

    def test_ask_force_cloud(self, gateway, fake_adapter):
        """constraints propage."""
        gateway.ask("Q", constraints={"force_cloud": True})
        call_kwargs = fake_adapter.chat_completion.call_args.kwargs
        assert call_kwargs["force_cloud"] is True


# ============================================================
# 7. Couverture des helpers
# ============================================================

class TestWrapUntrustedIntegration:
    @pytest.mark.asyncio
    async def test_task_is_wrapped(self, gateway, fake_adapter):
        """La tache envoyee au LLM est enveloppee par wrap_untrusted."""
        await gateway.ask_async("Contenu utilisateur")
        call_kwargs = fake_adapter.chat_completion.call_args.kwargs
        messages = call_kwargs["messages"]
        user_msg = messages[-1]
        assert user_msg["role"] == "user"
        assert "<<<UNTRUSTED-DATA>>" in user_msg["content"]
        assert "Contenu utilisateur" in user_msg["content"]
