import os

import pytest

from runtime.agent.contracts import AgentStatus, AgentTask
from runtime.agent.loop import AgentLoop
from runtime.agent.state_machine import AgentStateMachine


def test_real_agent_task_execution_read_only_nominal(tmp_path):
    target_dir = tmp_path / "task_workspace"
    target_dir.mkdir()
    sample_file = target_dir / "target.py"
    sample_file.write_text("def task_target(): return 42", encoding="utf-8")

    loop = AgentLoop()
    res = loop.run(f"Observe et analyse {str(sample_file).replace('\\\\', '/')}")

    assert res is not None
    assert res["state"] in ["COMPLETED", "HALTED", "EXECUTING"]
    assert res["ledger_events"] > 0
    assert "task_id" in res

def test_real_agent_task_execution_forbidden_capability_deny():
    loop = AgentLoop()
    # Tâche ciblant un composant protégé
    res = loop.run("runtime/constitution/modify_rules.md")
    assert res["state"] == "HALTED"
    assert "Constitution violation" in res.get("reason", "")
