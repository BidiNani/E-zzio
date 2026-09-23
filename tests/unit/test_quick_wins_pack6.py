"""Tests Pack 6 : 6 fichiers a 100%.

- core/tasks/models.py : TaskState + ALLOWED_TRANSITIONS + Task.transition_to
- core/orchestrator.py : Orchestrator.run (async + bus + router + sandbox)
- core/decision_router.py : DecisionRouter (search + fallback + erreurs)
- core/cognition/model_router.py : ModelRouter.select_engine (branches role)
- core/generators/media_engine.py : MediaEngine (WAV + OBJ)
- core/sandbox.py : SecuritySandbox (assess_risk + execute)
"""
from __future__ import annotations

import asyncio
import wave
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# ============================================================
# 1. core/tasks/models.py
# ============================================================

class TestTaskState:
    def test_taskstate_is_strenum(self):
        from core.tasks.models import TaskState
        assert issubclass(TaskState, str)
        assert TaskState.DRAFT == "DRAFT"
        assert TaskState.COMPLETED.value == "COMPLETED"

    def test_allowed_transitions_draft(self):
        from core.tasks.models import ALLOWED_TRANSITIONS, TaskState
        assert TaskState.SCOPED in ALLOWED_TRANSITIONS[TaskState.DRAFT]
        assert TaskState.CANCELLED in ALLOWED_TRANSITIONS[TaskState.DRAFT]

    def test_allowed_transitions_terminal_states_empty(self):
        from core.tasks.models import ALLOWED_TRANSITIONS, TaskState
        assert ALLOWED_TRANSITIONS[TaskState.COMPLETED] == []
        assert ALLOWED_TRANSITIONS[TaskState.CANCELLED] == []


class TestTask:
    def test_task_default_init(self):
        from core.tasks.models import Task, TaskState
        t = Task(title="Test task", workspace="ws1")
        assert t.title == "Test task"
        assert t.workspace == "ws1"
        assert t.state == TaskState.DRAFT
        assert t.task_id.startswith("tsk_")
        assert t.scope == {}
        assert t.plan == []
        assert t.approval_id is None
        assert t.error_message is None

    def test_task_unique_ids(self):
        from core.tasks.models import Task
        t1 = Task(title="a", workspace="w")
        t2 = Task(title="a", workspace="w")
        assert t1.task_id != t2.task_id

    def test_valid_transition_draft_to_scoped(self):
        from core.tasks.models import Task, TaskState
        t = Task(title="a", workspace="w")
        t.transition_to(TaskState.SCOPED)
        assert t.state == TaskState.SCOPED

    def test_valid_transition_full_lifecycle(self):
        from core.tasks.models import Task, TaskState
        t = Task(title="a", workspace="w")
        t.transition_to(TaskState.SCOPED)
        t.transition_to(TaskState.PLANNED)
        t.transition_to(TaskState.AWAITING_APPROVAL)
        t.transition_to(TaskState.EXECUTING)
        t.transition_to(TaskState.VERIFYING)
        t.transition_to(TaskState.COMPLETED)
        assert t.state == TaskState.COMPLETED

    def test_invalid_transition_raises(self):
        from core.tasks.models import (
            InvalidStateTransitionError,
            Task,
            TaskState,
        )
        t = Task(title="a", workspace="w")
        with pytest.raises(InvalidStateTransitionError):
            t.transition_to(TaskState.COMPLETED)  # DRAFT -> COMPLETED interdit

    def test_transition_updates_timestamp(self):
        from core.tasks.models import Task, TaskState
        t = Task(title="a", workspace="w")
        old_ts = t.updated_at
        import time
        time.sleep(0.01)
        t.transition_to(TaskState.SCOPED)
        assert t.updated_at > old_ts

    def test_cancel_from_any_active_state(self):
        from core.tasks.models import Task, TaskState
        t = Task(title="a", workspace="w")
        t.transition_to(TaskState.SCOPED)
        t.transition_to(TaskState.CANCELLED)
        assert t.state == TaskState.CANCELLED

    def test_failed_can_retry_to_planned(self):
        from core.tasks.models import Task, TaskState
        t = Task(title="a", workspace="w")
        t.transition_to(TaskState.SCOPED)
        t.transition_to(TaskState.PLANNED)
        t.transition_to(TaskState.AWAITING_APPROVAL)
        t.transition_to(TaskState.EXECUTING)
        t.transition_to(TaskState.FAILED)
        t.transition_to(TaskState.PLANNED)  # retry autorisé
        assert t.state == TaskState.PLANNED


# ============================================================
# 2. core/orchestrator.py
# ============================================================

def _make_orchestrator():
    """Construit un Orchestrator avec bus + router mockés."""
    from core.orchestrator import Orchestrator
    bus = MagicMock()
    bus.emit = AsyncMock()
    router = MagicMock()
    router.resolve_route = MagicMock(return_value={
        "primary": {"provider": "groq", "model": "qwen"},
    })
    router.complete = AsyncMock(return_value={
        "text": "Reponse finale",
        "provider_used": "groq",
        "model_used": "qwen",
        "fallback_triggered": False,
    })
    sandbox = MagicMock()
    sandbox.assess_risk = MagicMock(return_value=("safe", False))
    sandbox.execute = AsyncMock(return_value=MagicMock(
        command="ls",
        exit_code=0,
        stdout="file.txt",
        stderr="",
        approved=True,
    ))
    orch = Orchestrator(bus=bus, router=router, sandbox=sandbox)
    return orch, bus, router, sandbox


class TestOrchestrator:
    @pytest.mark.asyncio
    async def test_run_simple_prompt(self):
        orch, bus, router, sandbox = _make_orchestrator()
        result = await orch.run(run_id="r1", prompt="Bonjour")
        assert result["status"] == "completed"
        assert result["text"] == "Reponse finale"
        assert result["provider"] == "groq"
        assert result["execution"] is None  # pas de exec:
        # 3 emit : plan, thought, final
        assert bus.emit.await_count == 3

    @pytest.mark.asyncio
    async def test_run_with_exec_command(self):
        orch, bus, router, sandbox = _make_orchestrator()
        result = await orch.run(run_id="r2", prompt="exec: ls -la")
        assert result["status"] == "completed"
        assert result["execution"] is not None
        assert result["execution"]["command"] == "ls"
        # 5 emit : plan, thought, tool_call, terminal, final
        assert bus.emit.await_count == 5

    @pytest.mark.asyncio
    async def test_run_with_run_prefix(self):
        orch, bus, router, sandbox = _make_orchestrator()
        result = await orch.run(run_id="r3", prompt="run: echo hello")
        assert result["execution"] is not None

    @pytest.mark.asyncio
    async def test_run_router_exception_returns_failed(self):
        orch, bus, router, sandbox = _make_orchestrator()
        router.resolve_route = MagicMock(side_effect=RuntimeError("boom"))
        result = await orch.run(run_id="r4", prompt="test")
        assert result["status"] == "failed"
        assert "boom" in result["error"]

    @pytest.mark.asyncio
    async def test_run_sandbox_sensitive_command(self):
        orch, bus, router, sandbox = _make_orchestrator()
        sandbox.assess_risk = MagicMock(return_value=("sensitive", True))
        result = await orch.run(run_id="r5", prompt="exec: rm -rf dir")
        assert result["status"] == "completed"
        # L'event tool_call doit avoir requires_approval=True
        # On peut verifier les appels
        calls = bus.emit.await_args_list
        tool_calls = [c for c in calls if c.args[0].event_type == "tool_call"]
        assert len(tool_calls) == 1
        assert tool_calls[0].args[0].requires_approval is True


# ============================================================
# 3. core/decision_router.py
# ============================================================

def _make_provider(name: str, result=None, side_effect=None):
    """Construit un mock IResearchProvider.

    Si result est explicitement fourni (y compris {}), on l'utilise tel quel.
    Sinon on utilise un resultat par defaut.
    """
    p = MagicMock()
    p.name = name
    if side_effect:
        p.search = AsyncMock(side_effect=side_effect)
    elif result is not None:
        p.search = AsyncMock(return_value=result)
    else:
        p.search = AsyncMock(return_value={"provider": name, "data": {}})
    return p


class TestDecisionRouter:
    def test_search_mode_enum(self):
        from core.decision_router import SearchMode
        assert SearchMode.FAST.value == "fast"
        assert SearchMode.RESEARCH.value == "research"
        assert SearchMode.FORENSIC.value == "forensic"
        assert SearchMode.GOOGLE.value == "google"
        assert SearchMode.LOCAL.value == "local"

    def test_init_maps_providers_by_name(self):
        from core.decision_router import DecisionRouter
        p1 = _make_provider("tavily")
        p2 = _make_provider("jina")
        dr = DecisionRouter(providers=[p1, p2])
        assert dr._provider_map["tavily"] is p1
        assert dr._provider_map["jina"] is p2

    def test_select_providers_by_mode(self):
        from core.decision_router import DecisionRouter, SearchMode
        p_tav = _make_provider("tavily")
        p_jina = _make_provider("jina")
        dr = DecisionRouter(providers=[p_tav, p_jina])
        # FAST -> ["tavily", "jina"]
        selected = dr._select_providers(SearchMode.FAST)
        assert selected == [p_tav, p_jina]

    def test_select_providers_fallback_to_all(self):
        from core.decision_router import DecisionRouter, SearchMode
        p_unknown = _make_provider("unknown")
        dr = DecisionRouter(providers=[p_unknown])
        # FAST -> ["tavily", "jina"] mais aucun dispo -> fallback all
        selected = dr._select_providers(SearchMode.FAST)
        assert selected == [p_unknown]

    @pytest.mark.asyncio
    async def test_search_empty_providers_raises(self):
        from core.decision_router import DecisionRouter
        dr = DecisionRouter(providers=[])
        with pytest.raises(RuntimeError, match="Aucun fournisseur"):
            await dr.search("query")

    @pytest.mark.asyncio
    async def test_search_first_provider_succeeds(self):
        from core.decision_router import DecisionRouter, SearchMode
        p_tav = _make_provider("tavily", result={"provider": "tavily", "data": {"hits": 3}})
        dr = DecisionRouter(providers=[p_tav])
        result = await dr.search("query", mode=SearchMode.FAST)
        assert result["mode"] == "fast"
        assert result["provider"] == "tavily"
        assert result["data"] == {"hits": 3}

    @pytest.mark.asyncio
    async def test_search_fallback_on_exception(self):
        from core.decision_router import DecisionRouter, SearchMode
        p_tav = _make_provider("tavily", side_effect=RuntimeError("network fail"))
        p_jina = _make_provider("jina", result={"provider": "jina", "data": {"ok": 1}})
        dr = DecisionRouter(providers=[p_tav, p_jina])
        result = await dr.search("query", mode=SearchMode.FAST)
        assert result["provider"] == "jina"

    @pytest.mark.asyncio
    async def test_search_all_fail_raises_with_summary(self):
        from core.decision_router import DecisionRouter, SearchMode
        p_tav = _make_provider("tavily", side_effect=RuntimeError("fail1"))
        p_jina = _make_provider("jina", side_effect=ValueError("fail2"))
        dr = DecisionRouter(providers=[p_tav, p_jina])
        with pytest.raises(RuntimeError, match="Échec de recherche"):
            await dr.search("query", mode=SearchMode.FAST)

    @pytest.mark.asyncio
    async def test_search_provider_returns_empty_dict_falls_through(self):
        from core.decision_router import DecisionRouter, SearchMode
        p_tav = _make_provider("tavily", result={})  # falsy
        p_jina = _make_provider("jina", result={"provider": "jina", "data": {"x": 1}})
        dr = DecisionRouter(providers=[p_tav, p_jina])
        result = await dr.search("query", mode=SearchMode.FAST)
        assert result["provider"] == "jina"


# ============================================================
# 4. core/cognition/model_router.py
# ============================================================

def _make_model_record(name="gpt-4", source_name="API"):
    rec = MagicMock()
    rec.name = name
    rec.source = MagicMock()
    rec.source.name = source_name
    return rec


class TestModelRouter:
    def test_router_instantiable(self):
        from core.cognition.model_router import ModelRouter
        r = ModelRouter()
        assert r is not None

    def test_select_engine_coding(self):
        from core.cognition.model_router import ModelRouter
        r = ModelRouter()
        with patch("core.cognition.model_router.canonical_model_registry") as reg:
            reg.get_by_role = MagicMock(return_value=_make_model_record("code-llm", "API"))
            result = r.select_engine(task_type="code generation")
        assert result["role"] == "CODING"
        assert result["thinking_level"] == "low"

    def test_select_engine_forensic(self):
        from core.cognition.model_router import ModelRouter
        r = ModelRouter()
        with patch("core.cognition.model_router.canonical_model_registry") as reg:
            reg.get_by_role = MagicMock(return_value=_make_model_record("for-llm"))
            result = r.select_engine(task_type="forensic audit")
        assert result["role"] == "FORENSIC"
        assert result["thinking_level"] == "medium"

    def test_select_engine_refactor(self):
        from core.cognition.model_router import ModelRouter
        r = ModelRouter()
        with patch("core.cognition.model_router.canonical_model_registry") as reg:
            reg.get_by_role = MagicMock(return_value=_make_model_record("ref-llm"))
            result = r.select_engine(task_type="refactor module")
        assert result["role"] == "REFACTOR"

    def test_select_engine_fast_infra(self):
        from core.cognition.model_router import ModelRouter
        r = ModelRouter()
        with patch("core.cognition.model_router.canonical_model_registry") as reg:
            reg.get_by_role = MagicMock(return_value=_make_model_record("fast-llm"))
            result = r.select_engine(task_type="infra task")
        assert result["role"] == "FAST"
        assert result["thinking_level"] == "off"

    def test_select_engine_fast_chat_low_complexity(self):
        from core.cognition.model_router import ModelRouter
        r = ModelRouter()
        with patch("core.cognition.model_router.canonical_model_registry") as reg:
            reg.get_by_role = MagicMock(return_value=_make_model_record("chat-llm"))
            result = r.select_engine(complexity_score=0.1, risk_level="low")
        assert result["role"] == "FAST_CHAT"

    def test_select_engine_standard_chat(self):
        from core.cognition.model_router import ModelRouter
        r = ModelRouter()
        with patch("core.cognition.model_router.canonical_model_registry") as reg:
            reg.get_by_role = MagicMock(return_value=_make_model_record("std-llm"))
            result = r.select_engine(complexity_score=0.5)
        assert result["role"] == "STANDARD_CHAT"
        assert result["thinking_level"] in ("low", "medium")

    def test_select_engine_master_strategic(self):
        from core.cognition.model_router import ModelRouter
        r = ModelRouter()
        with patch("core.cognition.model_router.canonical_model_registry") as reg:
            reg.get_by_role = MagicMock(return_value=_make_model_record("master-llm"))
            result = r.select_engine(complexity_score=0.95)
        assert result["role"] == "MASTER_STRATEGIC"
        assert result["thinking_level"] == "high"

    def test_select_engine_fallback_master(self):
        from core.cognition.model_router import ModelRouter
        r = ModelRouter()

        def side_effect(role):
            if role == "CODING":
                return None
            if role in ("MASTER_STRATEGIC", "MASTER"):
                return _make_model_record("fallback-master")
            return None

        with patch("core.cognition.model_router.canonical_model_registry") as reg:
            reg.get_by_role = MagicMock(side_effect=side_effect)
            result = r.select_engine(task_type="code")
        assert result["model"] == "fallback-master"

    def test_select_engine_no_record_uses_default(self):
        from core.cognition.model_router import ModelRouter
        r = ModelRouter()
        with patch("core.cognition.model_router.canonical_model_registry") as reg:
            reg.get_by_role = MagicMock(return_value=None)
            result = r.select_engine(task_type="general")
        assert result["model"] == "gemini-3.8-flash"
        assert result["provider"] == "api"

    def test_select_engine_local_provider(self):
        from core.cognition.model_router import ModelRouter
        r = ModelRouter()
        with patch("core.cognition.model_router.canonical_model_registry") as reg:
            reg.get_by_role = MagicMock(return_value=_make_model_record("llama", "LOCAL"))
            result = r.select_engine(task_type="code")
        assert result["provider"] == "ollama"


# ============================================================
# 5. core/generators/media_engine.py
# ============================================================

class TestMediaEngine:
    def test_engine_init_creates_exports_dir(self, tmp_path):
        from core.generators.media_engine import MediaEngine
        engine = MediaEngine(workspace_root=str(tmp_path))
        assert engine.exports_dir.exists()
        assert engine.exports_dir.name == "exports"

    def test_generate_tone_wav_creates_file(self, tmp_path):
        from core.generators.media_engine import MediaEngine
        engine = MediaEngine(workspace_root=str(tmp_path))
        result = engine.generate_tone_wav("test_tone", frequency_hz=440.0, duration_sec=0.1)
        assert result["ok"] is True
        assert result["filename"] == "test_tone.wav"
        assert Path(result["path"]).exists()
        assert result["size_bytes"] > 0

    def test_generate_tone_wav_adds_extension(self, tmp_path):
        from core.generators.media_engine import MediaEngine
        engine = MediaEngine(workspace_root=str(tmp_path))
        result = engine.generate_tone_wav("sans_extension")
        assert result["filename"] == "sans_extension.wav"

    def test_generate_tone_wav_is_valid_wav(self, tmp_path):
        from core.generators.media_engine import MediaEngine
        engine = MediaEngine(workspace_root=str(tmp_path))
        result = engine.generate_tone_wav("check", duration_sec=0.05)
        # Lire avec wave pour valider le format
        with wave.open(result["path"], "r") as wf:
            assert wf.getnchannels() == 1
            assert wf.getsampwidth() == 2
            assert wf.getframerate() == 44100

    def test_generate_3d_cube_obj(self, tmp_path):
        from core.generators.media_engine import MediaEngine
        engine = MediaEngine(workspace_root=str(tmp_path))
        result = engine.generate_3d_cube_obj("cube_test")
        assert result["ok"] is True
        assert result["filename"] == "cube_test.obj"
        assert result["vertices_count"] == 8
        assert result["faces_count"] == 12
        assert Path(result["path"]).exists()

    def test_generate_3d_cube_obj_content(self, tmp_path):
        from core.generators.media_engine import MediaEngine
        engine = MediaEngine(workspace_root=str(tmp_path))
        result = engine.generate_3d_cube_obj("cube", color_name="Red")
        content = Path(result["path"]).read_text(encoding="utf-8")
        assert "o Cube_Red" in content
        assert content.count("v ") == 8
        assert content.count("f ") == 12

    def test_generate_3d_cube_obj_adds_extension(self, tmp_path):
        from core.generators.media_engine import MediaEngine
        engine = MediaEngine(workspace_root=str(tmp_path))
        result = engine.generate_3d_cube_obj("no_ext")
        assert result["filename"] == "no_ext.obj"

    def test_filename_sanitized_by_basename(self, tmp_path):
        from core.generators.media_engine import MediaEngine
        engine = MediaEngine(workspace_root=str(tmp_path))
        result = engine.generate_tone_wav("../../etc/passwd", duration_sec=0.01)
        # os.path.basename -> "passwd.wav"
        assert result["filename"] == "passwd.wav"


# ============================================================
# 6. core/sandbox.py
# ============================================================

class TestExecutionResult:
    def test_execution_result_dataclass(self):
        from core.sandbox import ExecutionResult
        r = ExecutionResult(
            command="ls", exit_code=0, stdout="x", stderr="",
            risk_level="safe",
        )
        assert r.command == "ls"
        assert r.approved is True  # defaut

    def test_execution_result_approved_false(self):
        from core.sandbox import ExecutionResult
        r = ExecutionResult(
            command="rm -rf /", exit_code=-1, stdout="", stderr="blocked",
            risk_level="blocked", approved=False,
        )
        assert r.approved is False


class TestSecuritySandbox:
    def test_init(self):
        from core.sandbox import SecuritySandbox
        sb = SecuritySandbox(workspace_root=".")
        assert sb.workspace_root.exists()

    def test_assess_risk_safe_command(self):
        from core.sandbox import SecuritySandbox
        sb = SecuritySandbox()
        risk, needs_approval = sb.assess_risk("ls -la")
        assert risk == "safe"
        assert needs_approval is False

    def test_assess_risk_blocked_command(self):
        from core.sandbox import SecuritySandbox
        sb = SecuritySandbox()
        risk, needs_approval = sb.assess_risk("rm -rf /")
        assert risk == "blocked"
        assert needs_approval is False

    def test_assess_risk_blocked_mkfs(self):
        from core.sandbox import SecuritySandbox
        sb = SecuritySandbox()
        risk, _ = sb.assess_risk("mkfs.ext4 /dev/sda1")
        assert risk == "blocked"

    def test_assess_risk_sensitive_rm(self):
        from core.sandbox import SecuritySandbox
        sb = SecuritySandbox()
        risk, needs = sb.assess_risk("rm file.txt")
        assert risk == "sensitive"
        assert needs is True

    def test_assess_risk_sensitive_git_push(self):
        from core.sandbox import SecuritySandbox
        sb = SecuritySandbox()
        risk, needs = sb.assess_risk("git push origin main")
        assert risk == "sensitive"
        assert needs is True

    def test_assess_risk_sensitive_with_and(self):
        from core.sandbox import SecuritySandbox
        sb = SecuritySandbox()
        risk, needs = sb.assess_risk("ls && rm file.txt")
        assert risk == "sensitive"

    def test_assess_risk_sensitive_with_semicolon(self):
        from core.sandbox import SecuritySandbox
        sb = SecuritySandbox()
        risk, needs = sb.assess_risk("ls ; rm file")
        assert risk == "sensitive"

    @pytest.mark.asyncio
    async def test_execute_blocked_command(self):
        from core.sandbox import SecuritySandbox
        sb = SecuritySandbox()
        result = await sb.execute("rm -rf /")
        assert result.exit_code == -1
        assert result.risk_level == "blocked"
        assert result.approved is False
        assert "bloquée" in result.stderr.lower() or "interdite" in result.stderr.lower()

    @pytest.mark.asyncio
    async def test_execute_sensitive_without_approval(self):
        from core.sandbox import SecuritySandbox
        sb = SecuritySandbox()
        result = await sb.execute("rm file.txt", is_approved=False)
        assert result.exit_code == -1
        assert result.risk_level == "sensitive"
        assert result.approved is False

    @pytest.mark.asyncio
    async def test_execute_safe_command(self, tmp_path):
        from core.sandbox import SecuritySandbox
        sb = SecuritySandbox(workspace_root=tmp_path)
        result = await sb.execute("echo hello")
        assert result.exit_code == 0
        assert "hello" in result.stdout
        assert result.approved is True

    @pytest.mark.asyncio
    async def test_execute_timeout(self, tmp_path):
        from core.sandbox import SecuritySandbox
        sb = SecuritySandbox(workspace_root=tmp_path)

        # Mocker create_subprocess_shell pour simuler un timeout
        mock_proc = MagicMock()
        mock_proc.communicate = AsyncMock(side_effect=TimeoutError())
        mock_proc.kill = MagicMock()

        with patch("core.sandbox.asyncio.create_subprocess_shell",
                   new=AsyncMock(return_value=mock_proc)):
            result = await sb.execute("sleep 100", timeout=0.1)
        assert result.exit_code == -1
        assert "délai" in result.stderr.lower() or "timeout" in result.stderr.lower() or "interrompu" in result.stderr.lower()

    @pytest.mark.asyncio
    async def test_execute_generic_exception(self, tmp_path):
        from core.sandbox import SecuritySandbox
        sb = SecuritySandbox(workspace_root=tmp_path)

        with patch("core.sandbox.asyncio.create_subprocess_shell",
                   new=AsyncMock(side_effect=RuntimeError("subprocess fail"))):
            result = await sb.execute("echo test")
        assert result.exit_code == -1
        assert "subprocess fail" in result.stderr

    @pytest.mark.asyncio
    async def test_execute_timeout_process_lookup_error(self, tmp_path):
        """Timeout + kill leve ProcessLookupError -> avale."""
        from core.sandbox import SecuritySandbox
        sb = SecuritySandbox(workspace_root=tmp_path)

        mock_proc = MagicMock()
        mock_proc.communicate = AsyncMock(side_effect=TimeoutError())
        mock_proc.kill = MagicMock(side_effect=ProcessLookupError())

        with patch("core.sandbox.asyncio.create_subprocess_shell",
                   new=AsyncMock(return_value=mock_proc)):
            result = await sb.execute("sleep 100")
        assert result.exit_code == -1
