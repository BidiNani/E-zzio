"""Test cible : cognitive_gateway.ask() L156 (run_until_complete).

Cible le chemin ou `loop.is_running() == False` -> L156.
Appel simple de ask() sans aucune loop active.
"""
from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock

import pytest


class TestCognitiveGatewayAskWithoutRunningLoop:
    """L156 : appeler ask() hors loop -> loop.run_until_complete."""

    def test_ask_sync_no_running_loop(self, tmp_path):
        """ask() synchrone sans loop active -> L156 executee."""
        from core.cognition.cognitive_gateway import CognitiveGateway

        db_path = str(tmp_path / "test.db")

        # On force une nouvelle loop (pas la loop pytest-asyncio)
        asyncio.set_event_loop(asyncio.new_event_loop())

        gw = CognitiveGateway(db_path=db_path)

        # Mock l'adaptateur pour eviter un vrai appel LLM
        mock_adapter = MagicMock()
        mock_adapter.chat_completion = MagicMock(return_value="reponse mockee")
        gw._adapter = mock_adapter

        # Mock la memoire pour eviter un vrai acces SQLite
        gw.memory_gateway = MagicMock()
        gw.memory_gateway.init = AsyncMock()
        gw.memory_gateway.search_memory = AsyncMock(
            return_value={"chat_history": []}
        )
        gw.memory_gateway.get_session_history = AsyncMock(return_value=[])
        gw.memory_gateway.record_message = AsyncMock()

        # Appel synchrone : pas de loop active -> L156
        result = gw.ask("test simple", session_id="s1")

        assert result["status"] in ("ACCEPTED", "FAILED")
        assert result["session_id"] == "s1"

        # Nettoyage : fermer la loop
        try:
            loop = asyncio.get_event_loop()
            if not loop.is_closed():
                loop.close()
        except Exception:
            pass
