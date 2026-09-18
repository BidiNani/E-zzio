"""Always-on / barge-in / contrôle de tâches — classification, lifecycle, honnêteté."""
from core.agent.interaction_control import (
    InterruptionIntent as I,
)
from core.agent.interaction_control import (
    classify_interruption,
    control_for,
    reconcile_after_restart,
    status_view,
)
from core.agent.mission_controller import MissionTask, TaskStatus, WorkerRole


def _task():
    return MissionTask(task_id="T1", title="t", description="d", role=WorkerRole.CODER)


def test_classify_each_intent_fr_en():
    cases = [
        ("Stoppe cette tâche", I.TASK_CANCEL),
        ("Cancel the task", I.TASK_CANCEL),
        ("Mets en pause la tâche", I.TASK_PAUSE),
        ("Reprends la tâche", I.TASK_RESUME),
        ("Continue", I.TASK_RESUME),
        ("Où en es-tu ?", I.TASK_STATUS),
        ("Where is the progress?", I.TASK_STATUS),
        ("Passe A en priorité haute", I.TASK_PRIORITY_CHANGE),
        ("Travaille plutôt sur X, laisse le reste", I.TASK_REASSIGN),
        ("Pendant ce temps, fais aussi X", I.NEW_TASK),
        ("Je précise : uniquement les critiques", I.CLARIFICATION),
        ("Attends, écoute-moi une seconde", I.DIALOGUE_INTERRUPT),
    ]
    for text, expected in cases:
        intent, _ = classify_interruption(text)
        assert intent == expected, text


def test_ambiguous_is_ask_never_cancel():
    for text in ("", "stop", "euh", "annule... hmm en fait non, parle",
                 "Attends, je veux préciser quelque chose"):  # égalité → ASK
        intent, _ = classify_interruption(text)
        assert intent == I.ASK, text
    # ASK n'arrête jamais la tâche (effet NONE comme DIALOGUE)
    assert control_for(I.ASK).task_effect == "NONE"


def test_barge_in_is_not_cancellation():
    intent, _ = classify_interruption("Attends, écoute-moi une seconde")
    assert intent == I.DIALOGUE_INTERRUPT
    cmd = control_for(intent)
    assert cmd.response_action == "STOP_OUTPUT"
    assert cmd.task_effect == "NONE"  # la tâche continue


def test_explicit_cancel_commands_cancelling():
    intent, _ = classify_interruption("Stoppe cette tâche")
    cmd = control_for(intent)
    assert cmd.task_effect == "CANCELLING"
    assert cmd.priority < control_for(I.DIALOGUE_INTERRUPT).priority  # P1 > P2


def test_cooperative_cancel_lifecycle():
    t = _task()
    t.transition_to(TaskStatus.RUNNING)
    assert t.transition_to(TaskStatus.CANCELLING) is True
    assert t.status == TaskStatus.CANCELLING  # observé, pas encore CANCELLED
    assert t.transition_to(TaskStatus.CANCELLED) is True


def test_pause_resume_lifecycle():
    t = _task()
    t.transition_to(TaskStatus.RUNNING)
    for s in (TaskStatus.PAUSING, TaskStatus.PAUSED,
              TaskStatus.RESUMING, TaskStatus.RUNNING):
        assert t.transition_to(s) is True
    assert t.status == TaskStatus.RUNNING


def test_status_never_invents_progress():
    v = status_view("T1", "RUNNING", "tests", None, agent="coder")
    assert v["progress"] == "UNKNOWN"
    assert v["elapsed_s"] == "UNKNOWN"
    v2 = status_view("T1", "RUNNING", "tests", 42.0, elapsed_s=192.0)
    assert v2["progress"] == 42.0 and v2["elapsed_s"] == 192.0


def test_reconcile_fail_closed():
    assert reconcile_after_restart("RUNNING") == "UNKNOWN"
    assert reconcile_after_restart("CANCELLING") == "UNKNOWN"
    assert reconcile_after_restart("") == "UNKNOWN"
    assert reconcile_after_restart("SUCCEEDED") == "SUCCEEDED"
    assert reconcile_after_restart("CANCELLED") == "CANCELLED"


def test_scenario_two_tasks_governed():
    a, b = _task(), _task()
    a.task_id, b.task_id = "A", "B"
    a.transition_to(TaskStatus.RUNNING)
    b.transition_to(TaskStatus.RUNNING)
    intent, _ = classify_interruption("Passe A en priorité haute")
    assert intent == I.TASK_PRIORITY_CHANGE
    assert control_for(intent).task_effect == "MODIFY"
    assert a.status == TaskStatus.RUNNING and b.status == TaskStatus.RUNNING
