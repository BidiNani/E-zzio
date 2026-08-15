from typing import Any, Dict, List, Optional
from core.tasks.models import Task, TaskState
from core.tasks.store import ITaskStore

class TaskManager:
    def __init__(self, store: ITaskStore):
        self.store = store

    def create_task(self, title: str, workspace: str, scope: Dict[str, Any]) -> Task:
        task = Task(title=title, workspace=workspace, scope=scope)
        self.store.save(task)
        return task

    def advance_to_scoped(self, task_id: str, detailed_scope: Dict[str, Any]) -> Task:
        task = self._must_get(task_id)
        task.scope.update(detailed_scope)
        task.transition_to(TaskState.SCOPED)
        self.store.save(task)
        return task

    def advance_to_planned(self, task_id: str, plan_steps: List[Dict[str, Any]]) -> Task:
        task = self._must_get(task_id)
        task.plan = plan_steps
        task.transition_to(TaskState.PLANNED)
        self.store.save(task)
        return task

    def require_approval(self, task_id: str, approval_id: str) -> Task:
        task = self._must_get(task_id)
        task.approval_id = approval_id
        task.transition_to(TaskState.AWAITING_APPROVAL)
        self.store.save(task)
        return task

    def authorize_and_execute(self, task_id: str, validated_approval_id: str) -> Task:
        task = self._must_get(task_id)
        if task.approval_id != validated_approval_id:
            raise PermissionError("Jeton d'approbation non concordant.")
        task.transition_to(TaskState.EXECUTING)
        self.store.save(task)
        return task

    def complete_task(self, task_id: str) -> Task:
        task = self._must_get(task_id)
        task.transition_to(TaskState.VERIFYING)
        task.transition_to(TaskState.COMPLETED)
        self.store.save(task)
        return task

    def fail_task(self, task_id: str, reason: str) -> Task:
        task = self._must_get(task_id)
        task.error_message = reason
        task.transition_to(TaskState.FAILED)
        self.store.save(task)
        return task

    def _must_get(self, task_id: str) -> Task:
        task = self.store.get_by_id(task_id)
        if not task:
            raise KeyError(f"Tâche introuvable : {task_id}")
        return task
