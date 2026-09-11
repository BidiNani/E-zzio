"""
E-ZZIO Core V9.2 — Sovereign Multi-Agent DAG Orchestrator.
Exécute des flux de tâches asynchrones en respectant les graphes de dépendances (DAG),
la gouvernance cryptographique append-only (AuditLedger) et l'isolation des agents.
"""
from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone
from typing import Any, Callable, Coroutine, Dict, List, Optional

from core.orchestration.dag import (
    DAGExecutionStatus,
    DAGNode,
    DependencyNotMetError,
    TaskDAG,
    utc_now,
)
from core.security.audit_ledger import AuditLedger

logger = logging.getLogger("DAGOrchestrator")


TaskHandler = Callable[[DAGNode], Coroutine[Any, Any, Dict[str, Any]]]


class DAGOrchestrator:
    """Moteur d'exécution multi-agent pour les graphes de tâches (DAG)."""

    _instance: Optional[DAGOrchestrator] = None

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(
        self,
        audit_ledger: Optional[AuditLedger] = None,
        max_concurrency: int = 4,
    ):
        if getattr(self, "_initialized", False):
            return
        self.audit_ledger = audit_ledger or AuditLedger()
        self.semaphore = asyncio.Semaphore(max_concurrency)
        self.handlers: Dict[str, TaskHandler] = {}
        self._active_dags: Dict[str, TaskDAG] = {}
        self._lock = asyncio.Lock()
        self._initialized = True

    def register_handler(self, action_type: str, handler: TaskHandler) -> None:
        """Enregistre un exécuteur pour un type d'action donné."""
        self.handlers[action_type] = handler


    async def execute_dag(
        self,
        dag: TaskDAG,
        default_handler: Optional[TaskHandler] = None,
    ) -> Dict[str, Any]:
        """Exécute un DAG jusqu'à complétion ou échec fail-closed."""
        dag.validate()
        async with self._lock:
            self._active_dags[dag.dag_id] = dag

        # Journalisation Genesis DAG dans l'AuditLedger
        try:
            self.audit_ledger.record_event(
                actor="DAGOrchestrator",
                action="DAG_STARTED",
                payload={
                    "dag_id": dag.dag_id,
                    "name": dag.name,
                    "nodes_count": len(dag.nodes),
                    "created_at": dag.created_at,
                },
                status="RUNNING",
            )
        except Exception as e:
            logger.warning("Audit log error on DAG start: %s", e)

        # Boucle d'exécution continue par résolution des nœuds prêts
        while not dag.is_completed() and not dag.is_failed():
            ready_nodes = dag.get_ready_nodes()
            if not ready_nodes:
                # Vérifier si des nœuds tournent encore
                running_nodes = [n for n in dag.nodes.values() if n.status == DAGExecutionStatus.RUNNING]
                if not running_nodes:
                    # Plus rien ne tourne et aucun nœud prêt -> blocage / deadlock
                    for node in dag.nodes.values():
                        if node.status == DAGExecutionStatus.PENDING:
                            node.status = DAGExecutionStatus.BLOCKED
                            node.error = "Unmet dependency or upstream task failure."
                    break
                await asyncio.sleep(0.05)
                continue

            # Lancement concurrent des nœuds prêts dans la limite du sémaphore
            tasks = [
                asyncio.create_task(
                    self._execute_node(node, dag, default_handler)
                )
                for node in ready_nodes
            ]
            await asyncio.gather(*tasks)

        status_str = "COMPLETED" if dag.is_completed() else "FAILED"

        # Journalisation finale dans l'AuditLedger
        try:
            self.audit_ledger.record_event(
                actor="DAGOrchestrator",
                action=f"DAG_{status_str}",
                payload={
                    "dag_id": dag.dag_id,
                    "is_completed": dag.is_completed(),
                    "is_failed": dag.is_failed(),
                },
                status=status_str,
            )
        except Exception as e:
            logger.warning("Audit log error on DAG completion: %s", e)

        return dag.to_dict()

    async def _execute_node(
        self,
        node: DAGNode,
        dag: TaskDAG,
        default_handler: Optional[TaskHandler],
    ) -> None:
        async with self.semaphore:
            node.status = DAGExecutionStatus.RUNNING
            node.started_at = utc_now()

            try:
                self.audit_ledger.record_event(
                    actor=node.agent_id,
                    action="NODE_EXECUTION_START",
                    payload={
                        "dag_id": dag.dag_id,
                        "task_id": node.task_id,
                        "parent_id": node.parent_id,
                        "action_type": node.action_type,
                        "provider": node.provider,
                        "policy": node.policy_decision,
                        "approval_id": node.approval_id,
                        "correlation_id": node.correlation_id,
                    },
                    status="RUNNING",
                )
            except Exception:
                pass

            handler = self.handlers.get(node.action_type, default_handler)
            if not handler:
                node.status = DAGExecutionStatus.FAILED
                node.error = f"No handler registered for action_type '{node.action_type}'"
                node.completed_at = utc_now()
                return

            try:
                res = await handler(node)
                node.result = res
                node.status = DAGExecutionStatus.COMPLETED
                node.completed_at = utc_now()

                try:
                    self.audit_ledger.record_event(
                        actor=node.agent_id,
                        action="NODE_EXECUTION_SUCCESS",
                        payload={
                            "dag_id": dag.dag_id,
                            "task_id": node.task_id,
                            "parent_id": node.parent_id,
                            "provider": node.provider,
                            "correlation_id": node.correlation_id,
                        },
                        status="COMPLETED",
                    )
                except Exception:
                    pass


            except Exception as exc:
                logger.error("Error executing node %s: %s", node.task_id, exc)
                node.retry_count += 1
                if node.retry_count <= node.max_retries:
                    # Remise en attente pour retry
                    node.status = DAGExecutionStatus.PENDING
                    logger.info("Retrying node %s (%d/%d)", node.task_id, node.retry_count, node.max_retries)
                else:
                    node.status = DAGExecutionStatus.FAILED
                    node.error = str(exc)
                    node.completed_at = utc_now()

                    # Échec fail-closed : annuler / marquer les nœuds dépendants en aval
                    self._cascade_skip(dag, node.task_id)

                    try:
                        self.audit_ledger.record_event(
                            actor=node.agent_id,
                            action="NODE_EXECUTION_FAILED",
                            payload={
                                "dag_id": dag.dag_id,
                                "task_id": node.task_id,
                                "error": str(exc),
                                "correlation_id": node.correlation_id,
                            },
                            status="FAILED",
                        )
                    except Exception:
                        pass

    def _cascade_skip(self, dag: TaskDAG, failed_task_id: str) -> None:
        """Marque en SKIPPED tous les nœuds descendants qui dépendaient du nœud échoué."""
        to_skip = set()
        for node in dag.nodes.values():
            if failed_task_id in node.dependencies and node.status == DAGExecutionStatus.PENDING:
                to_skip.add(node.task_id)

        while to_skip:
            curr_id = to_skip.pop()
            curr_node = dag.nodes.get(curr_id)
            if curr_node and curr_node.status == DAGExecutionStatus.PENDING:
                curr_node.status = DAGExecutionStatus.SKIPPED
                curr_node.error = f"Skipped due to upstream failure in '{failed_task_id}'"
                for other in dag.nodes.values():
                    if curr_id in other.dependencies and other.status == DAGExecutionStatus.PENDING:
                        to_skip.add(other.task_id)

    def get_dag(self, dag_id: str) -> Optional[TaskDAG]:
        return self._active_dags.get(dag_id)


dag_orchestrator = DAGOrchestrator()