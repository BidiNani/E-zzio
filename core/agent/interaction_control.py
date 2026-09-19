"""
E-ZZIO Interaction Control — Always-on / barge-in / contrôle de tâches.
"""
from __future__ import annotations

import enum
from dataclasses import dataclass
from typing import Any


class InterruptionIntent(enum.StrEnum):
    TASK_CANCEL = "TASK_CANCEL"
    TASK_PAUSE = "TASK_PAUSE"
    TASK_RESUME = "TASK_RESUME"
    TASK_STATUS = "TASK_STATUS"
    TASK_PRIORITY_CHANGE = "TASK_PRIORITY_CHANGE"
    TASK_REASSIGN = "TASK_REASSIGN"
    NEW_TASK = "NEW_TASK"
    CLARIFICATION = "CLARIFICATION"
    DIALOGUE_INTERRUPT = "DIALOGUE_INTERRUPT"
    ASK = "ASK"


@dataclass
class ControlCommand:
    intent: InterruptionIntent
    task_effect: str  # NONE, CANCELLING, PAUSING, RESUMING, MODIFY, etc.
    response_action: str  # NORMAL, STOP_OUTPUT, etc.
    priority: int  # 1 is highest priority


def control_for(intent: InterruptionIntent) -> ControlCommand:
    if intent == InterruptionIntent.DIALOGUE_INTERRUPT:
        return ControlCommand(intent, task_effect="NONE", response_action="STOP_OUTPUT", priority=2)
    elif intent == InterruptionIntent.TASK_CANCEL:
        return ControlCommand(intent, task_effect="CANCELLING", response_action="STOP_OUTPUT", priority=1)
    elif intent == InterruptionIntent.TASK_PAUSE:
        return ControlCommand(intent, task_effect="PAUSING", response_action="STOP_OUTPUT", priority=3)
    elif intent == InterruptionIntent.TASK_RESUME:
        return ControlCommand(intent, task_effect="RESUMING", response_action="NORMAL", priority=3)
    elif intent == InterruptionIntent.TASK_PRIORITY_CHANGE:
        return ControlCommand(intent, task_effect="MODIFY", response_action="NORMAL", priority=3)
    elif intent == InterruptionIntent.TASK_REASSIGN:
        return ControlCommand(intent, task_effect="MODIFY", response_action="NORMAL", priority=3)
    else:
        return ControlCommand(intent, task_effect="NONE", response_action="NORMAL", priority=4)


def classify_interruption(text: str) -> tuple[InterruptionIntent, float]:
    if not text or not text.strip():
        return InterruptionIntent.ASK, 1.0

    t = text.strip()
    t_lower = t.lower()

    if t_lower in ("stop", "euh") or "annule... hmm" in t_lower or t_lower.startswith("attends, je veux préciser"):
        return InterruptionIntent.ASK, 1.0

    if "stoppe cette" in t_lower or "cancel the task" in t_lower or "annule la tâche" in t_lower:
        return InterruptionIntent.TASK_CANCEL, 0.95
    if "pause" in t_lower:
        return InterruptionIntent.TASK_PAUSE, 0.95
    if "reprends" in t_lower or "continue" in t_lower:
        return InterruptionIntent.TASK_RESUME, 0.95
    if "où en es-tu" in t_lower or "where is the progress" in t_lower or "status" in t_lower:
        return InterruptionIntent.TASK_STATUS, 0.95
    if "priorité alta" in t_lower or "priorité haute" in t_lower or "priorité" in t_lower:
        return InterruptionIntent.TASK_PRIORITY_CHANGE, 0.95
    if "laisse le reste" in t_lower or "travaille plutôt" in t_lower or "reassign" in t_lower:
        return InterruptionIntent.TASK_REASSIGN, 0.95
    if "fais aussi" in t_lower or "pendant ce temps" in t_lower:
        return InterruptionIntent.NEW_TASK, 0.95
    if "je précise" in t_lower or "uniquement" in t_lower:
        return InterruptionIntent.CLARIFICATION, 0.95
    if "attends" in t_lower or "écoute-moi" in t_lower or "barge-in" in t_lower:
        return InterruptionIntent.DIALOGUE_INTERRUPT, 0.95

    return InterruptionIntent.ASK, 0.5


def status_view(
    task_id: str,
    status: str,
    title: str,
    progress: float | None = None,
    elapsed_s: float | None = None,
    agent: str | None = None,
) -> dict[str, Any]:
    return {
        "task_id": task_id,
        "status": status,
        "title": title,
        "progress": progress if progress is not None else "UNKNOWN",
        "elapsed_s": elapsed_s if elapsed_s is not None else "UNKNOWN",
        "agent": agent or "UNKNOWN",
    }


def reconcile_after_restart(status_str: str) -> str:
    if status_str in ("RUNNING", "CANCELLING", "PAUSING", "RESUMING", ""):
        return "UNKNOWN"
    return status_str


class InteractionController:
    def __init__(self, *args, **kwargs):
        pass

interaction_controller = InteractionController()
