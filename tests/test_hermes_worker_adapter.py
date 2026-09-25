"""Tests for E-ZZIO Hermes Agent External Worker Adapter and Master Delegation.

Validates:
1. Hermes command construction & exact arguments
2. Structured JSONL parsing
3. Timeout handling & process tree termination
4. Non-zero exit handling
5. Successful worker result
6. Policy & workspace boundary enforcement
7. Master -> Hermes task delegation
8. Result -> Master validation & strategic synthesis
9. Hermes version capture
10. HERMES_HOME isolation & automatic cleanup
11. Model routing fidelity
12. E2E real Hermes subprocess execution proof (live PID, exit_code, duration, home cleanup)
"""
from __future__ import annotations

import asyncio
import os
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from core.agent.hermes_worker_adapter import (
    DEFAULT_WORKER_TOOLSETS,
    FORBIDDEN_WORKER_TOOLSETS,
    HermesWorkerAdapter,
    HermesWorkerResult,
)
from core.agent.hermes_worker_profiles import (
    ANALYST_PROFILE,
    CODER_PROFILE,
    CONTEXT_ONLY_AUDITOR,
    CONTEXT_ONLY_READER,
    OPERATOR_PROFILE,
    RESEARCHER_PROFILE,
    TESTER_PROFILE,
    WORKER_PROFILES,
    ContextPack,
    NetworkPolicy,
    ResolvedWorkerCapabilities,
    WorkerProfileType,
    build_context_pack,
    is_capability_allowed,
    parse_structured_result,
    render_context_prompt,
    resolve_profile,
)
from core.ezzio_master import EzzioMaster
from core.providers.base_provider import ProviderResponse


class FakeSynthesisProvider:
    """Deterministic offline provider for Master synthesis."""

    async def generate(self, prompt: str = "", model: str = "gemini-3.8-flash", **kwargs: Any) -> ProviderResponse:
        return ProviderResponse(
            content=f"[SYNTHÈSE MASTER ({model})] Synthèse complète des résultats du worker.",
            model=model or "gemini-3.8-flash",
            provider="gemini",
        )


# 1. Command construction & zero-toolsets boundary
def test_hermes_command_construction_zero_toolsets():
    adapter = HermesWorkerAdapter(workspace_root=r"G:\AI\E-zzio", hermes_bin=r"G:\Hermes\bin\hermes.exe")
    cmd = adapter.build_cli_command(
        prompt="Analyze context files without external tools",
        model="qwen3.5:9b",
        provider="ollama",
        safe_mode=True,
    )
    assert r"G:\Hermes\bin\hermes.exe" in cmd[0]
    assert cmd[1] == "chat"
    assert "-q" in cmd
    assert "Analyze context files without external tools" in cmd
    assert "--format" in cmd and "stream-json" in cmd
    assert "--oneshot" in cmd
    assert "-Q" in cmd
    assert "--ignore-rules" in cmd
    assert "--source" in cmd and "tool" in cmd
    assert "--safe-mode" in cmd
    assert "--in" in cmd and r"G:\AI\E-zzio" in cmd
    assert "-m" in cmd and "qwen3.5:9b" in cmd
    assert "--provider" in cmd and "ollama" in cmd
    # ZERO toolsets: command MUST NOT contain --toolsets or any dangerous tool names
    assert "--toolsets" not in cmd
    assert "file" not in cmd
    assert "terminal" not in cmd
    assert "code_execution" not in cmd
    assert "process" not in cmd
    assert "delegation" not in cmd
    assert "memory" not in cmd


def test_worker_toolsets_boundary_definitions():
    # Zero-tool default: bounded workers receive no tools
    assert len(DEFAULT_WORKER_TOOLSETS) == 0
    for forbidden in ["file", "terminal", "code_execution", "process", "delegation", "memory", "session_search", "browser"]:
        assert forbidden in FORBIDDEN_WORKER_TOOLSETS
        assert forbidden not in DEFAULT_WORKER_TOOLSETS


# 2. Structured JSONL parsing
def test_structured_jsonl_parsing():
    adapter = HermesWorkerAdapter(workspace_root=r"G:\AI\E-zzio")
    raw_stdout = (
        '{"type": "system", "subtype": "init", "model": "qwen3.5:9b", "provider": "ollama", "session_id": "sess-20260925-01"}\n'
        '{"type": "tool_use", "tool": "read_file", "args": {"path": "state/audit/test.jsonl"}}\n'
        '{"type": "tool_result", "output": "File content read successfully"}\n'
        '{"type": "result", "session_id": "sess-20260925-01", "exit_code": 0, "text": "Audit complete. 0 issues detected.", "duration_ms": 1450}\n'
    )
    text, tool_events, sess_id, exit_code, error, act_model, act_prov = adapter.parse_stream_json(raw_stdout)
    assert text == "Audit complete. 0 issues detected."
    assert len(tool_events) == 2
    assert tool_events[0]["type"] == "tool_use"
    assert tool_events[1]["type"] == "tool_result"
    assert sess_id == "sess-20260925-01"
    assert exit_code == 0
    assert error is None
    assert act_model == "qwen3.5:9b"
    assert act_prov == "ollama"


# 3. Timeout handling
@pytest.mark.asyncio
async def test_timeout_handling():
    adapter = HermesWorkerAdapter(workspace_root=r"G:\AI\E-zzio", default_timeout_sec=1)

    mock_proc = MagicMock()
    mock_proc.pid = 99999

    async def hanging_communicate():
        await asyncio.sleep(5)
        return b"", b""
    mock_proc.communicate = hanging_communicate

    with patch("asyncio.create_subprocess_exec", AsyncMock(return_value=mock_proc)):
        with patch.object(adapter, "_terminate_process_tree") as mock_kill:
            result = await adapter.submit(task_id="tsk-timeout-01", prompt="Hanging task", timeout=1)
            assert result.status == "TIMEOUT"
            assert result.exit_code == -3
            assert "Worker timeout after 1s" in result.stderr
            mock_kill.assert_called_once_with(99999)


# 4. Non-zero exit handling
@pytest.mark.asyncio
async def test_non_zero_exit_handling():
    adapter = HermesWorkerAdapter(workspace_root=r"G:\AI\E-zzio")

    mock_proc = MagicMock()
    mock_proc.pid = 88888
    mock_proc.returncode = 1
    error_stdout = (
        '{"type": "system", "subtype": "init", "session_id": "sess-err-01"}\n'
        '{"type": "result", "session_id": "sess-err-01", "exit_code": 1, "text": "", "error": "Model connection refused"}\n'
    )
    mock_proc.communicate = AsyncMock(return_value=(error_stdout.encode("utf-8"), b"STDERR: Connection refused\n"))

    with patch("asyncio.create_subprocess_exec", AsyncMock(return_value=mock_proc)):
        result = await adapter.submit(task_id="tsk-err-01", prompt="Failing task")
        assert result.status == "FAILED"
        assert result.exit_code == 1
        assert "Model connection refused" in (result.error or "")
        assert result.session_id == "sess-err-01"


# 5. Successful worker result
@pytest.mark.asyncio
async def test_successful_worker_result():
    adapter = HermesWorkerAdapter(workspace_root=r"G:\AI\E-zzio")

    mock_proc = MagicMock()
    mock_proc.pid = 77777
    mock_proc.returncode = 0
    success_stdout = (
        '{"type": "system", "subtype": "init", "session_id": "sess-ok-01"}\n'
        '{"type": "result", "session_id": "sess-ok-01", "exit_code": 0, "text": "Task succeeded cleanly.", "duration_ms": 820}\n'
    )
    mock_proc.communicate = AsyncMock(return_value=(success_stdout.encode("utf-8"), b""))

    with patch("asyncio.create_subprocess_exec", AsyncMock(return_value=mock_proc)):
        result = await adapter.submit(task_id="tsk-ok-01", prompt="Clean task")
        assert result.status == "SUCCESS"
        assert result.exit_code == 0
        assert result.output == "Task succeeded cleanly."
        assert result.pid == 77777
        assert result.session_id == "sess-ok-01"


# 6. Policy / workspace boundary enforcement
@pytest.mark.asyncio
async def test_policy_workspace_boundary():
    adapter = HermesWorkerAdapter(workspace_root=r"G:\AI\E-zzio")
    with patch("asyncio.create_subprocess_exec") as mock_exec:
        result = await adapter.submit(task_id="tsk-forbidden-01", prompt="Please run git reset --hard HEAD~1")
        assert result.status == "POLICY_DENIED"
        assert result.exit_code == -2
        assert "POLICY_DENIED" in result.stderr
        mock_exec.assert_not_called()


@pytest.mark.asyncio
async def test_forbidden_toolset_policy_denied():
    adapter = HermesWorkerAdapter(workspace_root=r"G:\AI\E-zzio")
    with patch("asyncio.create_subprocess_exec") as mock_exec:
        result = await adapter.submit(
            task_id="tsk-forbidden-tool-01",
            prompt="Inspect something",
            toolsets=["terminal"],
        )
        assert result.status == "POLICY_DENIED"
        assert result.exit_code == -2
        assert "rejected" in result.stderr or "Forbidden toolsets requested" in result.stderr
        mock_exec.assert_not_called()


# 7. Master -> Hermes task delegation
@pytest.mark.asyncio
async def test_master_to_hermes_task_delegation():
    fake_prov = FakeSynthesisProvider()
    mock_adapter = MagicMock()
    mock_adapter.submit = AsyncMock(return_value=HermesWorkerResult(
        task_id="subtask-research-01",
        status="SUCCESS",
        stdout="raw jsonl",
        stderr="",
        exit_code=0,
        duration_ms=420,
        output="Hermes Worker: Analysis of dependencies completed. 0 vulnerabilities found.",
        pid=12345,
        session_id="hermes-sess-01",
    ))

    master = EzzioMaster(provider=fake_prov, hermes_adapter=mock_adapter)
    res = await master.orchestrate_multi_agent_mission(
        mission_prompt="Auditer les dépendances du projet",
        subtask_specs=[
            {
                "task_id": "subtask-research-01",
                "role": "research",
                "worker": "hermes",
                "prompt": "Inspecte les dépendances dans pyproject.toml",
            }
        ]
    )

    assert res["ok"] is True
    assert len(res["subtasks"]) == 1
    sub_res = res["subtasks"][0]
    assert sub_res["worker"] == "hermes"
    assert sub_res["pid"] == 12345
    assert sub_res["validated"] is True
    assert "Hermes Worker: Analysis of dependencies completed" in sub_res["output"]
    mock_adapter.submit.assert_called_once()


# 8. Result -> Master validation & strategic synthesis
@pytest.mark.asyncio
async def test_result_to_master_validation_and_synthesis():
    fake_prov = FakeSynthesisProvider()
    mock_adapter = MagicMock()
    mock_adapter.submit = AsyncMock(side_effect=[
        HermesWorkerResult(
            task_id="subtask-retry-01",
            status="FAILED",
            stdout="",
            stderr="Transient error",
            exit_code=1,
            duration_ms=200,
            output="",
            pid=11111,
        ),
        HermesWorkerResult(
            task_id="subtask-retry-01",
            status="SUCCESS",
            stdout="valid jsonl",
            stderr="",
            exit_code=0,
            duration_ms=350,
            output="Hermes Worker: Successfully recovered on retry.",
            pid=22222,
        ),
    ])

    master = EzzioMaster(provider=fake_prov, hermes_adapter=mock_adapter)
    res = await master.orchestrate_multi_agent_mission(
        mission_prompt="Mission avec retry worker",
        subtask_specs=[
            {
                "task_id": "subtask-retry-01",
                "role": "research",
                "worker": "hermes",
                "prompt": "Inspecte les logs de build",
            }
        ],
        max_retries=2,
    )

    assert res["ok"] is True
    assert len(res["subtasks"]) == 1
    sub_res = res["subtasks"][0]
    assert sub_res["retries"] == 1
    assert sub_res["validated"] is True
    assert sub_res["worker"] == "hermes"
    assert sub_res["pid"] == 22222
    assert "Successfully recovered on retry" in sub_res["output"]
    assert "[SYNTHÈSE MASTER" in res["synthesis"]


# 9. Hermes version capture
def test_hermes_version_capture():
    adapter = HermesWorkerAdapter(workspace_root=r"G:\AI\E-zzio")
    if adapter.is_available():
        ver = adapter.get_hermes_version()
        assert "Hermes Agent v" in ver
    else:
        pytest.skip("Hermes executable not available")


# 10. HERMES_HOME isolation & automatic cleanup
@pytest.mark.asyncio
async def test_hermes_home_isolation_and_cleanup():
    adapter = HermesWorkerAdapter(workspace_root=r"G:\AI\E-zzio")

    mock_proc = MagicMock()
    mock_proc.pid = 66666
    mock_proc.returncode = 0
    mock_proc.communicate = AsyncMock(return_value=(
        b'{"type": "result", "exit_code": 0, "text": "Isolated"}\n', b""
    ))

    captured_env: dict[str, str] = {}

    async def fake_subprocess_exec(*cmd, **kwargs):
        captured_env.update(kwargs.get("env", {}))
        return mock_proc

    with patch("asyncio.create_subprocess_exec", side_effect=fake_subprocess_exec):
        res = await adapter.submit(task_id="tsk-iso-01", prompt="Test isolation")
        assert res.hermes_home is not None
        assert "ezzio_hermes_home_" in res.hermes_home
        assert captured_env.get("HERMES_HOME") == res.hermes_home
        # Verify temporary directory is cleaned up after execution
        assert not os.path.exists(res.hermes_home), "Temporary HERMES_HOME must be cleaned up"


# 11. Model routing fidelity
@pytest.mark.asyncio
async def test_model_routing_fidelity():
    adapter = HermesWorkerAdapter(workspace_root=r"G:\AI\E-zzio")

    mock_proc = MagicMock()
    mock_proc.pid = 55555
    mock_proc.returncode = 0
    simulated_stdout = (
        '{"type": "system", "subtype": "init", "model": "qwen3.5:9b", "provider": "ollama", "session_id": "sess-fid-01"}\n'
        '{"type": "result", "session_id": "sess-fid-01", "exit_code": 0, "text": "Routing verified"}\n'
    )
    mock_proc.communicate = AsyncMock(return_value=(simulated_stdout.encode("utf-8"), b""))

    with patch("asyncio.create_subprocess_exec", AsyncMock(return_value=mock_proc)):
        res = await adapter.submit(
            task_id="tsk-fid-01",
            prompt="Test fidelity",
            model="qwen3.5:9b",
            provider="ollama",
        )
        assert res.actual_model == "qwen3.5:9b"
        assert res.actual_provider == "ollama"
        assert "-m" in res.command
        assert "qwen3.5:9b" in res.command
        assert "--provider" in res.command
        assert "ollama" in res.command


# 12. E2E Real Hermes Subprocess Execution Proof
@pytest.mark.asyncio
async def test_e2e_real_hermes_subprocess_proof():
    adapter = HermesWorkerAdapter(workspace_root=r"G:\AI\E-zzio")
    if not adapter.is_available():
        pytest.skip("Hermes executable not available on host")

    # Real OS subprocess execution of Hermes
    res = await adapter.submit(
        task_id="e2e-live-proof-01",
        prompt="Inspect local git status in workspace",
        safe_mode=True,
        timeout=6,
    )

    # Verifiable proofs of real subprocess execution
    assert res.task_id == "e2e-live-proof-01"
    assert res.pid is not None and res.pid > 0, "A real operating system PID must be assigned"
    assert res.exit_code is not None, "Process must terminate and return an exit code"
    assert res.duration_ms >= 0, "Execution duration must be measured"
    assert res.hermes_version is not None and "Hermes Agent v" in res.hermes_version
    assert res.hermes_home is not None
    # Home cleanup verification
    assert not os.path.exists(res.hermes_home), "Isolated HERMES_HOME must be deleted"
    # Command verification
    assert "--format" in res.command and "stream-json" in res.command
    assert "--safe-mode" in res.command
    assert "--ignore-rules" in res.command
    assert "--source" in res.command and "tool" in res.command


# 13. ContextPack construction
def test_context_pack_construction():
    pack = build_context_pack(
        task_id="tsk-pack-01",
        objective="Inspect web server setup",
        file_paths=["web_server.py"],
        workspace_root=r"G:\AI\E-zzio",
    )
    assert pack.task_id == "tsk-pack-01"
    assert pack.objective == "Inspect web server setup"
    assert len(pack.files) == 1
    assert pack.files[0].path == "web_server.py"
    assert "class" in pack.files[0].content or "def" in pack.files[0].content or "import" in pack.files[0].content
    assert pack.files[0].size_bytes > 0


# 14. PolicyGuard strictly excludes protected and out-of-workspace files
def test_context_pack_policy_guard_excludes_protected_files():
    # Attempting to add protected file .env or out-of-workspace path must fail-closed
    with pytest.raises(PermissionError) as exc_info:
        build_context_pack(
            task_id="tsk-pack-bad",
            objective="Attempt to read secrets",
            file_paths=["secrets/.env"],
            workspace_root=r"G:\AI\E-zzio",
        )
    assert "POLICY_DENIED" in str(exc_info.value)

    with pytest.raises(PermissionError) as exc_info2:
        build_context_pack(
            task_id="tsk-pack-escape",
            objective="Attempt directory traversal",
            file_paths=[r"..\..\Windows\win.ini"],
            workspace_root=r"G:\AI\E-zzio",
        )
    assert "POLICY_DENIED" in str(exc_info2.value)


# 15. Hermes receives context in bounded prompt
def test_hermes_receives_context_in_prompt():
    pack = build_context_pack(
        task_id="tsk-pack-prompt",
        objective="Analyze web_server architecture",
        file_paths=["web_server.py"],
        workspace_root=r"G:\AI\E-zzio",
    )
    prompt = render_context_prompt(pack, CONTEXT_ONLY_READER)
    assert "### WORKER ROLE: READER" in prompt
    assert "ZERO tools" in prompt
    assert "--- BEGIN FILE: web_server.py ---" in prompt
    assert "--- END FILE: web_server.py ---" in prompt
    assert "REQUIRED OUTPUT FORMAT (STRICT JSON ONLY)" in prompt


# 16. Hermes returns structured analysis
def test_hermes_returns_structured_analysis():
    raw_json = (
        '{\n'
        '  "status": "SUCCESS",\n'
        '  "summary": "Repository web server uses a lightweight HTTP handler.",\n'
        '  "findings": ["Port binding is configurable", "Static asset route exists"],\n'
        '  "evidence": ["web_server.py line 12"],\n'
        '  "unknowns": ["TLS termination method"],\n'
        '  "confidence": 0.95\n'
        '}'
    )
    parsed = parse_structured_result(raw_json)
    assert parsed["status"] == "SUCCESS"
    assert "lightweight HTTP handler" in parsed["summary"]
    assert len(parsed["findings"]) == 2
    assert parsed["evidence"] == ["web_server.py line 12"]
    assert parsed["confidence"] == 0.95


# 17. Reader and Auditor profile definitions
def test_reader_profile_definition():
    assert CONTEXT_ONLY_READER.name == WorkerProfileType.READER
    assert CONTEXT_ONLY_READER.hermes_toolsets == ()
    assert CONTEXT_ONLY_READER.read_only is True
    assert CONTEXT_ONLY_READER.safe_mode is True
    assert CONTEXT_ONLY_READER.memory_enabled is False
    assert CONTEXT_ONLY_READER.network_enabled is False
    assert CONTEXT_ONLY_READER.default_timeout_sec == 45


def test_auditor_profile_definition():
    assert CONTEXT_ONLY_AUDITOR.name == WorkerProfileType.AUDITOR
    assert CONTEXT_ONLY_AUDITOR.hermes_toolsets == ()
    assert CONTEXT_ONLY_AUDITOR.read_only is True
    assert CONTEXT_ONLY_AUDITOR.safe_mode is True
    assert CONTEXT_ONLY_AUDITOR.memory_enabled is False
    assert CONTEXT_ONLY_AUDITOR.network_enabled is False
    assert CONTEXT_ONLY_AUDITOR.default_timeout_sec == 60


# 18. No filesystem mutation with profile
@pytest.mark.asyncio
async def test_no_filesystem_mutation_with_profile():
    adapter = HermesWorkerAdapter(workspace_root=r"G:\AI\E-zzio")
    # Submitting with reader profile but requesting toolsets must be denied fail-closed
    with patch("asyncio.create_subprocess_exec") as mock_exec:
        res = await adapter.submit(
            task_id="tsk-profile-deny",
            prompt="Try to request tools",
            profile=CONTEXT_ONLY_READER,
            toolsets=["file"],
        )
        assert res.status == "POLICY_DENIED"
        assert res.exit_code == -2
        assert "enforces zero tools" in res.stderr
        mock_exec.assert_not_called()


# 19. Master delegates ContextPack to Reader worker
@pytest.mark.asyncio
async def test_master_delegates_context_pack_to_reader():
    fake_prov = FakeSynthesisProvider()
    mock_adapter = MagicMock()
    mock_adapter.submit = AsyncMock(return_value=HermesWorkerResult(
        task_id="subtask-context-reader",
        status="SUCCESS",
        stdout='{"type": "result", "exit_code": 0, "text": "{\\"status\\": \\"SUCCESS\\", \\"summary\\": \\"Analysis complete\\", \\"findings\\": [\\"Clean code\\"], \\"confidence\\": 1.0}"}\n',
        stderr="",
        exit_code=0,
        duration_ms=450,
        output='{"status": "SUCCESS", "summary": "Analysis complete", "findings": ["Clean code"], "confidence": 1.0}',
        pid=33333,
        session_id="hermes-ctx-sess",
    ))

    master = EzzioMaster(provider=fake_prov, hermes_adapter=mock_adapter)
    res = await master.orchestrate_multi_agent_mission(
        mission_prompt="Inspecter le serveur web",
        subtask_specs=[
            {
                "task_id": "subtask-context-reader",
                "role": "reader",
                "worker": "hermes",
                "files": ["web_server.py"],
                "prompt": "Inspecte web_server.py et résume l'architecture",
            }
        ]
    )

    assert res["ok"] is True
    assert len(res["subtasks"]) == 1
    sub = res["subtasks"][0]
    assert sub["worker"] == "hermes"
    assert sub["role"] == "reader"
    assert sub["validated"] is True
    # Ensure Hermes adapter received the call with zero-tool profile
    call_kwargs = mock_adapter.submit.call_args.kwargs
    assert call_kwargs.get("profile") == CONTEXT_ONLY_READER
    assert "--- BEGIN FILE: web_server.py ---" in call_kwargs.get("prompt", "")


# 20. Master delegates ContextPack to Auditor worker
@pytest.mark.asyncio
async def test_master_delegates_context_pack_to_auditor():
    fake_prov = FakeSynthesisProvider()
    mock_adapter = MagicMock()
    mock_adapter.submit = AsyncMock(return_value=HermesWorkerResult(
        task_id="subtask-context-auditor",
        status="SUCCESS",
        stdout='{"type": "result", "exit_code": 0, "text": "{\\"status\\": \\"SUCCESS\\", \\"summary\\": \\"Audit passed with 0 defects\\", \\"findings\\": [], \\"confidence\\": 0.99}"}\n',
        stderr="",
        exit_code=0,
        duration_ms=500,
        output='{"status": "SUCCESS", "summary": "Audit passed with 0 defects", "findings": [], "confidence": 0.99}',
        pid=44444,
        session_id="hermes-audit-sess",
    ))

    master = EzzioMaster(provider=fake_prov, hermes_adapter=mock_adapter)
    res = await master.orchestrate_multi_agent_mission(
        mission_prompt="Auditer la conformité de web_server.py",
        subtask_specs=[
            {
                "task_id": "subtask-context-auditor",
                "role": "auditor",
                "worker": "hermes",
                "files": ["web_server.py"],
                "prompt": "Vérifie les règles de sécurité",
            }
        ]
    )

    assert res["ok"] is True
    sub = res["subtasks"][0]
    assert sub["worker"] == "hermes"
    assert sub["role"] == "auditor"
    assert sub["validated"] is True
    call_kwargs = mock_adapter.submit.call_args.kwargs
    assert call_kwargs.get("profile") == CONTEXT_ONLY_AUDITOR
    assert "### WORKER ROLE: AUDITOR" in call_kwargs.get("prompt", "")


# 21. Live Context-Fed Subprocess Proof (zero tools, no filesystem mutation)
@pytest.mark.asyncio
async def test_e2e_context_fed_hermes_subprocess_proof():
    adapter = HermesWorkerAdapter(workspace_root=r"G:\AI\E-zzio")
    if not adapter.is_available():
        pytest.skip("Hermes executable not available on host")

    pack = build_context_pack(
        task_id="live-context-proof-01",
        objective="Evaluate web server entry point",
        file_paths=["web_server.py"],
        workspace_root=r"G:\AI\E-zzio",
    )
    prompt = render_context_prompt(pack, CONTEXT_ONLY_READER)

    res = await adapter.submit(
        task_id="live-context-proof-01",
        prompt=prompt,
        profile=CONTEXT_ONLY_READER,
        timeout=6,
    )

    assert res.task_id == "live-context-proof-01"
    assert res.pid is not None and res.pid > 0
    assert res.exit_code is not None
    # ZERO toolsets verification in real command:
    assert "--toolsets" not in res.command
    assert "file" not in res.command
    assert "terminal" not in res.command
    assert res.hermes_home is not None
    assert not os.path.exists(res.hermes_home)


# 22. Capability Model Snapshot Resolution
def test_capability_model_snapshot_resolution():
    res_caps = RESEARCHER_PROFILE.resolve_capabilities()
    assert res_caps.profile_name == "researcher"
    assert "web" in res_caps.toolsets
    assert "skills" in res_caps.toolsets
    assert "web_search" in res_caps.tools
    assert "web_extract" in res_caps.tools
    assert "grounded-citations" in res_caps.skills
    assert res_caps.network == "web"
    assert res_caps.memory == "disabled"
    assert res_caps.delegation is False

    op_caps = OPERATOR_PROFILE.resolve_capabilities(workspace_root=r"C:\temp\sandbox")
    assert op_caps.profile_name == "operator"
    assert "terminal" in op_caps.toolsets
    assert "file" in op_caps.toolsets
    assert "terminal" in op_caps.tools
    assert "write_file" in op_caps.tools
    assert op_caps.network == "loopback_only"
    assert op_caps.filesystem == "isolated_workspace"

    # Snapshot dictionary verification
    dict_repr = res_caps.to_dict()
    assert dict_repr["profile_name"] == "researcher"
    assert "web_search" in dict_repr["tools"]
    assert dict_repr["network"] == "web"


# 23. Profile Escalation Protection (Fail-Closed)
@pytest.mark.asyncio
async def test_profile_escalation_protection():
    # 1. Unknown profile name raises ValueError immediately
    with pytest.raises(ValueError) as exc_info:
        resolve_profile("unauthorized_root_god_mode")
    assert "POLICY_DENIED" in str(exc_info.value)

    adapter = HermesWorkerAdapter(workspace_root=r"G:\AI\E-zzio")

    # 2. Researcher profile requesting terminal must be rejected
    with patch("asyncio.create_subprocess_exec") as mock_exec:
        res = await adapter.submit(
            task_id="tsk-esc-01",
            prompt="Attempting terminal under researcher",
            profile=RESEARCHER_PROFILE,
            toolsets=["terminal"],
        )
        assert res.status == "POLICY_DENIED"
        assert res.exit_code == -2
        assert "read-only" in res.stderr or "prohibited" in res.stderr
        mock_exec.assert_not_called()

    # 3. Analyst profile requesting file modification must be rejected
    with patch("asyncio.create_subprocess_exec") as mock_exec2:
        res2 = await adapter.submit(
            task_id="tsk-esc-02",
            prompt="Attempting file write under analyst",
            profile=ANALYST_PROFILE,
            toolsets=["file"],
        )
        assert res2.status == "POLICY_DENIED"
        assert res2.exit_code == -2
        mock_exec2.assert_not_called()


# 24. Security: Operator Protected Workspace Denied
@pytest.mark.asyncio
async def test_security_operator_protected_workspace_denied():
    adapter = HermesWorkerAdapter(workspace_root=r"G:\AI\E-zzio")
    # Submitting Operator targeting the core E-ZZIO repo must fail-closed
    with patch("asyncio.create_subprocess_exec") as mock_exec:
        res = await adapter.submit(
            task_id="tsk-op-core-denied",
            prompt="Write maintenance script",
            profile=OPERATOR_PROFILE,
            workspace_root=r"G:\AI\E-zzio",
        )
        assert res.status == "POLICY_DENIED"
        assert res.exit_code == -2
        assert "protected repository root directly" in res.stderr
        mock_exec.assert_not_called()


# 25. Security: Plugin Installation Denied
@pytest.mark.asyncio
async def test_security_plugin_installation_denied():
    adapter = HermesWorkerAdapter(workspace_root=r"G:\AI\E-zzio")
    with patch("asyncio.create_subprocess_exec") as mock_exec:
        res = await adapter.submit(
            task_id="tsk-plugin-deny",
            prompt="Please run hermes plugin install malicious-ext",
            profile=RESEARCHER_PROFILE,
        )
        assert res.status == "POLICY_DENIED"
        assert res.exit_code == -2
        assert "Plugin installation" in res.stderr or "plugin/MCP" in res.stderr
        mock_exec.assert_not_called()


# 26. Security: Arbitrary MCP Denied
@pytest.mark.asyncio
async def test_security_arbitrary_mcp_denied():
    adapter = HermesWorkerAdapter(workspace_root=r"G:\AI\E-zzio")
    with patch("asyncio.create_subprocess_exec") as mock_exec:
        res = await adapter.submit(
            task_id="tsk-mcp-deny",
            prompt="Please execute mcp connect https://untrusted-remote.org/sse",
            profile=RESEARCHER_PROFILE,
        )
        assert res.status == "POLICY_DENIED"
        assert res.exit_code == -2
        assert "arbitrary MCP" in res.stderr or "plugin/MCP" in res.stderr
        mock_exec.assert_not_called()


# 27. Master Delegates to Researcher Profile
@pytest.mark.asyncio
async def test_master_delegates_to_researcher_profile():
    fake_prov = FakeSynthesisProvider()
    mock_adapter = MagicMock()
    mock_adapter.submit = AsyncMock(return_value=HermesWorkerResult(
        task_id="subtask-researcher-01",
        status="SUCCESS",
        stdout='{"type": "result", "exit_code": 0, "text": "Research synthesis completed."}\n',
        stderr="",
        exit_code=0,
        duration_ms=620,
        output="Research synthesis completed with citations.",
        pid=55112,
        session_id="hermes-research-sess",
        resolved_capabilities={"profile_name": "researcher", "toolsets": ["web", "skills"]},
    ))

    master = EzzioMaster(provider=fake_prov, hermes_adapter=mock_adapter)
    res = await master.orchestrate_multi_agent_mission(
        mission_prompt="Recherche bibliographique sur les architectures agentiques",
        subtask_specs=[
            {
                "task_id": "subtask-researcher-01",
                "role": "researcher",
                "worker": "hermes",
                "prompt": "Recherche les papiers récents sur l'inférence agentique",
            }
        ]
    )

    assert res["ok"] is True
    assert len(res["subtasks"]) == 1
    sub = res["subtasks"][0]
    assert sub["worker"] == "hermes"
    assert sub["role"] == "researcher"
    assert sub["pid"] == 55112
    assert sub["validated"] is True
    call_kwargs = mock_adapter.submit.call_args.kwargs
    assert call_kwargs.get("profile") == RESEARCHER_PROFILE


# 28. Master Delegates to Operator in Sandbox
@pytest.mark.asyncio
async def test_master_delegates_to_operator_in_sandbox():
    import tempfile
    with tempfile.TemporaryDirectory(prefix="ezzio_test_sb_") as tmp_sandbox:
        fake_prov = FakeSynthesisProvider()
        mock_adapter = MagicMock()
        mock_adapter.submit = AsyncMock(return_value=HermesWorkerResult(
            task_id="subtask-operator-01",
            status="SUCCESS",
            stdout='{"type": "result", "exit_code": 0, "text": "File updated in sandbox."}\n',
            stderr="",
            exit_code=0,
            duration_ms=510,
            output="File updated in sandbox.",
            pid=55113,
            session_id="hermes-operator-sess",
            resolved_capabilities={"profile_name": "operator", "toolsets": ["file", "terminal", "skills"]},
        ))

        master = EzzioMaster(provider=fake_prov, hermes_adapter=mock_adapter)
        res = await master.orchestrate_multi_agent_mission(
            mission_prompt="Maintenance dans le sandbox temporaire",
            subtask_specs=[
                {
                    "task_id": "subtask-operator-01",
                    "role": "operator",
                    "worker": "hermes",
                    "workspace_root": tmp_sandbox,
                    "prompt": "Crée un fichier temporaire de test",
                }
            ]
        )

        assert res["ok"] is True
        sub = res["subtasks"][0]
        assert sub["worker"] == "hermes"
        assert sub["role"] == "operator"
        assert sub["pid"] == 55113
        call_kwargs = mock_adapter.submit.call_args.kwargs
        assert call_kwargs.get("profile") == OPERATOR_PROFILE
        assert call_kwargs.get("workspace_root") == tmp_sandbox


# 29. Deferred Profiles Status
def test_deferred_profiles_status():
    coder = resolve_profile("coder")
    assert coder.status == "DEFERRED"
    assert coder.name == WorkerProfileType.CODER
    assert len(coder.hermes_toolsets) == 0

    tester = resolve_profile("tester")
    assert tester.status == "DEFERRED"
    assert tester.name == WorkerProfileType.TESTER
    assert len(tester.hermes_toolsets) == 0


# 30. is_capability_allowed Helper
def test_is_capability_allowed_helper():
    assert is_capability_allowed(RESEARCHER_PROFILE, "web_search") is True
    assert is_capability_allowed(RESEARCHER_PROFILE, "skills_list") is True
    assert is_capability_allowed(RESEARCHER_PROFILE, "terminal") is False
    assert is_capability_allowed(RESEARCHER_PROFILE, "write_file") is False
    assert is_capability_allowed(RESEARCHER_PROFILE, "plugin_install") is False

    assert is_capability_allowed(OPERATOR_PROFILE, "terminal") is True
    assert is_capability_allowed(OPERATOR_PROFILE, "write_file") is True
    assert is_capability_allowed(OPERATOR_PROFILE, "read_file") is True
    assert is_capability_allowed(OPERATOR_PROFILE, "plugin_install") is False

    assert is_capability_allowed(CONTEXT_ONLY_READER, "read_file") is False
    assert is_capability_allowed(CONTEXT_ONLY_READER, "terminal") is False


# 31. Live E2E Researcher Proof
@pytest.mark.asyncio
async def test_live_e2e_researcher_proof():
    adapter = HermesWorkerAdapter(workspace_root=r"G:\AI\E-zzio")
    if not adapter.is_available():
        pytest.skip("Hermes executable not available on host")

    res = await adapter.submit(
        task_id="live-researcher-proof-01",
        prompt="Synthesize in 1 sentence: what is quantum entanglement?",
        profile=RESEARCHER_PROFILE,
        timeout=10,
    )

    assert res.task_id == "live-researcher-proof-01"
    assert res.pid is not None and res.pid > 0
    assert res.exit_code is not None
    assert "--toolsets" in res.command and "web,skills" in res.command
    assert "--skills" in res.command and "grounded-citations" in res.command
    assert res.hermes_home is not None
    assert not os.path.exists(res.hermes_home)
    assert res.resolved_capabilities.get("profile_name") == "researcher"


# 32. Live E2E Operator Proof in Isolated Sandbox
@pytest.mark.asyncio
async def test_live_e2e_operator_proof():
    import tempfile
    with tempfile.TemporaryDirectory(prefix="ezzio_op_live_") as tmp_sandbox:
        adapter = HermesWorkerAdapter(workspace_root=tmp_sandbox)
        if not adapter.is_available():
            pytest.skip("Hermes executable not available on host")

        res = await adapter.submit(
            task_id="live-operator-proof-01",
            prompt="Inspect your current isolated sandbox environment and report status.",
            profile=OPERATOR_PROFILE,
            workspace_root=tmp_sandbox,
            timeout=10,
        )

        assert res.task_id == "live-operator-proof-01"
        assert res.pid is not None and res.pid > 0
        assert res.exit_code is not None
        assert "--toolsets" in res.command and "file,terminal,skills" in res.command
        assert "--in" in res.command and tmp_sandbox in res.command
        assert res.hermes_home is not None
        assert not os.path.exists(res.hermes_home)
        assert res.resolved_capabilities.get("profile_name") == "operator"
