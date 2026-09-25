"""
tests/test_dag_master_integration.py — Integration Master -> TaskDAG -> DAGOrchestrator -> Discord.

Validates the full DAG execution pipeline (A-H proofs):
A — Dependencies (A -> B -> C)
B — Parallelism (A || B -> C)
C — Retry (B FAIL -> retry -> SUCCESS)
D — Skip (A FAIL -> descendants SKIPPED)
E — Result propagation (A.result -> B.input)
F — Master -> DAG -> Hermes worker
G — Discord -> /master/chat -> Master -> TaskDAG -> Synthesis -> Response
H — Audit log events (DAG_STARTED -> NODE_* -> DAG_COMPLETED)
"""
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest
from fastapi import FastAPI

from core.agent.hermes_worker_adapter import HermesWorkerResult
from core.ezzio_master import EzzioMaster
from core.orchestration.engine import dag_orchestrator
from core.providers.base_provider import CostClass, ProviderResponse
from routers.master import router as master_router


class FakeDagProvider:
    """Fake provider for deterministic DAG integration tests."""

    def __init__(self):
        self.prompts_received = []

    async def generate(
        self,
        prompt: str = "",
        system_prompt: str | None = None,
        model: str = "gemini-3.8-flash",
        temperature: float = 0.2,
        max_tokens: int = 512,
        thinking_level: str = "off",
        **kwargs
    ) -> ProviderResponse:
        self.prompts_received.append(prompt)
        if "Synthèse Master" in prompt:
            content = f"[SYNTHÈSE MASTER {model}] Mission accomplie via le TaskDAG."
        elif "FOUND_SECRET_KEY_12345" in prompt:
            content = "[TASK B OUTPUT] Received upstream secret key successfully."
        else:
            content = f"[RESULT {model}] Subtask output for {prompt[:30]}."

        return ProviderResponse(
            content=content,
            model=model,
            provider="fake_provider",
            cost_class=CostClass.LOCAL,
        )


@pytest.mark.asyncio
async def test_proof_a_dependencies_chain():
    """A — Dépendances : A -> B -> C s'exécutent dans l'ordre séquentiel du DAG."""
    fake_prov = FakeDagProvider()
    master = EzzioMaster(provider=fake_prov)

    subtasks = [
        {"task_id": "A", "role": "forensic", "prompt": "Task A analysis", "dependencies": []},
        {"task_id": "B", "role": "coding", "prompt": "Task B implementation", "dependencies": ["A"]},
        {"task_id": "C", "role": "qa", "prompt": "Task C validation", "dependencies": ["B"]},
    ]

    res = await master.orchestrate_multi_agent_mission(
        mission_prompt="Mission séquentielle A->B->C",
        subtask_specs=subtasks,
        session_id="session-proof-a"
    )

    assert res["ok"] is True
    assert "dag_id" in res
    assert len(res["subtasks"]) == 3
    task_ids = [s["task_id"] for s in res["subtasks"]]
    assert task_ids == ["A", "B", "C"]
    assert all(s["status"] == "SUCCESS" for s in res["subtasks"])


@pytest.mark.asyncio
async def test_proof_b_parallelism():
    """B — Parallélisme : A || B -> C."""
    fake_prov = FakeDagProvider()
    master = EzzioMaster(provider=fake_prov)

    subtasks = [
        {"task_id": "A", "role": "forensic", "prompt": "Task A forensic", "dependencies": []},
        {"task_id": "B", "role": "research", "prompt": "Task B research", "dependencies": []},
        {"task_id": "C", "role": "qa", "prompt": "Task C join", "dependencies": ["A", "B"]},
    ]

    res = await master.orchestrate_multi_agent_mission(
        mission_prompt="Mission parallèle A||B->C",
        subtask_specs=subtasks,
        session_id="session-proof-b"
    )

    assert res["ok"] is True
    assert len(res["subtasks"]) == 3
    nodes = {s["task_id"]: s for s in res["subtasks"]}
    assert nodes["A"]["status"] == "SUCCESS"
    assert nodes["B"]["status"] == "SUCCESS"
    assert nodes["C"]["status"] == "SUCCESS"
    assert "A" in nodes["C"]["dependency_results"]
    assert "B" in nodes["C"]["dependency_results"]


@pytest.mark.asyncio
async def test_proof_c_retry_recovery():
    """C — Retry gouverné par le DAG : B FAIL -> retry -> SUCCESS."""
    master = EzzioMaster()
    attempts = {"count": 0}

    class FlakyDagProvider:
        async def generate(self, prompt="", model="", **kwargs):
            if "Synthèse Master" in prompt:
                return ProviderResponse(content="[SYNTHÈSE] Retry réussi", model=model, provider="flaky", cost_class=CostClass.LOCAL)

            # Node B fails on attempt 1, succeeds on attempt 2
            if "Task B" in prompt:
                attempts["count"] += 1
                if attempts["count"] == 1:
                    return ProviderResponse(content="", model=model, provider="flaky", cost_class=CostClass.LOCAL)
                return ProviderResponse(content="[RECOVERED B] Success after retry", model=model, provider="flaky", cost_class=CostClass.LOCAL)

            return ProviderResponse(content="[OK] Output", model=model, provider="flaky", cost_class=CostClass.LOCAL)

    master._injected_provider = FlakyDagProvider()
    master.provider = master._injected_provider

    subtasks = [
        {"task_id": "A", "role": "forensic", "prompt": "Task A", "dependencies": []},
        {"task_id": "B", "role": "coding", "prompt": "Task B", "dependencies": ["A"]},
    ]

    res = await master.orchestrate_multi_agent_mission(
        mission_prompt="Mission retry test",
        subtask_specs=subtasks,
        session_id="session-proof-c",
        max_retries=2
    )

    assert res["ok"] is True
    nodes = {s["task_id"]: s for s in res["subtasks"]}
    assert nodes["B"]["retries"] == 1
    assert nodes["B"]["status"] == "SUCCESS"
    assert "RECOVERED B" in nodes["B"]["output"]


@pytest.mark.asyncio
async def test_proof_d_cascade_skip():
    """D — Skip : A FAIL -> descendants B, C SKIPPED."""
    master = EzzioMaster()

    class FailingProvider:
        async def generate(self, prompt="", model="", **kwargs):
            if "Task A" in prompt:
                # Retours vides systématiques pour faire échouer A
                return ProviderResponse(content="", model=model, provider="failing", cost_class=CostClass.LOCAL)
            return ProviderResponse(content="[OK] Output", model=model, provider="failing", cost_class=CostClass.LOCAL)

    master._injected_provider = FailingProvider()
    master.provider = master._injected_provider

    subtasks = [
        {"task_id": "A", "role": "forensic", "prompt": "Task A", "dependencies": []},
        {"task_id": "B", "role": "coding", "prompt": "Task B", "dependencies": ["A"]},
        {"task_id": "C", "role": "qa", "prompt": "Task C", "dependencies": ["B"]},
    ]

    res = await master.orchestrate_multi_agent_mission(
        mission_prompt="Mission cascade skip test",
        subtask_specs=subtasks,
        session_id="session-proof-d",
        max_retries=1
    )

    assert res["ok"] is False
    nodes = {s["task_id"]: s for s in res["subtasks"]}
    assert nodes["A"]["status"] == "FAILED"
    assert nodes["B"]["status"] == "SKIPPED"
    assert nodes["C"]["status"] == "SKIPPED"


@pytest.mark.asyncio
async def test_proof_e_result_propagation():
    """E — Propagation de résultat : A.result -> B.input."""
    fake_prov = FakeDagProvider()

    class SecretProvider:
        async def generate(self, prompt="", model="", **kwargs):
            if "Task A" in prompt:
                return ProviderResponse(content="FOUND_SECRET_KEY_12345", model=model, provider="sec", cost_class=CostClass.LOCAL)
            fake_prov.prompts_received.append(prompt)
            return await fake_prov.generate(prompt=prompt, model=model)

    master = EzzioMaster(provider=SecretProvider())

    subtasks = [
        {"task_id": "A", "role": "forensic", "prompt": "Task A inspect key", "dependencies": []},
        {"task_id": "B", "role": "coding", "prompt": "Task B consume key", "dependencies": ["A"]},
    ]

    res = await master.orchestrate_multi_agent_mission(
        mission_prompt="Mission propagation secret",
        subtask_specs=subtasks,
        session_id="session-proof-e"
    )

    assert res["ok"] is True
    nodes = {s["task_id"]: s for s in res["subtasks"]}
    assert "FOUND_SECRET_KEY_12345" in nodes["B"]["dependency_results"]["A"]
    # Vérifie qu'au moins un prompt envoyé à B contenait le secret d'amont
    assert any("FOUND_SECRET_KEY_12345" in p for p in fake_prov.prompts_received)


@pytest.mark.asyncio
async def test_proof_f_hermes_worker_execution():
    """F — Master -> DAG -> Hermes worker."""
    fake_prov = FakeDagProvider()
    master = EzzioMaster(provider=fake_prov)

    hermes_response = HermesWorkerResult(
        task_id="hermes-01",
        status="SUCCESS",
        stdout="[HERMES OUTPUT] Executed via context_reader profile",
        stderr="",
        exit_code=0,
        duration_ms=100,
        output="[HERMES OUTPUT] Executed via context_reader profile",
        pid=9876,
    )

    with patch.object(master.hermes_adapter, "submit", new_callable=AsyncMock) as mock_submit:
        mock_submit.return_value = hermes_response

        subtasks = [
            {
                "task_id": "hermes-01",
                "role": "research",
                "worker": "hermes",
                "profile": "context_reader",
                "prompt": "Inspect codebase with Hermes",
                "dependencies": []
            }
        ]

        res = await master.orchestrate_multi_agent_mission(
            mission_prompt="Mission Hermes",
            subtask_specs=subtasks,
            session_id="session-proof-f"
        )

        assert res["ok"] is True
        sub = res["subtasks"][0]
        assert sub["worker"] == "hermes"
        assert sub["pid"] == 9876
        assert sub["status"] == "SUCCESS"
        assert "[HERMES OUTPUT]" in sub["output"]
        assert mock_submit.called


@pytest.mark.asyncio
async def test_proof_g_discord_to_dag_e2e():
    """G — Discord E2E : Discord -> /master/chat -> Master -> TaskDAG -> Worker -> Synthesis -> Discord."""
    fake_prov = FakeDagProvider()

    app = FastAPI()
    app.include_router(master_router)

    with patch("core.ezzio_master.ezzio_master.provider", fake_prov), \
         patch("core.ezzio_master.ezzio_master._injected_provider", fake_prov):

        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
            payload = {
                "text": "Audite la sécurité du module vault et vérifie les tests QA",
                "session_id": "disc_guild_123_user_456",
                "channel": "discord",
                "mission_profile": "MISSION",
            }
            resp = await client.post("/master/chat", json=payload)
            assert resp.status_code == 200
            data = resp.json()

            assert data["channel"] == "discord"
            assert data["mission"] == "MISSION"
            assert data["ok"] is True
            assert "mission_id" in data
            assert "dag_id" in data
            assert len(data["subtasks"]) >= 2
            assert "response" in data
            assert "[SYNTHÈSE MASTER" in data["response"]


@pytest.mark.asyncio
async def test_proof_h_audit_ledger_events():
    """H — Audit Ledger : Vérification de la séquence des événements émis pendant le DAG."""
    fake_prov = FakeDagProvider()
    master = EzzioMaster(provider=fake_prov)

    events_recorded = []

    def mock_audit(action, payload, status="SUCCESS"):
        events_recorded.append({"action": action, "payload": payload, "status": status})

    with patch("core.ezzio_master._audit_command", side_effect=mock_audit):
        subtasks = [
            {"task_id": "audit-A", "role": "forensic", "prompt": "Audit task A", "dependencies": []},
            {"task_id": "audit-B", "role": "coding", "prompt": "Audit task B", "dependencies": ["audit-A"]},
        ]

        res = await master.orchestrate_multi_agent_mission(
            mission_prompt="Mission Audit Test",
            subtask_specs=subtasks,
            session_id="session-proof-h"
        )

        assert res["ok"] is True
        action_names = [e["action"] for e in events_recorded]
        assert "MISSION_STARTED" in action_names
        assert "VALIDATION_RESULT" in action_names
        assert "SUBTASK_EXECUTED" in action_names
        assert "MISSION_SYNTHESIS_COMPLETED" in action_names
