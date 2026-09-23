"""Tests Paquet 4 quick wins : 6 fichiers a 100%.

- core/coding/policy.py : task_description vide + whitelist None
- core/ezzio_identity.py : 3 fonctions
- core/autonomy.py : check_port + check_ollama
- core/agents/schemas.py : AgentContribution + ADRRecord
- core/providers/jina_provider.py : search + init
- core/integrations/discord/routing_rules.py : should_respond + channel_category_id
"""
from __future__ import annotations

import socket
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# ============================================================
# 1. core/coding/policy.py (fix des 2 misses)
# ============================================================

class TestCodingPolicyRemainingBranches:
    def _make_request(self, task="test", mode=None, files=None):
        from core.coding.protocol import CodingRequest, ExecutionMode
        return CodingRequest(
            task_description=task,
            mode=mode or ExecutionMode.DRY_RUN,
            files_context=files or [],
        )

    def test_empty_task_description_raises(self, tmp_path):
        """L55 : task_description vide -> CodingPolicyViolationError."""
        from core.coding.policy import CodingPolicy
        from core.coding.protocol import CodingPolicyViolationError, ExecutionMode
        policy = CodingPolicy(root_dir=tmp_path)
        request = self._make_request(task="   ", mode=ExecutionMode.DRY_RUN)
        with pytest.raises(CodingPolicyViolationError) as exc:
            policy.evaluate_request(request)
        assert "vide" in str(exc.value).lower()

    def test_whitelist_none_skips_check(self, tmp_path):
        """L66->73 : whitelist_paths=None -> check whitelist skippe."""
        from core.coding.policy import CodingPolicy
        from core.coding.protocol import ExecutionMode
        policy = CodingPolicy(root_dir=tmp_path, whitelist_paths=None)
        request = self._make_request(
            mode=ExecutionMode.DRY_RUN,
            files=["anything/goes.py", "here/too.py"],
        )
        # Ne doit pas lever (whitelist None -> check ignore)
        policy.evaluate_request(request)


# ============================================================
# 2. core/ezzio_identity.py
# ============================================================

class TestEzzioIdentity:
    def test_identity_payload(self):
        """identity_payload retourne un dict structure."""
        from core import ezzio_identity as ident
        mock_ci = MagicMock()
        mock_ci.get_payload = MagicMock(return_value={"name": "E-ZZIO"})
        with patch.object(ident, "CanonicalIdentity", return_value=mock_ci):
            result = ident.identity_payload()
        assert result["status"] == "canonical_verified"
        assert result["entity"] == "E-ZZIO"
        assert result["authority"] == "CanonicalIdentity"
        assert result["payload"] == {"name": "E-ZZIO"}

    def test_manifest_payload(self):
        """manifest_payload inclut identity + integrity."""
        from core import ezzio_identity as ident
        with patch.object(ident, "identity_payload", return_value={"x": 1}):
            result = ident.manifest_payload()
        assert result["identity"] == {"x": 1}
        assert result["integrity"] == "verified"

    def test_routes_payload(self):
        """routes_payload retourne endpoints statiques."""
        from core.ezzio_identity import routes_payload
        result = routes_payload()
        assert result["canonical_endpoint"] == "/master/chat"
        assert result["identity_endpoint"] == "/identity"

    def test_routes_payload_with_app_arg(self):
        """routes_payload accepte un arg app sans erreur."""
        from core.ezzio_identity import routes_payload
        result = routes_payload(app="dummy")
        assert "canonical_endpoint" in result


# ============================================================
# 3. core/autonomy.py
# ============================================================

class TestAutonomy:
    def test_check_port_open(self):
        """check_port retourne True si connect_ex retourne 0."""
        from core import autonomy
        mock_socket = MagicMock()
        mock_socket.connect_ex = MagicMock(return_value=0)
        mock_socket.settimeout = MagicMock()
        mock_socket.close = MagicMock()
        with patch.object(autonomy.socket, "socket", return_value=mock_socket):
            result = autonomy.check_port("127.0.0.1", 11434)
        assert result is True
        mock_socket.close.assert_called_once()

    def test_check_port_closed(self):
        """check_port retourne False si connect_ex retourne != 0."""
        from core import autonomy
        mock_socket = MagicMock()
        mock_socket.connect_ex = MagicMock(return_value=111)  # ECONNREFUSED
        mock_socket.settimeout = MagicMock()
        mock_socket.close = MagicMock()
        with patch.object(autonomy.socket, "socket", return_value=mock_socket):
            result = autonomy.check_port()
        assert result is False

    def test_check_port_exception(self):
        """check_port retourne False si exception."""
        from core import autonomy
        mock_socket = MagicMock()
        mock_socket.connect_ex = MagicMock(side_effect=OSError("fail"))
        mock_socket.settimeout = MagicMock()
        mock_socket.close = MagicMock()
        with patch.object(autonomy.socket, "socket", return_value=mock_socket):
            result = autonomy.check_port()
        assert result is False
        # close doit etre appele meme en cas d'exception (finally)
        mock_socket.close.assert_called_once()

    def test_check_ollama_available(self):
        """check_ollama True si subprocess returncode == 0."""
        from core import autonomy
        mock_result = MagicMock()
        mock_result.returncode = 0
        with patch.object(autonomy.subprocess, "run", return_value=mock_result) as mock_run:
            result = autonomy.check_ollama()
        assert result is True
        mock_run.assert_called_once()

    def test_check_ollama_unavailable(self):
        """check_ollama False si returncode != 0."""
        from core import autonomy
        mock_result = MagicMock()
        mock_result.returncode = 127
        with patch.object(autonomy.subprocess, "run", return_value=mock_result):
            result = autonomy.check_ollama()
        assert result is False

    def test_check_ollama_exception(self):
        """check_ollama False si exception."""
        from core import autonomy
        with patch.object(autonomy.subprocess, "run", side_effect=FileNotFoundError("no ollama")):
            result = autonomy.check_ollama()
        assert result is False


# ============================================================
# 4. core/agents/schemas.py
# ============================================================

class TestAgentContributionSchema:
    def test_valid_contribution(self):
        from core.agents.schemas import AgentContribution
        c = AgentContribution(
            agent_id="a1",
            phase="PROPOSAL",
            confidence=0.8,
            summary="Short summary",
        )
        assert c.agent_id == "a1"
        assert c.phase == "PROPOSAL"
        assert c.unified_diff is None
        assert c.identified_risks == []
        assert c.blockers == []

    def test_confidence_out_of_range_raises(self):
        from pydantic import ValidationError

        from core.agents.schemas import AgentContribution
        with pytest.raises(ValidationError):
            AgentContribution(
                agent_id="a1", phase="PROPOSAL",
                confidence=1.5,  # > 1.0
                summary="x",
            )
        with pytest.raises(ValidationError):
            AgentContribution(
                agent_id="a1", phase="PROPOSAL",
                confidence=-0.1,  # < 0
                summary="x",
            )

    def test_phase_invalid_literal_raises(self):
        from pydantic import ValidationError

        from core.agents.schemas import AgentContribution
        with pytest.raises(ValidationError):
            AgentContribution(
                agent_id="a1", phase="INVALID",  # pas dans Literal
                confidence=0.5, summary="x",
            )

    def test_summary_too_long_raises(self):
        from pydantic import ValidationError

        from core.agents.schemas import AgentContribution
        with pytest.raises(ValidationError):
            AgentContribution(
                agent_id="a1", phase="PROPOSAL", confidence=0.5,
                summary="x" * 201,  # > max_length=200
            )

    def test_extra_field_forbidden(self):
        from pydantic import ValidationError

        from core.agents.schemas import AgentContribution
        with pytest.raises(ValidationError):
            AgentContribution(
                agent_id="a1", phase="PROPOSAL", confidence=0.5,
                summary="x",
                extra_field="not allowed",  # extra=forbid
            )


class TestADRRecordSchema:
    def test_valid_adr(self):
        from core.agents.schemas import ADRRecord
        adr = ADRRecord(
            adr_id="ADR-001",
            title="Test decision",
            decision="Do this",
            rationale="Because",
        )
        assert adr.adr_id == "ADR-001"
        assert adr.status == "PROPOSED"  # defaut
        assert adr.decided_by == "ezzio-master"
        assert adr.rejected_alternatives == []
        assert adr.decided_at != ""  # auto-genere

    def test_status_literal_invalid(self):
        from pydantic import ValidationError

        from core.agents.schemas import ADRRecord
        with pytest.raises(ValidationError):
            ADRRecord(
                adr_id="x", title="t", decision="d", rationale="r",
                status="INVALID",  # pas dans Literal
            )

    def test_title_too_long(self):
        from pydantic import ValidationError

        from core.agents.schemas import ADRRecord
        with pytest.raises(ValidationError):
            ADRRecord(
                adr_id="x", title="x" * 121,  # > 120
                decision="d", rationale="r",
            )

    def test_extra_field_forbidden(self):
        from pydantic import ValidationError

        from core.agents.schemas import ADRRecord
        with pytest.raises(ValidationError):
            ADRRecord(
                adr_id="x", title="t", decision="d", rationale="r",
                unknown_field="nope",
            )


# ============================================================
# 5. core/providers/jina_provider.py
# ============================================================

class TestJinaProvider:
    def test_provider_init_no_key(self):
        """__init__ sans api_key + sans env -> api_key None."""
        from core.providers import jina_provider as jp
        with patch.object(jp, "load_secrets", return_value=True):
            with patch.dict("os.environ", {}, clear=False):
                # S'assurer que JINA_API_KEY n'est pas dans l'env
                import os
                os.environ.pop("JINA_API_KEY", None)
                p = jp.JinaProvider()
        assert p.base_url == "https://s.jina.ai"

    def test_provider_init_with_explicit_key(self):
        from core.providers import jina_provider as jp
        with patch.object(jp, "load_secrets", return_value=True):
            p = jp.JinaProvider(api_key="test_key_123")
        assert p.api_key == "test_key_123"

    @pytest.mark.asyncio
    async def test_search_without_key_no_auth_header(self):
        """Sans api_key, pas d'Authorization header."""
        from core.providers import jina_provider as jp
        with patch.object(jp, "load_secrets", return_value=True):
            p = jp.JinaProvider(api_key=None)
        p.api_key = None  # force

        mock_response = MagicMock()
        mock_response.json = MagicMock(return_value={"data": [{"x": 1}, {"x": 2}]})
        mock_response.raise_for_status = MagicMock()
        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=mock_response)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        with patch.object(jp.httpx, "AsyncClient", return_value=mock_client):
            result = await p.search("test query")

        assert result["provider"] == "jina"
        assert result["data"]["total"] == 2
        # Verifier headers
        call_kwargs = mock_client.get.call_args.kwargs
        assert "Authorization" not in call_kwargs["headers"]

    @pytest.mark.asyncio
    async def test_search_with_key_has_auth_header(self):
        """Avec api_key, Authorization header present."""
        from core.providers import jina_provider as jp
        with patch.object(jp, "load_secrets", return_value=True):
            p = jp.JinaProvider(api_key="my_key")

        mock_response = MagicMock()
        mock_response.json = MagicMock(return_value={"data": []})
        mock_response.raise_for_status = MagicMock()
        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=mock_response)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        with patch.object(jp.httpx, "AsyncClient", return_value=mock_client):
            result = await p.search("query")

        call_kwargs = mock_client.get.call_args.kwargs
        assert call_kwargs["headers"]["Authorization"] == "Bearer my_key"
        assert result["data"]["total"] == 0


# ============================================================
# 6. core/integrations/discord/routing_rules.py
# ============================================================

class TestChannelCategoryId:
    def test_category_id_direct(self):
        from core.integrations.discord.routing_rules import channel_category_id
        channel = MagicMock()
        channel.category_id = 42
        assert channel_category_id(channel) == 42

    def test_category_id_via_parent(self):
        from core.integrations.discord.routing_rules import channel_category_id
        channel = MagicMock()
        channel.category_id = None
        channel.parent = MagicMock()
        channel.parent.category_id = 99
        assert channel_category_id(channel) == 99

    def test_category_id_none(self):
        from core.integrations.discord.routing_rules import channel_category_id
        channel = MagicMock()
        channel.category_id = None
        channel.parent = None
        assert channel_category_id(channel) is None


class TestShouldRespond:
    def test_private_channel_with_content(self):
        from core.integrations.discord.routing_rules import should_respond
        result = should_respond(
            is_private=True, category_id=None, mentioned=False,
            content="Hello",
        )
        assert result == (True, "Hello")

    def test_private_channel_empty(self):
        from core.integrations.discord.routing_rules import should_respond
        result = should_respond(
            is_private=True, category_id=None, mentioned=False,
            content="   ",
        )
        assert result == (False, "")

    def test_bidinani_bus_category(self):
        from core.integrations.discord.routing_rules import (
            BIDINANI_BUS_CATEGORY_ID,
            should_respond,
        )
        result = should_respond(
            is_private=False, category_id=BIDINANI_BUS_CATEGORY_ID,
            mentioned=False, content="Hello",
        )
        assert result == (True, "Hello")

    def test_bang_e_prefix(self):
        from core.integrations.discord.routing_rules import should_respond
        result = should_respond(
            is_private=False, category_id=123, mentioned=False,
            content="!e ask me something",
        )
        assert result == (True, "ask me something")

    def test_bang_ezzio_prefix(self):
        from core.integrations.discord.routing_rules import should_respond
        result = should_respond(
            is_private=False, category_id=123, mentioned=False,
            content="!ezzio help please",
        )
        assert result == (True, "help please")

    def test_mentioned_strips_bot_id(self):
        from core.integrations.discord.routing_rules import should_respond
        result = should_respond(
            is_private=False, category_id=123, mentioned=True,
            content="<@12345> hello there",
            bot_id=12345,
        )
        assert result == (True, "hello there")

    def test_mentioned_with_alt_syntax(self):
        from core.integrations.discord.routing_rules import should_respond
        result = should_respond(
            is_private=False, category_id=123, mentioned=True,
            content="<@!67890> hello",
            bot_id=67890,
        )
        assert result == (True, "hello")

    def test_mentioned_no_bot_id(self):
        from core.integrations.discord.routing_rules import should_respond
        result = should_respond(
            is_private=False, category_id=123, mentioned=True,
            content="<@999> hi",
            bot_id=None,
        )
        # Sans bot_id, on ne retire rien
        assert result == (True, "<@999> hi")

    def test_not_mentioned_not_private_not_bus(self):
        from core.integrations.discord.routing_rules import should_respond
        result = should_respond(
            is_private=False, category_id=123, mentioned=False,
            content="just chatting",
        )
        assert result == (False, "")

    def test_content_none(self):
        from core.integrations.discord.routing_rules import should_respond
        result = should_respond(
            is_private=False, category_id=123, mentioned=False,
            content=None,
        )
        assert result == (False, "")
