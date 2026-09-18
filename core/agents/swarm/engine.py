"""
E-ZZIO Core V10.3 — Collective Intelligence & Governed Agent Swarm Engine.
Gère les brainstormings multi-agents, discussions inter-agents, débats contradictoires,
détection de conflits, résolutions basées sur les preuves, consensus et arbitrage Master.
"""
from __future__ import annotations

import logging
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from core.agents.registry import (
    AgentRegistry,
    agent_registry,
)

logger = logging.getLogger("ezzio.agents.swarm")


class MessageType(str, Enum):
    QUESTION = "QUESTION"
    PROPOSAL = "PROPOSAL"
    OBJECTION = "OBJECTION"
    COUNTER_ARGUMENT = "COUNTER_ARGUMENT"
    EVIDENCE = "EVIDENCE"
    CLARIFICATION = "CLARIFICATION"
    ALTERNATIVE = "ALTERNATIVE"
    VOTE = "VOTE"
    CONCESSION = "CONCESSION"
    SUMMARY = "SUMMARY"
    FINAL_POSITION = "FINAL_POSITION"


class SwarmMode(str, Enum):
    BRAINSTORM = "BRAINSTORM"
    DEBATE = "DEBATE"
    COLLABORATION = "COLLABORATION"
    CROSS_EXAMINATION = "CROSS_EXAMINATION"


class SwarmState(str, Enum):
    CREATED = "CREATED"
    ACTIVE = "ACTIVE"
    BRAINSTORMING = "BRAINSTORMING"
    DEBATING = "DEBATING"
    SYNTHESIZING = "SYNTHESIZING"
    CONSENSUS_REACHED = "CONSENSUS_REACHED"
    ARBITRATED = "ARBITRATED"
    ABORTED = "ABORTED"
    COMPLETED = "COMPLETED"


@dataclass
class SwarmMessage:
    message_id: str
    mission_id: str
    swarm_id: str
    sender_agent_id: str
    recipient_agent_id: str  # "BROADCAST" ou agent_id spécifique
    message_type: MessageType
    content: str
    timestamp: float = field(default_factory=time.time)
    parent_message_id: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class SwarmConflict:
    conflict_id: str
    mission_id: str
    swarm_id: str
    participants: list[str]
    claims: dict[str, str]  # agent_id -> claim
    severity: str = "MEDIUM"  # LOW, MEDIUM, HIGH, CRITICAL
    evidence: list[str] = field(default_factory=list)
    resolution_state: str = "OPEN"  # OPEN, RESOLVED, ARBITRATED
    resolution: str | None = None


@dataclass
class SwarmProposal:
    proposal_id: str
    agent_id: str
    title: str
    description: str
    score: float = 0.0
    objections: list[str] = field(default_factory=list)
    evidence: list[str] = field(default_factory=list)
    is_minority_report: bool = False


@dataclass
class AgentSwarm:
    swarm_id: str
    mission_id: str
    coordinator_id: str
    participants: set[str]
    mode: SwarmMode
    state: SwarmState
    objective: str
    budget: float = 50.0
    budget_used: float = 0.0
    max_rounds: int = 5
    current_round: int = 0
    messages: list[SwarmMessage] = field(default_factory=list)
    proposals: list[SwarmProposal] = field(default_factory=list)
    conflicts: list[SwarmConflict] = field(default_factory=list)
    minority_reports: list[SwarmProposal] = field(default_factory=list)
    decision: dict[str, Any] | None = None


class SwarmLimitError(Exception):
    """Exception levée en cas de dépassement des limites du Swarm (budget, rounds)."""
    pass


class SwarmEngine:
    """Moteur souverain d'intelligence collective et de swarming d'agents."""

    MAX_MESSAGES_PER_SWARM = 100

    def __init__(self, registry: AgentRegistry | None = None):
        self.registry = registry or agent_registry
        self._swarms: dict[str, AgentSwarm] = {}

    def create_swarm(
        self,
        mission_id: str,
        coordinator_id: str = "master_ezzio",
        participants: list[str] | None = None,
        objective: str = "Collective problem solving",
        mode: SwarmMode = SwarmMode.BRAINSTORM,
        budget: float = 50.0,
        max_rounds: int = 5,
    ) -> AgentSwarm:
        """Crée un nouvel Agent Swarm gouverné."""
        swarm_id = f"swarm_{uuid.uuid4().hex[:8]}"
        initial_participants = set(participants or ["master_ezzio", "coder_worker", "researcher_scout", "qa_tester", "sec_guard"])
        initial_participants.add(coordinator_id)

        swarm = AgentSwarm(
            swarm_id=swarm_id,
            mission_id=mission_id,
            coordinator_id=coordinator_id,
            participants=initial_participants,
            mode=mode,
            state=SwarmState.CREATED,
            objective=objective,
            budget=budget,
            max_rounds=max_rounds,
        )
        self._swarms[swarm_id] = swarm
        logger.info(f"[SWARM-ENGINE] Swarm créé: {swarm_id} ({mode.value}, {len(initial_participants)} participants)")
        return swarm

    def get_swarm(self, swarm_id: str) -> AgentSwarm | None:
        return self._swarms.get(swarm_id)

    def join_swarm(self, swarm_id: str, agent_id: str) -> bool:
        swarm = self._swarms.get(swarm_id)
        if not swarm:
            return False
        swarm.participants.add(agent_id)
        logger.info(f"[SWARM-ENGINE] Agent {agent_id} rejoint le swarm {swarm_id}")
        return True

    def leave_swarm(self, swarm_id: str, agent_id: str) -> bool:
        swarm = self._swarms.get(swarm_id)
        if not swarm or agent_id not in swarm.participants:
            return False
        swarm.participants.remove(agent_id)
        logger.info(f"[SWARM-ENGINE] Agent {agent_id} quitte le swarm {swarm_id}")
        return True

    def post_message(
        self,
        swarm_id: str,
        sender_agent_id: str,
        recipient_agent_id: str,
        message_type: MessageType,
        content: str,
        parent_message_id: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> SwarmMessage:
        """Envoie un message gouverné au sein du Swarm."""
        swarm = self._swarms.get(swarm_id)
        if not swarm:
            raise ValueError(f"Swarm introuvable: '{swarm_id}'")

        if sender_agent_id not in swarm.participants:
            raise ValueError(f"Agent '{sender_agent_id}' n'est pas participant au Swarm '{swarm_id}'")

        if len(swarm.messages) >= self.MAX_MESSAGES_PER_SWARM:
            raise SwarmLimitError(f"Limite max de messages atteinte pour le Swarm {swarm_id}")

        msg_id = f"msg_{uuid.uuid4().hex[:8]}"
        msg = SwarmMessage(
            message_id=msg_id,
            mission_id=swarm.mission_id,
            swarm_id=swarm_id,
            sender_agent_id=sender_agent_id,
            recipient_agent_id=recipient_agent_id,
            message_type=message_type,
            content=content,
            parent_message_id=parent_message_id,
            metadata=metadata or {},
        )
        swarm.messages.append(msg)
        swarm.budget_used += 0.5  # coût nominal par message

        # Détection automatique de conflit sur objection
        if message_type == MessageType.OBJECTION:
            self._register_conflict_from_objection(swarm, msg)

        return msg

    def _register_conflict_from_objection(self, swarm: AgentSwarm, msg: SwarmMessage) -> None:
        conflict_id = f"conflict_{uuid.uuid4().hex[:6]}"
        conflict = SwarmConflict(
            conflict_id=conflict_id,
            mission_id=swarm.mission_id,
            swarm_id=swarm.swarm_id,
            participants=[msg.sender_agent_id, msg.recipient_agent_id],
            claims={msg.sender_agent_id: msg.content},
            severity="MEDIUM",
        )
        swarm.conflicts.append(conflict)

    def submit_proposal(
        self,
        swarm_id: str,
        agent_id: str,
        title: str,
        description: str,
        evidence: list[str] | None = None,
    ) -> SwarmProposal:
        swarm = self._swarms.get(swarm_id)
        if not swarm:
            raise ValueError(f"Swarm introuvable: '{swarm_id}'")

        prop_id = f"prop_{uuid.uuid4().hex[:6]}"
        proposal = SwarmProposal(
            proposal_id=prop_id,
            agent_id=agent_id,
            title=title,
            description=description,
            evidence=evidence or [],
        )
        swarm.proposals.append(proposal)
        self.post_message(
            swarm_id=swarm_id,
            sender_agent_id=agent_id,
            recipient_agent_id="BROADCAST",
            message_type=MessageType.PROPOSAL,
            content=f"PROPOSAL [{title}]: {description}",
        )
        return proposal

    def resolve_conflict(
        self,
        swarm_id: str,
        conflict_id: str,
        resolution_evidence: str,
        winning_agent_id: str,
    ) -> bool:
        swarm = self._swarms.get(swarm_id)
        if not swarm:
            return False

        for c in swarm.conflicts:
            if c.conflict_id == conflict_id:
                c.resolution_state = "RESOLVED"
                c.resolution = f"Resolved in favor of {winning_agent_id} based on evidence: {resolution_evidence}"
                c.evidence.append(resolution_evidence)
                self.post_message(
                    swarm_id=swarm_id,
                    sender_agent_id="master_ezzio",
                    recipient_agent_id="BROADCAST",
                    message_type=MessageType.EVIDENCE,
                    content=f"CONFLICT RESOLVED [{conflict_id}]: {c.resolution}",
                )
                return True
        return False

    def synthesize_consensus(self, swarm_id: str) -> dict[str, Any]:
        """Fait la synthèse et vérifie si le consensus est atteint."""
        swarm = self._swarms.get(swarm_id)
        if not swarm:
            raise ValueError(f"Swarm introuvable: '{swarm_id}'")

        swarm.state = SwarmState.SYNTHESIZING
        open_conflicts = [c for c in swarm.conflicts if c.resolution_state == "OPEN"]

        if not open_conflicts and swarm.proposals:
            best_proposal = max(swarm.proposals, key=lambda p: p.score)
            swarm.state = SwarmState.CONSENSUS_REACHED
            swarm.decision = {
                "status": "CONSENSUS_REACHED",
                "winning_proposal": best_proposal.title,
                "author": best_proposal.agent_id,
                "score": best_proposal.score,
                "proposals_count": len(swarm.proposals),
            }

            # Identifier les minority reports (score crédible mais non gagnant)
            for p in swarm.proposals:
                if p != best_proposal and p.score >= 0.5:
                    p.is_minority_report = True
                    swarm.minority_reports.append(p)

        else:
            swarm.state = SwarmState.ARBITRATED
            swarm.decision = {
                "status": "REQUIRES_ARBITRATION",
                "open_conflicts": len(open_conflicts),
                "proposals_count": len(swarm.proposals),
            }

        return swarm.decision

    def arbitrate_master(self, swarm_id: str, winning_proposal_id: str, reason: str) -> dict[str, Any]:
        """Arbitrage souverain du Master E-ZZIO."""
        swarm = self._swarms.get(swarm_id)
        if not swarm:
            raise ValueError(f"Swarm introuvable: '{swarm_id}'")

        target_prop = next((p for p in swarm.proposals if p.proposal_id == winning_proposal_id), None)
        swarm.state = SwarmState.ARBITRATED
        swarm.decision = {
            "status": "MASTER_ARBITRATED",
            "winning_proposal_id": winning_proposal_id,
            "title": target_prop.title if target_prop else "Master Custom Direct",
            "arbitrator": "master_ezzio",
            "reason": reason,
        }
        self.post_message(
            swarm_id=swarm_id,
            sender_agent_id="master_ezzio",
            recipient_agent_id="BROADCAST",
            message_type=MessageType.FINAL_POSITION,
            content=f"MASTER ARBITRATION: {reason}",
        )
        return swarm.decision


swarm_engine = SwarmEngine()
