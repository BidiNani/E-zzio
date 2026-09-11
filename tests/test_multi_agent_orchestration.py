"""
tests/test_multi_agent_orchestration.py — Deterministic test for multi-agent delegation & synthesis
"""
import pytest
import asyncio
from core.ezzio_master import EzzioMaster

@pytest.mark.asyncio
async def test_multi_agent_delegation_flow():
    master = EzzioMaster()

    mission_prompt = "Mission d'analyse de sécurité et correctif du module vault"
    
    # 2 sous-tâches explicites avec des rôles distincts (FORENSIC et CODING)
    subtasks = [
        {"task_id": "sub-01", "role": "forensic", "prompt": "Audit des vulnérabilités vault", "complexity": 0.6},
        {"task_id": "sub-02", "role": "coding", "prompt": "Correctif de code vault", "complexity": 0.7}
    ]

    res = await master.orchestrate_multi_agent_mission(
        mission_prompt=mission_prompt,
        subtask_specs=subtasks,
        session_id="test-multi-agent-session",
        channel="web"
    )

    assert res["ok"] is True
    assert res["master_model"] == "gemini-3.8-flash"
    assert len(res["subtasks"]) == 2

    # Vérification des sous-tâches et rôles affectés par le ModelRouter
    sub_forensic = res["subtasks"][0]
    sub_coding = res["subtasks"][1]

    assert sub_forensic["role"] == "forensic"
    assert sub_forensic["model"] == "gemini-3.6-flash"
    assert sub_forensic["thinking_level"] == "medium"

    assert sub_coding["role"] == "coding"
    assert sub_coding["model"] == "gemini-3.7-flash"
    assert sub_coding["thinking_level"] == "low"

    # Vérification de la synthèse Master
    assert res["synthesis"] is not None
    assert len(res["synthesis"]) > 0

if __name__ == "__main__":
    asyncio.run(test_multi_agent_delegation_flow())
    print("✅ MULTI-AGENT DELEGATION TEST PASSED")
