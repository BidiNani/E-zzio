"""Tests Vague C bloc 4 : dag (fin) + evidence_logger + pdf_engine.

Cible :
- dag.py              : 155->154, 181
- evidence_logger.py  : 39-43, 90-91, 100-102, 111-113, 118
- pdf_engine.py       : 47, 129, 132, 135-137, 139->125, 144, 146, 149-161
"""
from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest

# ============================================================
# 1. dag.py — L155->154 (DFS skip) + L181 (cycle cache)
# ============================================================

class TestTaskDAGCompleteCoverage:
    def test_validate_skips_already_visited_in_main_loop(self):
        """L155->154 : chain a -> b -> c.

        dfs(a) visite a, b, c.
        Tour 2 de la boucle principale : 'b' est deja visited -> skip.
        Tour 3 : 'c' est deja visited -> skip.
        """
        from core.orchestration.dag import TaskDAG

        dag = TaskDAG()
        dag.add_node(task_id="a", title="A", action_type="read")
        dag.add_node(task_id="b", title="B", action_type="read", dependencies=["a"])
        dag.add_node(task_id="c", title="C", action_type="read", dependencies=["b"])

        # validate() fait le DFS, doit passer sans erreur
        dag.validate()

    def test_topological_order_cycle_after_validate_bypass(self):
        """L181 : cycle non detecte par validate() mais detecte par topological.

        On patch validate() pour qu'il ne fasse rien, puis on cree un cycle.
        get_topological_order() appellera validate() (no-op) puis verra
        que order < nodes et levera CycleDetectedError ligne 181.
        """
        from core.orchestration.dag import CycleDetectedError, TaskDAG

        dag = TaskDAG()
        dag.add_node(task_id="a", title="A", action_type="read")
        dag.add_node(task_id="b", title="B", action_type="read", dependencies=["a"])
        # Cree un cycle a -> b -> a
        dag.nodes["a"].dependencies = ["b"]

        # Patch validate() pour qu'il soit no-op
        with patch.object(dag, "validate", lambda: None):
            with pytest.raises(CycleDetectedError, match="Unresolvable cycle"):
                dag.get_topological_order()


# ============================================================
# 2. evidence_logger.py — L39-43, 90-91, 100-102, 111-113, 118
# ============================================================

class TestEvidenceLoggerComplete:
    def test_coding_task_evidence_complete_method(self):
        """L39-43 : CodingTaskEvidence.complete() remplit end_time et duration."""
        from core.agent.evidence_logger import CodingTaskEvidence

        ev = CodingTaskEvidence(task_id="t1")
        assert ev.end_time is None
        assert ev.duration_sec == 0.0
        assert ev.result == "PENDING"

        ev.complete(result="SUCCESS", final_diff="+ line", rollback_applied=False)

        assert ev.end_time is not None
        assert ev.duration_sec >= 0.0
        assert ev.result == "SUCCESS"
        assert ev.final_diff == "+ line"
        assert ev.rollback_state is False

    def test_markdown_with_files_commands_tests_and_diff(self, tmp_path):
        """L90-91 (files), L100-102 (commands), L111-113 (tests), L118 (diff)."""
        from core.agent.evidence_logger import CodingTaskEvidence, EvidenceLogger

        logger = EvidenceLogger(workspace_root=str(tmp_path))
        ev = CodingTaskEvidence(
            task_id="t_full",
            plan="plan de test",
            files_changed=["file1.py", "file2.py"],
            commands=[
                {"command": "pytest tests/", "exit_code": 0, "duration_ms": 1500},
                {"command": "ruff check", "exit_code": 1, "duration_ms": 200},
            ],
            tests=[
                {"name": "test_a", "passed": True, "summary": "OK"},
                {"name": "test_b", "passed": False, "summary": "FAIL"},
            ],
        )
        ev.complete(
            result="SUCCESS",
            final_diff="+ new line\n- old line",
            rollback_applied=False,
        )

        res = logger.record_evidence(ev)
        md = Path(res["markdown"]).read_text(encoding="utf-8")

        # L90-91 : fichiers listés
        assert "file1.py" in md
        assert "file2.py" in md
        # L100-102 : commandes avec statut
        assert "pytest tests/" in md
        assert "ruff check" in md
        assert "exit 0" in md
        assert "exit 1" in md
        # L111-113 : tests avec statut
        assert "test_a" in md
        assert "test_b" in md
        # L118 : diff présent (section 5)
        assert "Final Diff Review" in md
        assert "+ new line" in md


# ============================================================
# 3. pdf_engine.py — L47, 129, 132, 135-137, 139->125, 144, 146, 149-161
# ============================================================

class TestPdfEngineComplete:
    def test_filename_without_extension_gets_pdf(self, tmp_path):
        """L47 : filename sans .pdf -> ajout automatique."""
        from core.generators.pdf_engine import PdfEngine

        engine = PdfEngine(workspace_root=str(tmp_path))
        result = engine.generate_pdf(
            filename="sans_extension",
            title="Test",
            sections=[],
        )
        assert result["ok"] is True
        assert result["filename"].endswith(".pdf")
        assert result["filename"] == "sans_extension.pdf"

    def test_all_section_types(self, tmp_path):
        """L129 (heading), L132 (paragraph), L135-137 (bullet), L144/146/149-161 (table)."""
        from core.generators.pdf_engine import PdfEngine

        engine = PdfEngine(workspace_root=str(tmp_path))
        result = engine.generate_pdf(
            filename="full_test.pdf",
            title="Document Complet",
            author="E-ZZIO Test",
            sections=[
                # L128-129 : heading
                {"type": "heading", "text": "Section 1"},
                # L131-132 : paragraph
                {"type": "paragraph", "text": "Ceci est un paragraphe de test."},
                # L134-137 : bullets avec items
                {"type": "bullet", "items": ["Point A", "Point B", "Point C"]},
                # L139-161 : table complète avec headers ET rows
                {
                    "type": "table",
                    "headers": ["Colonne A", "Colonne B"],
                    "rows": [
                        ["val1", "val2"],
                        ["val3", "val4"],
                    ],
                },
            ],
        )
        assert result["ok"] is True
        assert result["size_bytes"] > 0

    def test_bullet_without_items(self, tmp_path):
        """L135->137 : bullets sans items -> pas de crash."""
        from core.generators.pdf_engine import PdfEngine

        engine = PdfEngine(workspace_root=str(tmp_path))
        result = engine.generate_pdf(
            filename="bullets_vides.pdf",
            title="Test",
            sections=[{"type": "bullet", "items": []}],
        )
        assert result["ok"] is True

    def test_table_with_headers_but_no_rows(self, tmp_path):
        """L144 : table avec headers mais sans rows."""
        from core.generators.pdf_engine import PdfEngine

        engine = PdfEngine(workspace_root=str(tmp_path))
        result = engine.generate_pdf(
            filename="headers_seuls.pdf",
            title="Test",
            sections=[
                {
                    "type": "table",
                    "headers": ["H1", "H2"],
                    "rows": [],
                }
            ],
        )
        assert result["ok"] is True

    def test_table_with_rows_but_no_headers(self, tmp_path):
        """L146 : table avec rows mais sans headers."""
        from core.generators.pdf_engine import PdfEngine

        engine = PdfEngine(workspace_root=str(tmp_path))
        result = engine.generate_pdf(
            filename="rows_seuls.pdf",
            title="Test",
            sections=[
                {
                    "type": "table",
                    "headers": [],
                    "rows": [["r1c1", "r1c2"], ["r2c1", "r2c2"]],
                }
            ],
        )
        assert result["ok"] is True
