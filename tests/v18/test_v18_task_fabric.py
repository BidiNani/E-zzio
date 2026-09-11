import pytest
from v18.fabric.models import SubtaskNode, SubtaskState, MissionRecord
from v18.evidence.engine import global_evidence_vault, FactCertainty
from v18.agents.coordinator import agent_coordinator

def test_v18_evidence_and_agent_coordination():
    st = SubtaskNode(subtask_id="st_1", parent_mission_id="m_1", role="ANALYST", task_type="FORENSIC")
    res = agent_coordinator.execute_subtask(st)
    assert res.state == SubtaskState.COMPLETED
    assert res.evidence_id is not None
    ev = global_evidence_vault.get_evidence(res.evidence_id)
    assert ev.certainty == FactCertainty.VERIFIED_FACT
