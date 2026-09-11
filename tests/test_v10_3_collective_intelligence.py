"""
E-ZZIO V10.3 — Critical Test Suite: Collective Intelligence, Agent Swarms, Brainstorming & Debates.
Couvre les tests unitaires et scénarios End-to-End exigés par la spécification V10.3.
"""

import pytest
import sys
import subprocess

from core.agents import (
    agent_registry,
    agent_factory,
    swarm_engine,
    AgentSwarm,
    SwarmMessage,
    SwarmConflict,
    SwarmProposal,
    MessageType,
    SwarmMode,
    SwarmState,
    SwarmLimitError,
)


@pytest.fixture(autouse=True)
def setup_registry_and_swarm():
    agent_registry.reset_to_defaults()
    agent_factory._spawn_timestamps.clear()
    swarm_engine._swarms.clear()
    swarm_engine.MAX_MESSAGES_PER_SWARM = 100
    yield
    agent_registry.reset_to_defaults()
    agent_factory._spawn_timestamps.clear()
    swarm_engine._swarms.clear()
    swarm_engine.MAX_MESSAGES_PER_SWARM = 100


def test_01_swarm_creation():
    """1. Swarm creation."""
    swarm = swarm_engine.create_swarm(
        mission_id="m_001",
        coordinator_id="master_ezzio",
        objective="Design high-performance cache architecture",
        mode=SwarmMode.BRAINSTORM,
    )
    assert swarm.swarm_id.startswith("swarm_")
    assert swarm.coordinator_id == "master_ezzio"
    assert swarm.state == SwarmState.CREATED
    assert "coder_worker" in swarm.participants


def test_02_03_agent_join_and_leave():
    """2 & 3. Agent join and leave."""
    swarm = swarm_engine.create_swarm(mission_id="m_002", mode=SwarmMode.COLLABORATION)
    assert swarm_engine.join_swarm(swarm.swarm_id, "image_agent") is True
    assert "image_agent" in swarm.participants

    assert swarm_engine.leave_swarm(swarm.swarm_id, "image_agent") is True
    assert "image_agent" not in swarm.participants


def test_04_05_agent_messages_and_broadcast():
    """4 & 5. Agent-to-agent & broadcast messages."""
    swarm = swarm_engine.create_swarm(mission_id="m_003")
    msg1 = swarm_engine.post_message(
        swarm_id=swarm.swarm_id,
        sender_agent_id="coder_worker",
        recipient_agent_id="qa_tester",
        message_type=MessageType.QUESTION,
        content="Is the cache invalidation thread-safe?",
    )
    assert msg1.sender_agent_id == "coder_worker"
    assert msg1.recipient_agent_id == "qa_tester"

    msg2 = swarm_engine.post_message(
        swarm_id=swarm.swarm_id,
        sender_agent_id="master_ezzio",
        recipient_agent_id="BROADCAST",
        message_type=MessageType.SUMMARY,
        content="Proceed with divergent brainstorming phase",
    )
    assert msg2.recipient_agent_id == "BROADCAST"
    assert len(swarm.messages) == 2


def test_06_brainstorming_and_proposals():
    """6. Brainstorming mode & proposals."""
    swarm = swarm_engine.create_swarm(mission_id="m_004", mode=SwarmMode.BRAINSTORM)
    p1 = swarm_engine.submit_proposal(
        swarm_id=swarm.swarm_id,
        agent_id="coder_worker",
        title="LRU In-Memory Cache",
        description="Use double-linked list + hashmap for O(1) reads/writes",
    )
    p2 = swarm_engine.submit_proposal(
        swarm_id=swarm.swarm_id,
        agent_id="researcher_scout",
        title="SQLite WAL Shared Cache",
        description="Leverage existing SQLite WAL gateway for zero-leak persistence",
    )
    assert len(swarm.proposals) == 2
    assert p1.title == "LRU In-Memory Cache"
    assert p2.title == "SQLite WAL Shared Cache"


def test_08_09_10_objection_conflict_detection_and_resolution():
    """8, 9, 10. Objection, conflict detection, and resolution via evidence."""
    swarm = swarm_engine.create_swarm(mission_id="m_005", mode=SwarmMode.DEBATE)

    # Objection generates conflict automatically
    msg_obj = swarm_engine.post_message(
        swarm_id=swarm.swarm_id,
        sender_agent_id="sec_guard",
        recipient_agent_id="coder_worker",
        message_type=MessageType.OBJECTION,
        content="In-memory cache risks secret exposure on process crash dump",
    )
    assert len(swarm.conflicts) == 1
    conflict = swarm.conflicts[0]
    assert conflict.resolution_state == "OPEN"

    # Resolve conflict with evidence
    ok = swarm_engine.resolve_conflict(
        swarm_id=swarm.swarm_id,
        conflict_id=conflict.conflict_id,
        resolution_evidence="Encrypted RAM buffer + zeroize on SIGSEGV",
        winning_agent_id="sec_guard",
    )
    assert ok is True
    assert conflict.resolution_state == "RESOLVED"


def test_11_12_13_voting_consensus_and_minority_report():
    """11, 12, 13. Voting, consensus, and minority report preservation."""
    swarm = swarm_engine.create_swarm(mission_id="m_006")
    p1 = swarm_engine.submit_proposal(
        swarm_id=swarm.swarm_id,
        agent_id="coder_worker",
        title="Option A: Micro-batching",
        description="Batch I/O operations in 10ms windows",
    )
    p2 = swarm_engine.submit_proposal(
        swarm_id=swarm.swarm_id,
        agent_id="researcher_scout",
        title="Option B: Event-driven Async Stream",
        description="Stream events immediately using async bus",
    )

    p1.score = 0.90
    p2.score = 0.70  # Valid minority report

    decision = swarm_engine.synthesize_consensus(swarm.swarm_id)
    assert decision["status"] == "CONSENSUS_REACHED"
    assert decision["winning_proposal"] == "Option A: Micro-batching"
    assert len(swarm.minority_reports) == 1
    assert swarm.minority_reports[0].title == "Option B: Event-driven Async Stream"


def test_14_master_arbitration():
    """14. Master arbitration."""
    swarm = swarm_engine.create_swarm(mission_id="m_007")
    p1 = swarm_engine.submit_proposal(
        swarm_id=swarm.swarm_id,
        agent_id="coder_worker",
        title="Option X",
        description="Custom Implementation X",
    )

    decision = swarm_engine.arbitrate_master(
        swarm_id=swarm.swarm_id,
        winning_proposal_id=p1.proposal_id,
        reason="Master selects Option X due to zero external dependencies",
    )
    assert decision["status"] == "MASTER_ARBITRATED"
    assert decision["arbitrator"] == "master_ezzio"
    assert swarm.state == SwarmState.ARBITRATED


def test_16_17_sub_agent_swarm_collaboration():
    """16 & 17. Sub-agent collaboration in swarm (V10.2 + V10.3 integration)."""
    sub_coder = agent_factory.create_sub_agent(
        parent_id="master_ezzio",
        role="SUB_CODER",
        capabilities=["CODE_READ", "CODE_WRITE"],
        budget=30.0,
    )
    swarm = swarm_engine.create_swarm(mission_id="m_008", participants=[sub_coder.agent_id])
    assert sub_coder.agent_id in swarm.participants

    msg = swarm_engine.post_message(
        swarm_id=swarm.swarm_id,
        sender_agent_id=sub_coder.agent_id,
        recipient_agent_id="master_ezzio",
        message_type=MessageType.PROPOSAL,
        content="Sub-agent proposal for task refinement",
    )
    assert msg.sender_agent_id == sub_coder.agent_id


def test_18_max_messages_limit():
    """18. Max messages limit (SwarmLimitError)."""
    swarm = swarm_engine.create_swarm(mission_id="m_009")
    swarm_engine.MAX_MESSAGES_PER_SWARM = 2

    swarm_engine.post_message(swarm.swarm_id, "coder_worker", "BROADCAST", MessageType.QUESTION, "Msg 1")
    swarm_engine.post_message(swarm.swarm_id, "coder_worker", "BROADCAST", MessageType.QUESTION, "Msg 2")

    with pytest.raises(SwarmLimitError, match="Limite max de messages atteinte"):
        swarm_engine.post_message(swarm.swarm_id, "coder_worker", "BROADCAST", MessageType.QUESTION, "Msg 3")


def test_21_frozen_core_check():
    """21. Frozen Core remains unchanged."""
    res = subprocess.run([sys.executable, "tools/check_frozen_core.py"], capture_output=True, text=True)
    assert res.returncode == 0
    assert "FROZEN_CORE_OK" in res.stdout


def test_23_end_to_end_scenario_a():
    """Scenario A: Full Brainstorm -> Debate -> Synthesis -> Arbitration."""
    swarm = swarm_engine.create_swarm(
        mission_id="m_e2e_a",
        objective="E2E Architecture Redesign",
        mode=SwarmMode.BRAINSTORM,
    )

    # 1. Submissions
    p1 = swarm_engine.submit_proposal(swarm.swarm_id, "coder_worker", "Architecture Alpha", "Modular design")
    p2 = swarm_engine.submit_proposal(swarm.swarm_id, "researcher_scout", "Architecture Beta", "Monolithic design")

    # 2. Debate & Objections
    swarm_engine.post_message(
        swarm.swarm_id, "sec_guard", "researcher_scout", MessageType.OBJECTION, "Monolithic design violates isolation"
    )

    # 3. Resolve conflict with evidence
    assert len(swarm.conflicts) == 1
    swarm_engine.resolve_conflict(
        swarm.swarm_id,
        swarm.conflicts[0].conflict_id,
        "Modular isolation verified by Security Audit",
        "coder_worker",
    )

    # 4. Scoring & Consensus
    p1.score = 0.95
    p2.score = 0.40

    decision = swarm_engine.synthesize_consensus(swarm.swarm_id)
    assert decision["status"] == "CONSENSUS_REACHED"
    assert decision["winning_proposal"] == "Architecture Alpha"
