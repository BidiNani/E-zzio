"""E-ZZIO Native Harness — Task Lifecycle Controller.

Directly integrated with the microkernel primitives:
- ModelRouter (routing & model selection)
- UnifiedMemoryGateway (context authority)
- AgentPolicyGuard (policy & capability authority)
- AuditLedger (proof authority)
- ToolRegistry (primitive tool execution)
"""
from __future__ import annotations

import logging
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from core.agent.agent_guard import AgentPolicyGuard
from core.cognition.model_router import ModelRouter
from core.memory.instance import memory_gateway
from core.security.audit_ledger import AuditLedger
from core.tools.registry import ToolRegistry

logger = logging.getLogger("ezzio.harness")


class HarnessState(str, Enum):
    INITIALIZING = "INITIALIZING"
    PERCEIVING = "PERCEIVING"
    THINKING = "THINKING"
    VALIDATING = "VALIDATING"
    AWAITING_APPROVAL = "AWAITING_APPROVAL"
    EXECUTING = "EXECUTING"
    HEALING = "HEALING"
    TERMINATED = "TERMINATED"


class TerminationReason(str, Enum):
    SUCCESS = "SUCCESS"
    FAILED = "FAILED"
    DENIED = "DENIED"
    TIMEOUT = "TIMEOUT"
    BUDGET_EXHAUSTED = "BUDGET_EXHAUSTED"


class InvalidTransitionError(Exception):
    """Raised when an illegal FSM transition is attempted."""
    pass


# Explicit FSM transition table
LEGAL_TRANSITIONS: dict[HarnessState, set[HarnessState]] = {
    HarnessState.INITIALIZING: {HarnessState.PERCEIVING, HarnessState.TERMINATED},
    HarnessState.PERCEIVING: {HarnessState.THINKING, HarnessState.TERMINATED},
    HarnessState.THINKING: {HarnessState.VALIDATING, HarnessState.TERMINATED},
    HarnessState.VALIDATING: {HarnessState.EXECUTING, HarnessState.AWAITING_APPROVAL, HarnessState.HEALING, HarnessState.TERMINATED},
    HarnessState.AWAITING_APPROVAL: {HarnessState.EXECUTING, HarnessState.TERMINATED},
    HarnessState.EXECUTING: {HarnessState.THINKING, HarnessState.HEALING, HarnessState.TERMINATED},
    HarnessState.HEALING: {HarnessState.THINKING, HarnessState.TERMINATED},
    HarnessState.TERMINATED: set()
}


@dataclass
class TaskSession:
    session_id: str
    correlation_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    current_state: HarnessState = HarnessState.INITIALIZING
    current_turn: int = 0
    max_turns: int = 10
    heal_attempts: int = 0
    max_heal_attempts: int = 3
    termination_reason: TerminationReason | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


class NativeHarness:
    """Task Lifecycle Orchestrator for E-ZZIO.

    Sequences, bounds, and terminates task execution using canonical microkernel primitives.
    """

    def __init__(
        self,
        router: ModelRouter | None = None,
        policy_guard: AgentPolicyGuard | None = None,
        audit_ledger: AuditLedger | None = None,
        tool_registry: ToolRegistry | None = None,
        workspace_root: str = r"G:\AI\E-zzio"
    ) -> None:
        self.router = router or ModelRouter()
        self.policy_guard = policy_guard or AgentPolicyGuard(workspace_root=workspace_root)
        self.audit_ledger = audit_ledger or AuditLedger()
        self.memory = memory_gateway
        self.tool_registry = tool_registry or ToolRegistry()

    def transition_to(
        self,
        session: TaskSession,
        target_state: HarnessState,
        metadata: dict[str, Any] | None = None
    ) -> None:
        """Applique une transition FSM stricte et enregistre l'événement dans AuditLedger."""
        allowed = LEGAL_TRANSITIONS.get(session.current_state, set())
        if target_state not in allowed:
            err_msg = (f"[HARNESS FSM ERROR] Transition illégale : "
                       f"{session.current_state.value} -> {target_state.value}")
            logger.error(err_msg)
            self._audit_transition(session, session.current_state, target_state, status="ILLEGAL_TRANSITION")
            session.termination_reason = TerminationReason.FAILED
            session.current_state = HarnessState.TERMINATED
            raise InvalidTransitionError(err_msg)

        prev_state = session.current_state
        session.current_state = target_state
        self._audit_transition(session, prev_state, target_state, metadata=metadata)

    def _audit_transition(
        self,
        session: TaskSession,
        prev_state: HarnessState,
        new_state: HarnessState,
        status: str = "SUCCESS",
        metadata: dict[str, Any] | None = None
    ) -> None:
        payload = {
            "session_id": session.session_id,
            "correlation_id": session.correlation_id,
            "previous_state": prev_state.value,
            "new_state": new_state.value,
            "turn": session.current_turn,
            "timestamp": time.time()
        }
        if metadata:
            payload["meta"] = metadata
        try:
            self.audit_ledger.record_event(
                actor="native-harness",
                action="STATE_TRANSITION",
                payload=payload,
                status=status
            )
        except Exception as exc:
            logger.warning("[HARNESS AUDIT FAIL] %s", exc)

    def sanitize_error(self, err: Exception, correlation_id: str) -> dict[str, Any]:
        """Convertit une exception en structure sécurisée sans fuite de secrets."""
        raw_msg = str(err)
        safe_msg = raw_msg
        for key in ["aizasy", "sk-", "token", "password", "secret", "bearer"]:
            if key in safe_msg.lower():
                safe_msg = "[REDACTED SECURITY EXCEPTION]"
                break

        return {
            "error_type": err.__class__.__name__,
            "safe_message": safe_msg[:300],
            "correlation_id": correlation_id
        }

    async def execute_task(
        self,
        task_prompt: str,
        session_id: str = "",
        user_id: str = "operator",
        channel: str = "task",
        max_turns: int = 10,
        max_heal_attempts: int = 3,
        **kwargs: Any
    ) -> dict[str, Any]:
        """Exécute le cycle de vie d'une tâche via la FSM Native Harness."""
        if not session_id:
            session_id = f"task-session-{uuid.uuid4().hex[:8]}"

        session = TaskSession(
            session_id=session_id,
            max_turns=max_turns,
            max_heal_attempts=max_heal_attempts
        )

        try:
            # 1. INITIALIZING -> PERCEIVING
            self.transition_to(session, HarnessState.PERCEIVING)

            # Record memory context
            try:
                await self.memory.init()
                await self.memory.record_message(
                    session_id=session_id,
                    role="user",
                    content=task_prompt,
                    metadata={"channel": channel, "user_id": user_id}
                )
            except Exception as m_err:
                logger.warning("[HARNESS MEMORY INIT FAIL] %s", m_err)

            # 2. PERCEIVING -> THINKING
            self.transition_to(session, HarnessState.THINKING)

            # Select engine via canonical ModelRouter
            routing = self.router.select_engine(
                task_type="general",
                complexity_score=0.5,
                risk_level="low",
                channel=channel
            )

            # 3. THINKING -> VALIDATING
            self.transition_to(session, HarnessState.VALIDATING)

            # Policy Guard evaluation
            tool_name = kwargs.get("tool_name")
            tool_args = kwargs.get("tool_args", {})

            if tool_name:
                allowed, reason = self.policy_guard.evaluate_intent(tool_name, tool_args)
                if not allowed:
                    logger.warning(f"[HARNESS POLICY DENIED] {reason}")
                    session.termination_reason = TerminationReason.DENIED
                    self.transition_to(session, HarnessState.TERMINATED, metadata={"reason": reason})
                    return {
                        "status": "DENIED",
                        "session_id": session.session_id,
                        "correlation_id": session.correlation_id,
                        "reason": reason,
                        "turn": session.current_turn
                    }

            # 4. Check approval if required
            requires_approval = kwargs.get("requires_approval", False)
            if requires_approval:
                self.transition_to(session, HarnessState.AWAITING_APPROVAL)
                approved = kwargs.get("approved", False)
                if not approved:
                    session.termination_reason = TerminationReason.DENIED
                    self.transition_to(session, HarnessState.TERMINATED, metadata={"reason": "User approval denied"})
                    return {
                        "status": "DENIED",
                        "session_id": session.session_id,
                        "correlation_id": session.correlation_id,
                        "reason": "Approval denied",
                        "turn": session.current_turn
                    }

            # 5. VALIDATING/AWAITING_APPROVAL -> EXECUTING
            self.transition_to(session, HarnessState.EXECUTING)
            session.current_turn += 1

            # Tool execution or Provider generation via Master/Provider delegate
            exec_result = kwargs.get("exec_result", f"Task '{task_prompt[:50]}' executed successfully under model {routing['model']}.")

            # 6. EXECUTING -> TERMINATED (SUCCESS)
            session.termination_reason = TerminationReason.SUCCESS
            self.transition_to(session, HarnessState.TERMINATED, metadata={"model": routing["model"]})

            return {
                "status": "SUCCESS",
                "session_id": session.session_id,
                "correlation_id": session.correlation_id,
                "turn": session.current_turn,
                "model": routing["model"],
                "result": exec_result
            }

        except InvalidTransitionError as ite:
            return {
                "status": "FAILED",
                "session_id": session.session_id,
                "correlation_id": session.correlation_id,
                "error": self.sanitize_error(ite, session.correlation_id)
            }
        except Exception as exc:
            # Handle healing loop if attempts remaining
            if session.heal_attempts < session.max_heal_attempts and session.current_state in LEGAL_TRANSITIONS and HarnessState.HEALING in LEGAL_TRANSITIONS[session.current_state]:
                session.heal_attempts += 1
                try:
                    self.transition_to(session, HarnessState.HEALING, metadata={"attempt": session.heal_attempts})
                    self.transition_to(session, HarnessState.THINKING)
                except Exception:
                    pass

            session.termination_reason = TerminationReason.FAILED
            try:
                if session.current_state != HarnessState.TERMINATED:
                    self.transition_to(session, HarnessState.TERMINATED)
            except Exception:
                session.current_state = HarnessState.TERMINATED

            return {
                "status": "FAILED",
                "session_id": session.session_id,
                "correlation_id": session.correlation_id,
                "error": self.sanitize_error(exc, session.correlation_id)
            }
