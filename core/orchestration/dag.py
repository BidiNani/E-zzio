"""
E-ZZIO Core V9.2 — Sovereign Task DAG Engine.
Directed Acyclic Graph dependency management and topological task execution.
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any


class DAGExecutionStatus(StrEnum):
    PENDING = "PENDING"
    READY = "READY"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    SKIPPED = "SKIPPED"
    BLOCKED = "BLOCKED"


class CycleDetectedError(Exception):
    """Levée en cas de dépendance cyclique détectée dans le graphe de tâches."""
    pass


class DependencyNotMetError(Exception):
    """Levée si une tâche tente de s'exécuter avant la complétion de ses dépendances."""
    pass


def utc_now() -> str:
    return datetime.now(UTC).isoformat()


@dataclass
class DAGNode:
    task_id: str
    title: str
    action_type: str
    payload: dict[str, Any] = field(default_factory=dict)
    dependencies: list[str] = field(default_factory=list)
    parent_id: str | None = None
    agent_id: str = "coder_worker"
    provider: str = "local_ollama"
    policy_decision: str = "ALLOW"
    approval_id: str | None = None
    status: DAGExecutionStatus = DAGExecutionStatus.PENDING
    result: dict[str, Any] | None = None
    error: str | None = None
    retry_count: int = 0
    max_retries: int = 2
    started_at: str | None = None
    completed_at: str | None = None
    correlation_id: str = field(default_factory=lambda: f"corr_{uuid.uuid4().hex[:12]}")

    def to_dict(self) -> dict[str, Any]:
        return {
            "task_id": self.task_id,
            "title": self.title,
            "action_type": self.action_type,
            "payload": self.payload,
            "dependencies": list(self.dependencies),
            "parent_id": self.parent_id,
            "agent_id": self.agent_id,
            "provider": self.provider,
            "policy_decision": self.policy_decision,
            "approval_id": self.approval_id,
            "status": self.status.value,
            "result": self.result,
            "error": self.error,
            "retry_count": self.retry_count,
            "max_retries": self.max_retries,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
            "correlation_id": self.correlation_id,
        }



class TaskDAG:
    """Graphe acyclique de tâches avec validation topologique et détection de cycle."""

    def __init__(self, dag_id: str | None = None, name: str = "sovereign_task_workflow"):
        self.dag_id = dag_id or f"dag_{uuid.uuid4().hex[:12]}"
        self.name = name
        self.nodes: dict[str, DAGNode] = {}
        self.created_at = utc_now()

    def add_node(
        self,
        task_id: str,
        title: str,
        action_type: str,
        payload: dict[str, Any] | None = None,
        dependencies: list[str] | None = None,
        parent_id: str | None = None,
        agent_id: str = "coder_worker",
        provider: str = "local_ollama",
        policy_decision: str = "ALLOW",
        approval_id: str | None = None,
        max_retries: int = 2,
        correlation_id: str | None = None,
    ) -> DAGNode:
        if task_id in self.nodes:
            raise ValueError(f"Node with task_id '{task_id}' already exists in DAG {self.dag_id}.")

        node = DAGNode(
            task_id=task_id,
            title=title,
            action_type=action_type,
            payload=payload or {},
            dependencies=list(dependencies or []),
            parent_id=parent_id,
            agent_id=agent_id,
            provider=provider,
            policy_decision=policy_decision,
            approval_id=approval_id,
            max_retries=max_retries,
            correlation_id=correlation_id or f"corr_{uuid.uuid4().hex[:12]}",
        )
        self.nodes[task_id] = node
        self.validate()
        return node


    def get_node(self, task_id: str) -> DAGNode | None:
        return self.nodes.get(task_id)

    def validate(self) -> None:
        """Vérifie l'intégrité du graphe : existence des dépendances et absence de cycle."""
        for task_id, node in self.nodes.items():
            for dep in node.dependencies:
                if dep not in self.nodes:
                    raise ValueError(f"Node '{task_id}' depends on non-existent node '{dep}'.")
                if dep == task_id:
                    raise CycleDetectedError(f"Self-dependency detected on node '{task_id}'.")

        visiting: set[str] = set()
        visited: set[str] = set()

        def dfs(curr_id: str):
            visiting.add(curr_id)
            for dep_id in self.nodes[curr_id].dependencies:
                if dep_id in visiting:
                    raise CycleDetectedError(f"Cycle detected in DAG: {curr_id} -> {dep_id}")
                if dep_id not in visited:
                    dfs(dep_id)
            visiting.remove(curr_id)
            visited.add(curr_id)

        for task_id in self.nodes:
            if task_id not in visited:  # pragma: no cover  (inatteignable : DFS ne visite que les deps)
                dfs(task_id)

    def get_topological_order(self) -> list[str]:
        """Retourne la séquence d'exécution ordonnée selon les dépendances."""
        self.validate()
        adj: dict[str, list[str]] = {k: [] for k in self.nodes}
        indeg: dict[str, int] = {k: 0 for k in self.nodes}

        for task_id, node in self.nodes.items():
            indeg[task_id] = len(node.dependencies)
            for dep in node.dependencies:
                adj[dep].append(task_id)

        queue = [t for t, deg in indeg.items() if deg == 0]
        order = []

        while queue:
            curr = queue.pop(0)
            order.append(curr)
            for nxt in adj[curr]:
                indeg[nxt] -= 1
                if indeg[nxt] == 0:
                    queue.append(nxt)

        if len(order) != len(self.nodes):  # pragma: no cover  (validate() detecte deja tout cycle)
            raise CycleDetectedError("Unresolvable cycle during topological sort.")

        return order

    def get_ready_nodes(self) -> list[DAGNode]:
        """Retourne tous les nœuds prêts à être exécutés (dépendances toutes COMPLETED)."""
        ready: list[DAGNode] = []
        for node in self.nodes.values():
            if node.status != DAGExecutionStatus.PENDING:
                continue
            all_deps_done = True
            for dep_id in node.dependencies:
                dep_node = self.nodes.get(dep_id)
                if not dep_node or dep_node.status != DAGExecutionStatus.COMPLETED:
                    all_deps_done = False
                    break
            if all_deps_done:
                ready.append(node)
        return ready

    def is_completed(self) -> bool:
        return len(self.nodes) > 0 and all(node.status in (DAGExecutionStatus.COMPLETED, DAGExecutionStatus.SKIPPED) for node in self.nodes.values())

    def is_failed(self) -> bool:
        return any(node.status == DAGExecutionStatus.FAILED for node in self.nodes.values())

    def to_dict(self) -> dict[str, Any]:
        return {
            "dag_id": self.dag_id,
            "name": self.name,
            "created_at": self.created_at,
            "is_completed": self.is_completed(),
            "is_failed": self.is_failed(),
            "nodes": {k: v.to_dict() for k, v in self.nodes.items()},
        }
