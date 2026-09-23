"""Tests Vague C final : interaction_control + nothing_impossible + doc_engine + simple_rag."""
from __future__ import annotations

import asyncio
from unittest.mock import patch

import pytest

# ============================================================
# 1. interaction_control.py
# ============================================================

class TestControlForAllIntents:
    def test_dialogue_interrupt(self):
        from core.agent.interaction_control import InterruptionIntent, control_for
        cmd = control_for(InterruptionIntent.DIALOGUE_INTERRUPT)
        assert cmd.task_effect == "NONE"
        assert cmd.response_action == "STOP_OUTPUT"
        assert cmd.priority == 2

    def test_task_cancel(self):
        from core.agent.interaction_control import InterruptionIntent, control_for
        cmd = control_for(InterruptionIntent.TASK_CANCEL)
        assert cmd.task_effect == "CANCELLING"
        assert cmd.priority == 1

    def test_task_pause(self):
        from core.agent.interaction_control import InterruptionIntent, control_for
        cmd = control_for(InterruptionIntent.TASK_PAUSE)
        assert cmd.task_effect == "PAUSING"
        assert cmd.priority == 3

    def test_task_resume(self):
        from core.agent.interaction_control import InterruptionIntent, control_for
        cmd = control_for(InterruptionIntent.TASK_RESUME)
        assert cmd.task_effect == "RESUMING"
        assert cmd.priority == 3

    def test_task_priority_change(self):
        from core.agent.interaction_control import InterruptionIntent, control_for
        cmd = control_for(InterruptionIntent.TASK_PRIORITY_CHANGE)
        assert cmd.task_effect == "MODIFY"
        assert cmd.priority == 3

    def test_task_reassign(self):
        from core.agent.interaction_control import InterruptionIntent, control_for
        cmd = control_for(InterruptionIntent.TASK_REASSIGN)
        assert cmd.task_effect == "MODIFY"
        assert cmd.priority == 3


class TestClassifyAllPatterns:
    def test_stop_pattern(self):
        from core.agent.interaction_control import InterruptionIntent, classify_interruption
        intent, conf = classify_interruption("stop")
        assert intent == InterruptionIntent.ASK
        assert conf == 1.0

    def test_task_cancel_pattern(self):
        from core.agent.interaction_control import InterruptionIntent, classify_interruption
        intent, conf = classify_interruption("annule la tâche en cours")
        assert intent == InterruptionIntent.TASK_CANCEL
        assert conf == 0.95

    def test_pause_pattern(self):
        from core.agent.interaction_control import InterruptionIntent, classify_interruption
        intent, conf = classify_interruption("fais une pause")
        assert intent == InterruptionIntent.TASK_PAUSE
        assert conf == 0.95

    def test_resume_pattern(self):
        from core.agent.interaction_control import InterruptionIntent, classify_interruption
        intent, conf = classify_interruption("continue le travail")
        assert intent == InterruptionIntent.TASK_RESUME
        assert conf == 0.95

    def test_status_pattern(self):
        from core.agent.interaction_control import InterruptionIntent, classify_interruption
        intent, conf = classify_interruption("quel est le status ?")
        assert intent == InterruptionIntent.TASK_STATUS
        assert conf == 0.95

    def test_priority_pattern(self):
        from core.agent.interaction_control import InterruptionIntent, classify_interruption
        intent, conf = classify_interruption("change la priorité")
        assert intent == InterruptionIntent.TASK_PRIORITY_CHANGE
        assert conf == 0.95

    def test_reassign_pattern(self):
        from core.agent.interaction_control import InterruptionIntent, classify_interruption
        intent, conf = classify_interruption("reassign this task")
        assert intent == InterruptionIntent.TASK_REASSIGN
        assert conf == 0.95

    def test_new_task_pattern(self):
        from core.agent.interaction_control import InterruptionIntent, classify_interruption
        intent, conf = classify_interruption("fais aussi ceci")
        assert intent == InterruptionIntent.NEW_TASK
        assert conf == 0.95

    def test_clarification_pattern(self):
        from core.agent.interaction_control import InterruptionIntent, classify_interruption
        intent, conf = classify_interruption("uniquement ce fichier")
        assert intent == InterruptionIntent.CLARIFICATION
        assert conf == 0.95

    def test_dialogue_interrupt_pattern(self):
        from core.agent.interaction_control import InterruptionIntent, classify_interruption
        intent, conf = classify_interruption("attends une seconde")
        assert intent == InterruptionIntent.DIALOGUE_INTERRUPT
        assert conf == 0.95


class TestStatusView:
    def test_status_view_all_params(self):
        from core.agent.interaction_control import status_view
        result = status_view(task_id="t1", status="RUNNING", title="Test",
                             progress=0.5, elapsed_s=10.0, agent="coder")
        assert result["task_id"] == "t1"
        assert result["progress"] == 0.5
        assert result["elapsed_s"] == 10.0
        assert result["agent"] == "coder"

    def test_status_view_defaults(self):
        from core.agent.interaction_control import status_view
        result = status_view(task_id="t2", status="PENDING", title="X")
        assert result["progress"] == "UNKNOWN"
        assert result["elapsed_s"] == "UNKNOWN"
        assert result["agent"] == "UNKNOWN"


# ============================================================
# 2. nothing_impossible.py
# ============================================================

class TestFeasibilityEngineComplete:
    def test_evaluate_unknown_gap(self):
        import core.agent.nothing_impossible as ni_mod
        from core.agent.nothing_impossible import FeasibilityEngine
        e = FeasibilityEngine()
        with patch.object(ni_mod, "self_knowledge") as mock_sk:
            mock_sk.query_capability.return_value = {"can_do": False}
            mock_sk.detect_gap.return_value = {"gap_type": "UNKNOWN_GAP"}
            res = e.evaluate_feasibility("something we can't do")
            assert res["feasibility"] == "POSSIBLE_WITH_NEW_CAPABILITY"
            assert res["action"] == "ACQUIRE_OR_CREATE_CAPABILITY"

    def test_evaluate_knowledge_gap(self):
        import core.agent.nothing_impossible as ni_mod
        from core.agent.nothing_impossible import FeasibilityEngine
        e = FeasibilityEngine()
        with patch.object(ni_mod, "self_knowledge") as mock_sk:
            mock_sk.query_capability.return_value = {"can_do": False}
            mock_sk.detect_gap.return_value = {"gap_type": "KNOWLEDGE_GAP"}
            res = e.evaluate_feasibility("need research")
            assert res["feasibility"] == "POSSIBLE_WITH_EXISTING_CAPABILITIES"
            assert res["action"] == "RESEARCH"

    def test_create_custom_tool_complete(self):
        import core.agent.nothing_impossible as ni_mod
        from core.agent.nothing_impossible import FeasibilityEngine
        e = FeasibilityEngine()
        with patch.object(ni_mod, "self_knowledge") as mock_sk:
            mock_sk.install_and_register_tool.return_value = {"registered": True}
            res = e.create_custom_tool({"name": "my_tool", "capability_name": "my_cap"})
            assert res["status"] == "SUCCESS"
            assert res["tool_name"] == "my_tool"
            assert res["capability_added"] == "my_cap"

    def test_create_custom_tool_default_name(self):
        import core.agent.nothing_impossible as ni_mod
        from core.agent.nothing_impossible import FeasibilityEngine
        e = FeasibilityEngine()
        with patch.object(ni_mod, "self_knowledge") as mock_sk:
            mock_sk.install_and_register_tool.return_value = {}
            res = e.create_custom_tool({})
            assert res["tool_name"].startswith("custom_tool_")
            assert res["capability_added"] == "custom_capability"

    def test_create_custom_adapter(self):
        import core.agent.nothing_impossible as ni_mod
        from core.agent.nothing_impossible import FeasibilityEngine
        e = FeasibilityEngine()
        with patch.object(ni_mod, "self_knowledge") as mock_sk:
            mock_sk.install_and_register_tool.return_value = {}
            res = e.create_custom_adapter("json", "xml")
            assert res["status"] == "SUCCESS"
            assert res["tool_name"] == "adapter_json_to_xml"

    def test_format_honest_failure(self):
        from core.agent.nothing_impossible import FeasibilityEngine
        e = FeasibilityEngine()
        res = e.format_honest_failure("Pas possible", "credential")
        assert res["status"] == "HONEST_FAILURE"
        assert res["missing_capability"] == "credential"

    def test_solve_iteratively_block(self):
        from core.agent.nothing_impossible import FeasibilityEngine
        e = FeasibilityEngine()
        res = e.solve_iteratively("bypass_security")
        assert res["status"] == "HONEST_FAILURE"
        assert res["missing_capability"] == "SECURITY_POLICY"

    def test_solve_iteratively_direct(self):
        import core.agent.nothing_impossible as ni_mod
        from core.agent.nothing_impossible import FeasibilityEngine
        e = FeasibilityEngine()
        with patch.object(ni_mod, "self_knowledge") as mock_sk:
            mock_sk.query_capability.return_value = {"can_do": True, "capability_id": "cap_code"}
            res = e.solve_iteratively("write code")
            assert res["status"] == "RESOLVED"
            assert res["path"] == "DIRECT_EXECUTION"

    def test_solve_iteratively_composition(self):
        import core.agent.nothing_impossible as ni_mod
        from core.agent.nothing_impossible import FeasibilityEngine
        e = FeasibilityEngine()
        with patch.object(ni_mod, "self_knowledge") as mock_sk:
            mock_sk.query_capability.return_value = {"can_do": False}
            mock_sk.detect_gap.return_value = {"gap_type": "TOOL_GAP"}
            res = e.solve_iteratively("generate a report")
            assert res["status"] == "RESOLVED"
            assert res["path"] == "CAPABILITY_COMPOSITION"

    def test_solve_iteratively_creation(self):
        import core.agent.nothing_impossible as ni_mod
        from core.agent.nothing_impossible import FeasibilityEngine
        e = FeasibilityEngine()
        with patch.object(ni_mod, "self_knowledge") as mock_sk:
            mock_sk.query_capability.return_value = {"can_do": False}
            mock_sk.detect_gap.return_value = {"gap_type": "TOOL_GAP"}
            mock_sk.install_and_register_tool.return_value = {}
            res = e.solve_iteratively("do something unique")
            assert res["status"] == "RESOLVED"


# ============================================================
# 3. doc_engine.py
# ============================================================

class TestDocEngineComplete:
    def test_docx_unavailable(self, tmp_path):
        from core.generators import doc_engine as de_mod
        from core.generators.doc_engine import DocEngine
        engine = DocEngine(workspace_root=str(tmp_path))
        with patch.object(de_mod, "DOCX_AVAILABLE", False):
            res = engine.generate_docx(filename="x.docx", title="T", sections=[])
        assert res["ok"] is False

    def test_all_sections(self, tmp_path):
        from core.generators.doc_engine import DocEngine
        engine = DocEngine(workspace_root=str(tmp_path))
        res = engine.generate_docx(
            filename="full.docx", title="Doc", author="E-ZZIO",
            sections=[
                {"type": "heading", "level": 2, "text": "Titre"},
                {"type": "paragraph", "text": "Para"},
                {"type": "bullet", "items": ["A", "B"]},
                {"type": "table", "headers": ["H1", "H2"], "rows": [["a", "b"]]},
            ],
        )
        assert "ok" in res

    def test_table_no_headers(self, tmp_path):
        from core.generators.doc_engine import DocEngine
        engine = DocEngine(workspace_root=str(tmp_path))
        res = engine.generate_docx(
            filename="no_h.docx", title="T",
            sections=[{"type": "table", "rows": [["a", "b"]]}],
        )
        assert "ok" in res


# ============================================================
# 4. simple_rag.py
# ============================================================

class TestSimpleRAGComplete:
    def test_add_and_search(self, tmp_path):
        from core.rag.simple_rag import SimpleRAG
        rag = SimpleRAG(db_path=str(tmp_path / "rag.db"))
        asyncio.run(rag.init())
        doc_id = asyncio.run(rag.add_document(
            content="E-ZZIO est un assistant IA.",
            metadata={"source": "test"},
            tag="general",
        ))
        assert doc_id is not None
        results = asyncio.run(rag.search_documents("E-ZZIO", limit=5))
        assert isinstance(results, list)

    def test_add_documents_batch(self, tmp_path):
        from core.rag.simple_rag import SimpleRAG
        rag = SimpleRAG(db_path=str(tmp_path / "rag.db"))
        asyncio.run(rag.init())
        ids = asyncio.run(rag.add_documents([
            {"content": "Premier.", "tag": "a"},
            {"content": "Deuxième.", "tag": "b"},
        ]))
        assert len(ids) == 2

    def test_search_with_tag(self, tmp_path):
        from core.rag.simple_rag import SimpleRAG
        rag = SimpleRAG(db_path=str(tmp_path / "rag.db"))
        asyncio.run(rag.init())
        asyncio.run(rag.add_document(content="Doc A", tag="cat_a"))
        results = asyncio.run(rag.search_documents("Doc", limit=5, tag="cat_a"))
        assert isinstance(results, list)

    def test_delete_document(self, tmp_path):
        from core.rag.simple_rag import SimpleRAG
        rag = SimpleRAG(db_path=str(tmp_path / "rag.db"))
        asyncio.run(rag.init())
        doc_id = asyncio.run(rag.add_document(content="A supprimer"))
        result = asyncio.run(rag.delete_document(doc_id))
        assert result is True
