"""Tests Vague C bloc 3 : dag.py -> 100%.

Cible les 25 lignes manquantes :
- L60       : DAGNode.to_dict() complet
- L130      : get_node() inexistant
- L137      : dependance non-existante -> ValueError
- L155->154 : DFS skip
- L160-183  : get_topological_order()
- L202      : is_completed() sur DAG vide
- L205      : is_failed() sans fail
- L208      : TaskDAG.to_dict()
"""
from __future__ import annotations

import pytest

# ============================================================
# 1. DAGNode.to_dict() (L60)
# ============================================================

class TestDAGNodeToDict:
    def test_node_to_dict_complete(self):
        """L60 : to_dict() retourne tous les champs."""
        from core.orchestration.dag import DAGExecutionStatus, DAGNode

        node = DAGNode(
            task_id="t1", title="Test", action_type="read",
            payload={"x": 1}, dependencies=["a", "b"],
            status=DAGExecutionStatus.RUNNING,
        )
        d = node.to_dict()
        assert d["task_id"] == "t1"
        assert d["title"] == "Test"
        assert d["action_type"] == "read"
        assert d["payload"] == {"x": 1}
        assert d["dependencies"] == ["a", "b"]
        assert d["status"] == "RUNNING"
        assert "correlation_id" in d
        assert "started_at" in d
        assert "completed_at" in d


# ============================================================
# 2. TaskDAG — get_node, validate (L130, L137)
# ============================================================

class TestTaskDAGAccessors:
    def test_get_node_returns_none_for_missing(self):
        """L130 : get_node() inexistant -> None."""
        from core.orchestration.dag import TaskDAG

        dag = TaskDAG()
        assert dag.get_node("nonexistent") is None

    def test_add_node_with_nonexistent_dependency_raises(self):
        """L137 : dependance non-existante -> ValueError."""
        from core.orchestration.dag import TaskDAG

        dag = TaskDAG()
        with pytest.raises(ValueError, match="non-existent"):
            dag.add_node(
                task_id="t1", title="A", action_type="read",
                dependencies=["does_not_exist"],
            )


# ============================================================
# 3. TaskDAG.validate — DFS skip (L155->154)
# ============================================================

class TestTaskDAGValidateDFS:
    def test_validate_skip_already_visited(self):
        """L155->154 : DFS skip les nodes deja visites.

        Avec 2 nodes qui ont la meme dependance, la 2e DFS voit
        que la dep est deja visitee et skip.
        """
        from core.orchestration.dag import TaskDAG

        dag = TaskDAG()
        # root -> a, root -> b, a et b dependent de root
        dag.add_node(task_id="root", title="R", action_type="read")
        dag.add_node(task_id="a", title="A", action_type="read", dependencies=["root"])
        dag.add_node(task_id="b", title="B", action_type="read", dependencies=["root"])

        # validate() doit passer sans lever
        dag.validate()

        # Verifier la topologie : root avant a et b
        order = dag.get_topological_order()
        assert order.index("root") < order.index("a")
        assert order.index("root") < order.index("b")


# ============================================================
# 4. TaskDAG.get_topological_order (L160-183)
# ============================================================

class TestTaskDAGTopologicalOrder:
    def test_topological_order_simple_chain(self):
        """L160-183 : chain A -> B -> C."""
        from core.orchestration.dag import TaskDAG

        dag = TaskDAG()
        dag.add_node(task_id="a", title="A", action_type="read")
        dag.add_node(task_id="b", title="B", action_type="read", dependencies=["a"])
        dag.add_node(task_id="c", title="C", action_type="read", dependencies=["b"])

        order = dag.get_topological_order()
        assert order.index("a") < order.index("b") < order.index("c")

    def test_topological_order_parallel(self):
        """L160-183 : A et B paralleles, puis C depend des 2."""
        from core.orchestration.dag import TaskDAG

        dag = TaskDAG()
        dag.add_node(task_id="a", title="A", action_type="read")
        dag.add_node(task_id="b", title="B", action_type="read")
        dag.add_node(task_id="c", title="C", action_type="read", dependencies=["a", "b"])

        order = dag.get_topological_order()
        assert order.index("c") == 2  # c en dernier
        assert set(order[:2]) == {"a", "b"}

    def test_topological_order_unresolvable_cycle(self):
        """L180-181 : cycle -> CycleDetectedError.

        On cree un cycle 'cache' (validate() est appele mais on bypasse
        en patchant temporairement validate).
        """
        from core.orchestration.dag import CycleDetectedError, TaskDAG

        dag = TaskDAG()
        dag.add_node(task_id="a", title="A", action_type="read")
        dag.add_node(task_id="b", title="B", action_type="read", dependencies=["a"])
        # Cree le cycle manuellement (a depend de b maintenant)
        dag.nodes["a"].dependencies = ["b"]

        with pytest.raises(CycleDetectedError):
            dag.get_topological_order()


# ============================================================
# 5. TaskDAG.is_completed / is_failed (L202, L205)
# ============================================================

class TestTaskDAGStatus:
    def test_is_completed_empty_dag(self):
        """L202 : DAG vide -> is_completed() = False."""
        from core.orchestration.dag import TaskDAG

        dag = TaskDAG()
        assert dag.is_completed() is False

    def test_is_completed_all_completed(self):
        """L202 : tous les nodes COMPLETED -> True."""
        from core.orchestration.dag import DAGExecutionStatus, TaskDAG

        dag = TaskDAG()
        dag.add_node(task_id="a", title="A", action_type="read")
        dag.add_node(task_id="b", title="B", action_type="read")
        dag.nodes["a"].status = DAGExecutionStatus.COMPLETED
        dag.nodes["b"].status = DAGExecutionStatus.SKIPPED

        assert dag.is_completed() is True

    def test_is_completed_partial(self):
        """L202 : certains PENDING -> False."""
        from core.orchestration.dag import DAGExecutionStatus, TaskDAG

        dag = TaskDAG()
        dag.add_node(task_id="a", title="A", action_type="read")
        dag.add_node(task_id="b", title="B", action_type="read")
        dag.nodes["a"].status = DAGExecutionStatus.COMPLETED
        # b reste PENDING
        assert dag.is_completed() is False

    def test_is_failed_no_fail(self):
        """L205 : aucun FAILED -> is_failed() = False."""
        from core.orchestration.dag import DAGExecutionStatus, TaskDAG

        dag = TaskDAG()
        dag.add_node(task_id="a", title="A", action_type="read")
        dag.nodes["a"].status = DAGExecutionStatus.COMPLETED
        assert dag.is_failed() is False

    def test_is_failed_with_fail(self):
        """L205 : au moins un FAILED -> True."""
        from core.orchestration.dag import DAGExecutionStatus, TaskDAG

        dag = TaskDAG()
        dag.add_node(task_id="a", title="A", action_type="read")
        dag.nodes["a"].status = DAGExecutionStatus.FAILED
        assert dag.is_failed() is True


# ============================================================
# 6. TaskDAG.to_dict (L208)
# ============================================================

class TestTaskDAGToDict:
    def test_dag_to_dict(self):
        """L208 : to_dict() retourne la structure complete."""
        from core.orchestration.dag import TaskDAG

        dag = TaskDAG(name="test_workflow")
        dag.add_node(task_id="a", title="A", action_type="read")
        dag.add_node(task_id="b", title="B", action_type="write", dependencies=["a"])

        d = dag.to_dict()
        assert d["name"] == "test_workflow"
        assert "dag_id" in d
        assert "created_at" in d
        assert d["is_completed"] is False
        assert d["is_failed"] is False
        assert "a" in d["nodes"]
        assert "b" in d["nodes"]
        assert d["nodes"]["b"]["dependencies"] == ["a"]
