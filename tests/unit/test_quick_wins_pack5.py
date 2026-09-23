"""Tests Pack 5+6 : 8 fichiers a 100%.

- core/agents/swarm.py : alias de compatibilite
- core/providers/google_gmail_provider.py : stub + except vault
- core/providers/searxng_provider.py : search + exception
- core/models/discovery/litellm.py : discover (async + httpx)
- core/models/qualification/policies.py : policy helpers
- core/models/telemetry.py : SafeTelemetry (sanitize + emit)
- core/actions.py : ActionToolbox (sandbox)
- core/observability/tracer.py : ExecutionTracer (async sqlite)
"""
from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# ============================================================
# 1. core/agents/swarm.py
# ============================================================

class TestSwarmAlias:
    def test_exports_all_classes(self):
        """Le package swarm expose au moins les 10 noms canoniques."""
        from core.agents import swarm as swarm_mod
        # Noms minimaux obligatoires
        required = {
            "SwarmEngine", "swarm_engine", "AgentSwarm", "SwarmMessage",
            "SwarmConflict", "SwarmProposal", "MessageType", "SwarmMode",
            "SwarmState", "SwarmLimitError",
        }
        # Le package peut en exposer d'autres (SentinelAgent, WatcherAgent, etc.)
        assert required.issubset(set(swarm_mod.__all__))

    def test_classes_importable(self):
        from core.agents.swarm import (
            AgentSwarm,
            MessageType,
            SwarmConflict,
            SwarmEngine,
            SwarmLimitError,
            SwarmMessage,
            SwarmMode,
            SwarmProposal,
            SwarmState,
            swarm_engine,
        )
        # Juste verifier que les imports fonctionnent
        assert SwarmEngine is not None
        assert swarm_engine is not None


# ============================================================
# 2. core/providers/google_gmail_provider.py
# ============================================================

class TestGoogleGmailProvider:
    def test_provider_instantiable_with_explicit_key(self):
        from core.providers import google_gmail_provider as gg
        with patch.object(gg, "load_secrets", return_value=True):
            p = gg.GoogleGmailProvider(api_key="test_key_123")
        assert p.api_key == "test_key_123"

    def test_provider_vault_exception_path(self):
        """Si l'import vault leve -> _vault_key=None, fallback."""
        from core.providers import google_gmail_provider as gg

        # Forcer une ImportError sur le vault
        original_import = __builtins__["__import__"]
        def fake_import(name, *args, **kwargs):
            if name == "core.security.unified_vault":
                raise ImportError("simulated")
            return original_import(name, *args, **kwargs)

        with patch.object(gg, "load_secrets", return_value=True):
            with patch("builtins.__import__", side_effect=fake_import):
                p = gg.GoogleGmailProvider(api_key="fallback")
        assert p.api_key == "fallback"

    @pytest.mark.asyncio
    async def test_provider_execute_not_implemented(self):
        from core.providers import google_gmail_provider as gg
        with patch.object(gg, "load_secrets", return_value=True):
            p = gg.GoogleGmailProvider(api_key="test_key")
        with pytest.raises(NotImplementedError):
            await p.execute()


# ============================================================
# 3. core/providers/searxng_provider.py
# ============================================================

class TestSearxngProvider:
    @pytest.mark.asyncio
    async def test_search_success(self):
        from core.providers import searxng_provider as sp
        p = sp.SearxngProvider(base_url="http://test:8080")

        mock_response = MagicMock()
        mock_response.json = MagicMock(return_value={
            "results": [
                {"title": "T1", "url": "http://a", "content": "C1"},
                {"title": "T2", "url": "http://b", "content": "C2"},
            ]
        })
        mock_response.raise_for_status = MagicMock()

        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=mock_response)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        with patch.object(sp.httpx, "AsyncClient", return_value=mock_client):
            result = await p.search("test")

        assert result["provider"] == "searxng"
        assert result["status"] == "success"
        assert len(result["data"]["results"]) == 2
        assert "T1" in result["data"]["text"]

    @pytest.mark.asyncio
    async def test_search_empty_results(self):
        from core.providers import searxng_provider as sp
        p = sp.SearxngProvider()

        mock_response = MagicMock()
        mock_response.json = MagicMock(return_value={"results": []})
        mock_response.raise_for_status = MagicMock()

        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=mock_response)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        with patch.object(sp.httpx, "AsyncClient", return_value=mock_client):
            result = await p.search("nothing")

        assert result["data"]["text"] == "Aucun résultat trouvé via SearXNG."

    @pytest.mark.asyncio
    async def test_search_exception_reraises(self):
        from core.providers import searxng_provider as sp
        p = sp.SearxngProvider()

        mock_client = AsyncMock()
        mock_client.get = AsyncMock(side_effect=RuntimeError("network down"))
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        with patch.object(sp.httpx, "AsyncClient", return_value=mock_client):
            with pytest.raises(RuntimeError, match="network down"):
                await p.search("test")

    def test_alias_class(self):
        from core.providers.searxng_provider import SearXNGProvider, SearxngProvider
        assert issubclass(SearXNGProvider, SearxngProvider)


# ============================================================
# 4. core/models/discovery/litellm.py
# ============================================================

class TestLiteLLMDiscovery:
    @pytest.mark.asyncio
    async def test_discover_success(self):
        from core.models.discovery import litellm as lm
        d = lm.LiteLLMDiscovery()

        mock_response = MagicMock()
        mock_response.json = MagicMock(return_value={
            "data": [
                {"id": "gpt-4"},
                {"id": "claude-reasoning-3"},
                {"id": ""},  # id vide, doit etre skippe
            ]
        })
        mock_response.raise_for_status = MagicMock()

        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=mock_response)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        with patch.object(lm.httpx, "AsyncClient", return_value=mock_client):
            result = await d.discover("api_key_test")

        assert len(result) == 2
        assert result[0]["model_id"] == "gpt-4"
        assert result[1]["model_id"] == "claude-reasoning-3"
        assert result[1]["supports_reasoning"] is True  # "reason" dans le nom
        assert result[0]["supports_reasoning"] is False

    @pytest.mark.asyncio
    async def test_discover_with_api_key_sets_header(self):
        from core.models.discovery import litellm as lm
        d = lm.LiteLLMDiscovery()

        mock_response = MagicMock()
        mock_response.json = MagicMock(return_value={"data": []})
        mock_response.raise_for_status = MagicMock()

        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=mock_response)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        with patch.object(lm.httpx, "AsyncClient", return_value=mock_client):
            await d.discover("my_secret_key")

        call_kwargs = mock_client.get.call_args.kwargs
        assert call_kwargs["headers"]["Authorization"] == "Bearer my_secret_key"

    @pytest.mark.asyncio
    async def test_discover_without_api_key_no_header(self):
        from core.models.discovery import litellm as lm
        d = lm.LiteLLMDiscovery()

        mock_response = MagicMock()
        mock_response.json = MagicMock(return_value={"data": []})
        mock_response.raise_for_status = MagicMock()

        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=mock_response)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        with patch.object(lm.httpx, "AsyncClient", return_value=mock_client):
            await d.discover("")

        call_kwargs = mock_client.get.call_args.kwargs
        assert "Authorization" not in call_kwargs["headers"]

    @pytest.mark.asyncio
    async def test_discover_custom_base_url(self):
        from core.models.discovery import litellm as lm
        d = lm.LiteLLMDiscovery()

        mock_response = MagicMock()
        mock_response.json = MagicMock(return_value={"data": []})
        mock_response.raise_for_status = MagicMock()

        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=mock_response)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        with patch.dict("os.environ", {"EZZIO_LITELLM_BASE_URL": "http://custom:9999/"}):
            with patch.object(lm.httpx, "AsyncClient", return_value=mock_client):
                result = await d.discover("key")

        call_args = mock_client.get.call_args.args
        assert call_args[0] == "http://custom:9999/v1/models"


# ============================================================
# 5. core/models/qualification/policies.py
# ============================================================

class TestQualificationPolicies:
    def test_policy_name(self):
        from core.models.qualification import policies as pol
        assert pol.policy_name() == "FREE_ONLY"

    def test_is_free_only(self):
        from core.models.qualification import policies as pol
        assert pol.is_free_only() is True

    def test_policy_allows_delegates(self):
        from core.models.qualification import policies as pol
        # Un modele explicitement gratuit
        model = {"model_id": "gpt-3.5:free"}
        assert pol.policy_allows(model) is True

    def test_prepare_model_adds_fields(self):
        from core.models.qualification import policies as pol
        result = pol.prepare_model({"model_id": "gpt:free"})
        assert result["qualification_policy"] == "FREE_ONLY"
        assert "qualification_policy_version" in result
        assert "policy_allowed" in result
        assert result["policy_allowed"] is True

    def test_reject_reason_none_for_free(self):
        from core.models.qualification import policies as pol
        result = pol.reject_reason({"model_id": "test:free"})
        assert result is None

    def test_reject_reason_paid(self):
        from core.models.qualification import policies as pol
        result = pol.reject_reason({
            "model_id": "paid-model",
            "pricing": {"prompt": "0.001", "completion": "0.002"},
        })
        assert result == "free_only_reject_paid_model"

    def test_reject_reason_unknown(self):
        """Force le status UNKNOWN pour couvrir la branche L33-35."""
        from core.models.qualification import policies as pol

        # Mocker prepare_model pour forcer free_status=UNKNOWN + policy_allowed=False
        fake_prepared = {
            "policy_allowed": False,
            "free_status": "UNKNOWN",
        }
        with patch.object(pol, "prepare_model", return_value=fake_prepared):
            result = pol.reject_reason({"model_id": "any"})
        assert result == "free_only_reject_unknown_pricing"

    def test_reject_reason_generic_denied(self):
        """Force un free_status bizarre -> return 'qualification_policy_denied'."""
        from core.models.qualification import policies as pol

        fake_prepared = {
            "policy_allowed": False,
            "free_status": "SOMETHING_ELSE",
        }
        with patch.object(pol, "prepare_model", return_value=fake_prepared):
            result = pol.reject_reason({"model_id": "any"})
        assert result == "qualification_policy_denied"


# ============================================================
# 6. core/models/telemetry.py
# ============================================================

class TestSafeTelemetry:
    def test_sanitize_redacts_forbidden_keys(self):
        from core.models.telemetry import SafeTelemetry
        data = {
            "api_key": "secret_123",
            "normal": "visible",
            "authorization": "Bearer xxx",
        }
        result = SafeTelemetry.sanitize(data)
        assert result["api_key"] == "[REDACTED]"
        assert result["authorization"] == "[REDACTED]"
        assert result["normal"] == "visible"

    def test_sanitize_recursive_dict(self):
        from core.models.telemetry import SafeTelemetry
        data = {
            "outer": {
                "api_key": "secret",
                "inner": {"token": "abc", "safe": "ok"},
            }
        }
        result = SafeTelemetry.sanitize(data)
        assert result["outer"]["api_key"] == "[REDACTED]"
        assert result["outer"]["inner"]["token"] == "[REDACTED]"
        assert result["outer"]["inner"]["safe"] == "ok"

    def test_sanitize_list(self):
        from core.models.telemetry import SafeTelemetry
        data = [{"api_key": "x"}, {"normal": "y"}]
        result = SafeTelemetry.sanitize(data)
        assert result[0]["api_key"] == "[REDACTED]"
        assert result[1]["normal"] == "y"

    def test_sanitize_scalar(self):
        from core.models.telemetry import SafeTelemetry
        assert SafeTelemetry.sanitize("hello") == "hello"
        assert SafeTelemetry.sanitize(42) == 42
        assert SafeTelemetry.sanitize(None) is None

    def test_emit_writes_jsonl(self, tmp_path):
        from core.models.telemetry import SafeTelemetry
        t = SafeTelemetry(tmp_path)
        t.emit("test_event", {"api_key": "secret", "normal": "value"})

        log_file = tmp_path / "fabric_telemetry.jsonl"
        assert log_file.exists()

        lines = log_file.read_text(encoding="utf-8").strip().split("\n")
        assert len(lines) == 1

        record = json.loads(lines[0])
        assert record["event"] == "test_event"
        assert record["payload"]["api_key"] == "[REDACTED]"
        assert record["payload"]["normal"] == "value"
        assert "timestamp" in record

    def test_emit_appends(self, tmp_path):
        from core.models.telemetry import SafeTelemetry
        t = SafeTelemetry(tmp_path)
        t.emit("event1", {})
        t.emit("event2", {})

        log_file = tmp_path / "fabric_telemetry.jsonl"
        lines = log_file.read_text(encoding="utf-8").strip().split("\n")
        assert len(lines) == 2

    def test_init_creates_directory(self, tmp_path):
        from core.models.telemetry import SafeTelemetry
        nested = tmp_path / "a" / "b" / "c"
        t = SafeTelemetry(nested)
        assert nested.exists()


# ============================================================
# 7. core/actions.py
# ============================================================

class TestActionToolbox:
    def test_safe_path_rejects_outside(self, tmp_path, monkeypatch):
        """Chemin hors sandbox -> ValueError."""
        from core import actions as act_mod

        # Patcher SAFE_ROOT vers un tmp
        fake_safe = tmp_path / "sandbox"
        fake_safe.mkdir()
        monkeypatch.setattr(act_mod, "SAFE_ROOT", fake_safe)

        toolbox = act_mod.ActionToolbox()
        with pytest.raises(ValueError, match="refusé|sandbox"):
            toolbox._safe_path("../../etc/passwd")

    def test_safe_path_accepts_inside(self, tmp_path, monkeypatch):
        from core import actions as act_mod
        fake_safe = tmp_path / "sandbox"
        fake_safe.mkdir()
        monkeypatch.setattr(act_mod, "SAFE_ROOT", fake_safe)

        toolbox = act_mod.ActionToolbox()
        result = toolbox._safe_path("subdir/file.txt")
        assert str(result).startswith(str(fake_safe))

    def test_create_file(self, tmp_path, monkeypatch):
        from core import actions as act_mod
        fake_safe = tmp_path / "sandbox"
        monkeypatch.setattr(act_mod, "SAFE_ROOT", fake_safe)

        toolbox = act_mod.ActionToolbox()
        result = toolbox.create_file("test.txt", "hello")

        assert "Fichier créé" in result
        assert (fake_safe / "test.txt").read_text(encoding="utf-8") == "hello"

    def test_create_file_creates_parents(self, tmp_path, monkeypatch):
        from core import actions as act_mod
        fake_safe = tmp_path / "sandbox"
        monkeypatch.setattr(act_mod, "SAFE_ROOT", fake_safe)

        toolbox = act_mod.ActionToolbox()
        toolbox.create_file("a/b/c/deep.txt", "content")
        assert (fake_safe / "a" / "b" / "c" / "deep.txt").exists()

    def test_create_folder(self, tmp_path, monkeypatch):
        from core import actions as act_mod
        fake_safe = tmp_path / "sandbox"
        monkeypatch.setattr(act_mod, "SAFE_ROOT", fake_safe)

        toolbox = act_mod.ActionToolbox()
        result = toolbox.create_folder("newdir")
        assert "Dossier prêt" in result
        assert (fake_safe / "newdir").is_dir()

    def test_list_files(self, tmp_path, monkeypatch):
        from core import actions as act_mod
        fake_safe = tmp_path / "sandbox"
        fake_safe.mkdir()
        (fake_safe / "file1.txt").write_text("a")
        (fake_safe / "file2.txt").write_text("b")
        monkeypatch.setattr(act_mod, "SAFE_ROOT", fake_safe)

        toolbox = act_mod.ActionToolbox()
        result = toolbox.list_files(".")
        assert "file1.txt" in result
        assert "file2.txt" in result

    def test_list_files_nonexistent(self, tmp_path, monkeypatch):
        from core import actions as act_mod
        fake_safe = tmp_path / "sandbox"
        fake_safe.mkdir()
        monkeypatch.setattr(act_mod, "SAFE_ROOT", fake_safe)

        toolbox = act_mod.ActionToolbox()
        result = toolbox.list_files("nonexistent_dir")
        assert "introuvable" in result

    def test_status(self, tmp_path, monkeypatch):
        from core import actions as act_mod
        fake_safe = tmp_path / "sandbox"
        monkeypatch.setattr(act_mod, "SAFE_ROOT", fake_safe)

        toolbox = act_mod.ActionToolbox()
        result = toolbox.status()
        assert result["policy"] == "sandbox_only"
        assert result["destructive_actions"] is False
        assert result["can_create_files"] is True


# ============================================================
# 8. core/observability/tracer.py
# ============================================================

class TestExecutionTracer:
    @pytest.mark.asyncio
    async def test_init_creates_table(self, tmp_path):
        from core.observability.tracer import ExecutionTracer
        db_path = str(tmp_path / "test.db")
        tracer = ExecutionTracer(db_path=db_path)
        await tracer.init()

        # Verifier que la table existe
        conn = sqlite3.connect(db_path)
        try:
            cur = conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name='execution_traces'"
            )
            assert cur.fetchone() is not None
        finally:
            conn.close()

    @pytest.mark.asyncio
    async def test_log_trace_inserts(self, tmp_path):
        from core.observability.tracer import ExecutionTracer
        db_path = str(tmp_path / "test.db")
        tracer = ExecutionTracer(db_path=db_path)

        await tracer.log_trace(
            provider="test_provider",
            mode="test_mode",
            latency_ms=42.5,
            status="success",
            session_id="sess1",
        )

        # Verifier l'insertion
        conn = sqlite3.connect(db_path)
        try:
            cur = conn.execute("SELECT provider, status FROM execution_traces")
            row = cur.fetchone()
            assert row[0] == "test_provider"
            assert row[1] == "success"
        finally:
            conn.close()

    @pytest.mark.asyncio
    async def test_log_trace_swallows_exception(self, tmp_path, caplog):
        """Erreur SQLite -> log error, ne propage pas."""
        from core.observability.tracer import ExecutionTracer
        tracer = ExecutionTracer(db_path=str(tmp_path / "test.db"))

        # Mocker aiosqlite.connect pour lever
        with patch("core.observability.tracer.aiosqlite.connect",
                   side_effect=RuntimeError("db error")):
            # Ne doit pas lever
            await tracer.log_trace("p", "m", 1.0, "error")

    @pytest.mark.asyncio
    async def test_get_recent_traces(self, tmp_path):
        from core.observability.tracer import ExecutionTracer
        db_path = str(tmp_path / "test.db")
        tracer = ExecutionTracer(db_path=db_path)

        # Inserer 3 traces
        for i in range(3):
            await tracer.log_trace(
                provider=f"p{i}", mode="m", latency_ms=1.0, status="ok",
            )

        results = await tracer.get_recent_traces(limit=2)
        assert len(results) == 2
        # Ordre DESC -> p2 puis p1
        assert results[0]["provider"] == "p2"

    @pytest.mark.asyncio
    async def test_get_recent_traces_exception_returns_empty(self, tmp_path):
        """Erreur SQLite -> retourne []."""
        from core.observability.tracer import ExecutionTracer
        tracer = ExecutionTracer(db_path=str(tmp_path / "test.db"))

        with patch("core.observability.tracer.aiosqlite.connect",
                   side_effect=RuntimeError("db error")):
            results = await tracer.get_recent_traces(limit=5)
        assert results == []
