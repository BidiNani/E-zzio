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


# 1. Command construction & toolsets boundary
def test_hermes_command_construction():
    adapter = HermesWorkerAdapter(workspace_root=r"G:\AI\E-zzio", hermes_bin=r"G:\Hermes\bin\hermes.exe")
    cmd = adapter.build_cli_command(
        prompt="Inspect repository structure",
        model="qwen3.5:9b",
        provider="ollama",
        safe_mode=True,
    )
    assert r"G:\Hermes\bin\hermes.exe" in cmd[0]
    assert cmd[1] == "chat"
    assert "-q" in cmd
    assert "Inspect repository structure" in cmd
    assert "--format" in cmd and "stream-json" in cmd
    assert "--oneshot" in cmd
    assert "-Q" in cmd
    assert "--ignore-rules" in cmd
    assert "--source" in cmd and "tool" in cmd
    assert "--safe-mode" in cmd
    assert "--in" in cmd and r"G:\AI\E-zzio" in cmd
    assert "-m" in cmd and "qwen3.5:9b" in cmd
    assert "--provider" in cmd and "ollama" in cmd
    assert "--toolsets" in cmd and "file" in cmd
    # Ensure default toolsets do not expose dangerous tools
    assert "terminal" not in cmd
    assert "code_execution" not in cmd
    assert "process" not in cmd
    assert "delegation" not in cmd
    assert "memory" not in cmd


def test_worker_toolsets_boundary_definitions():
    assert "file" in DEFAULT_WORKER_TOOLSETS
    for forbidden in ["terminal", "code_execution", "process", "delegation", "memory", "session_search", "browser"]:
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
        assert "Forbidden toolsets requested" in result.stderr
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
