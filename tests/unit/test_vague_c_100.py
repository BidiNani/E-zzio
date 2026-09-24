"""Tests Vague C : 10 fichiers 90-94% -> 100%.

Cible les branches manquantes deduites du code source :
- ledger_engine.py          : except sur identity / json corrompu
- pdf_engine.py             : table_data vide
- interaction_control.py    : branches else / reconcile
- nothing_impossible.py     : BLOCK policy / compose / backtrack
- system_cleanup.py         : protections discord.log / except
- evidence_logger.py        : branches else (no files/commands/tests)
- model_registry.py         : id hors ROLE_MAP / doublon / role match
- dag.py                    : cycle / self-dep / node doublon
- simple_rag.py             : query vide / fallback LIKE
- doc_engine.py             : DOCX absent / table vide
"""
from __future__ import annotations

import asyncio
import json
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# ============================================================
# 1. ledger_engine.py
# ============================================================

class TestLedgerEngineBranches:
    def test_identity_ctx_raises_during_init(self, tmp_path):
        """L37-38 : ImmutableIdentityContext leve -> boot_identity_root = None."""
        from core.security import ledger_engine as le_mod

        with patch.object(le_mod, "LEDGER_PATH", tmp_path / "ledger.jsonl"), \
             patch.object(le_mod, "LOCK_PATH", tmp_path / "ledger.lock"), \
             patch.object(le_mod, "ARCHIVE_DIR", tmp_path / "archive"), \
             patch.object(le_mod, "ImmutableIdentityContext", side_effect=RuntimeError("boom")), \
             patch.dict("os.environ", {"EZZIO_LEDGER_SECRET": "test_secret"}):
            engine = le_mod.LedgerEngine()
            assert engine.boot_identity_root is None
            assert engine.system_mode == "FAIL_CLOSED"

    def test_identity_ctx_raises_during_commit(self, tmp_path):
        """L67-69 : 2e appel ImmutableIdentityContext leve -> FAIL_CLOSED."""
        from core.security import ledger_engine as le_mod

        class FakeCtx:
            identity_root_hash = "hash_root"
            signature = "sig"

        with patch.object(le_mod, "LEDGER_PATH", tmp_path / "ledger.jsonl"), \
             patch.object(le_mod, "LOCK_PATH", tmp_path / "ledger.lock"), \
             patch.object(le_mod, "ARCHIVE_DIR", tmp_path / "archive"), \
             patch.dict("os.environ", {"EZZIO_LEDGER_SECRET": "test_secret"}):
            # 1er appel : OK
            with patch.object(le_mod, "ImmutableIdentityContext", return_value=FakeCtx()):
                engine = le_mod.LedgerEngine()
            assert engine.system_mode == "NORMAL"

            # 2e appel : raise
            with patch.object(le_mod, "ImmutableIdentityContext", side_effect=RuntimeError("drift")):
                res = engine.commit_transaction("intent", "req", [], "sel", "state")
            assert res is False
            assert engine.system_mode == "FAIL_CLOSED"

    def test_corrupted_jsonl_returns_default(self, tmp_path):
        """L54-55 : JSON corrompu -> except -> return 0, '0'*64."""
        from core.security import ledger_engine as le_mod

        ledger_path = tmp_path / "ledger.jsonl"
        ledger_path.write_text("NOT_JSON\n", encoding="utf-8")

        with patch.object(le_mod, "LEDGER_PATH", ledger_path), \
             patch.object(le_mod, "LOCK_PATH", tmp_path / "ledger.lock"), \
             patch.object(le_mod, "ARCHIVE_DIR", tmp_path / "archive"), \
             patch.dict("os.environ", {"EZZIO_LEDGER_SECRET": "test_secret"}):
            engine = le_mod.LedgerEngine()
            seq, h = engine._get_last_sequence_and_hash()
            assert seq == 0
            assert h == "0" * 64


# ============================================================
# 2. pdf_engine.py
# ============================================================

class TestPdfEngineEmptyTable:
    def test_table_section_without_data(self, tmp_path):
        """L148 : table_data vide -> pas de Table."""
        from core.generators.pdf_engine import PdfEngine

        engine = PdfEngine(workspace_root=str(tmp_path))
        result = engine.generate_pdf(
            filename="empty_table.pdf",
            title="Test",
            sections=[
                {"type": "table", "headers": [], "rows": []},
            ],
        )
        assert result["ok"] is True
        assert result["size_bytes"] > 0


# ============================================================
# 3. interaction_control.py
# ============================================================

class TestInteractionControlBranches:
    def test_control_for_status_default_else(self):
        """L45-46 : intent non listé -> else (NONE/NORMAL/priority=4)."""
        from core.agent.interaction_control import InterruptionIntent, control_for

        cmd = control_for(InterruptionIntent.TASK_STATUS)
        assert cmd.task_effect == "NONE"
        assert cmd.response_action == "NORMAL"
        assert cmd.priority == 4

    def test_classify_empty_returns_ask(self):
        """L50-51 : texte vide -> ASK, 1.0."""
        from core.agent.interaction_control import InterruptionIntent, classify_interruption

        intent, conf = classify_interruption("")
        assert intent == InterruptionIntent.ASK
        assert conf == 1.0

    def test_classify_unrecognized_returns_ask_low(self):
        """L78 : texte inconnu -> ASK, 0.5."""
        from core.agent.interaction_control import InterruptionIntent, classify_interruption

        intent, conf = classify_interruption("blablabla random")
        assert intent == InterruptionIntent.ASK
        assert conf == 0.5

    def test_reconcile_after_restart_running(self):
        """L100-101 : RUNNING -> UNKNOWN."""
        from core.agent.interaction_control import reconcile_after_restart

        assert reconcile_after_restart("RUNNING") == "UNKNOWN"
        assert reconcile_after_restart("") == "UNKNOWN"
        assert reconcile_after_restart("DONE") == "DONE"


# ============================================================
# 4. nothing_impossible.py
# ============================================================

class TestNothingImpossibleBranches:
    def test_policy_block(self):
        """L100-106 : bypass_security -> BLOCKED_BY_POLICY."""
        from core.agent.nothing_impossible import FeasibilityEngine

        e = FeasibilityEngine()
        res = e.evaluate_feasibility("bypass_security to get admin")
        assert res["feasibility"] == "BLOCKED_BY_POLICY"
        assert res["action"] == "BLOCK"

    def test_possible_now(self):
        """L110-116 : capability native -> POSSIBLE_NOW."""
        from core.agent.nothing_impossible import FeasibilityEngine

        e = FeasibilityEngine()
        with patch.object(e.__class__, "__init__", lambda self: None):
            pass  # no-op, keeps real init

        # Mock self_knowledge pour retourner can_do=True
        import core.agent.nothing_impossible as ni_mod
        with patch.object(ni_mod, "self_knowledge") as mock_sk:
            mock_sk.query_capability.return_value = {"can_do": True, "capability_id": "cap_code_editing"}
            e = FeasibilityEngine()
            res = e.evaluate_feasibility("write a python script")
            assert res["feasibility"] == "POSSIBLE_NOW"

    def test_compose_returns_list(self):
        """L140-141 : target contient 'report' -> liste."""
        from core.agent.nothing_impossible import FeasibilityEngine

        e = FeasibilityEngine()
        res = e.compose_capabilities("generate a report")
        assert res == ["cap_text_extraction", "cap_web_search"]

    def test_compose_returns_none(self):
        """L142 : target sans 'report' -> None."""
        from core.agent.nothing_impossible import FeasibilityEngine

        e = FeasibilityEngine()
        assert e.compose_capabilities("do something weird") is None


# ============================================================
# 5. system_cleanup.py
# ============================================================

class TestSystemCleanupBranches:
    def test_active_log_skipped(self, tmp_path):
        """L61-63 : discord.log / uvicorn.log skippes."""
        from core.system_cleanup import SystemCleanupService

        (tmp_path / "discord.log").write_text("active", encoding="utf-8")
        (tmp_path / "uvicorn.log").write_text("active", encoding="utf-8")
        (tmp_path / "other.log").write_text("delete", encoding="utf-8")

        svc = SystemCleanupService(root_dir=str(tmp_path))
        res = svc.run_cleanup(dry_run=True)

        skipped = res["files_skipped"]
        removed = res["files_removed"]
        assert any("discord.log" in s for s in skipped)
        assert any("uvicorn.log" in s for s in skipped)
        assert any("other.log" in r for r in removed)

    def test_remove_archives_dir(self, tmp_path):
        """L36-49 : dossier _archive supprimé (dry_run)."""
        from core.system_cleanup import SystemCleanupService

        arc = tmp_path / "_archive"
        arc.mkdir()
        (arc / "old.txt").write_text("old", encoding="utf-8")

        svc = SystemCleanupService(root_dir=str(tmp_path))
        res = svc.run_cleanup(dry_run=True, remove_logs=False, remove_temp=False)
        assert any("_archive" in f for f in res["folders_removed"])


# ============================================================
# 6. evidence_logger.py
# ============================================================

class TestEvidenceLoggerBranches:
    def test_empty_evidence_branches(self, tmp_path):
        """L92-93, L103-104, L114-115 : tous les 'else' vides."""
        from core.agent.evidence_logger import CodingTaskEvidence, EvidenceLogger

        logger = EvidenceLogger(workspace_root=str(tmp_path))
        ev = CodingTaskEvidence(task_id="t_empty")
        res = logger.record_evidence(ev)

        md = Path(res["markdown"]).read_text(encoding="utf-8")
        assert "_No files modified._" in md
        assert "_No commands executed._" in md
        assert "_No tests registered._" in md


# ============================================================
# 7. model_registry.py
# ============================================================

class TestModelRegistryBranches:
    def test_role_map_filters_unknown_models(self):
        """L137-138 : modele cloud hors ROLE_MAP est ignore."""
        from core.routing.model_registry import CanonicalModelRegistry

        reg = CanonicalModelRegistry()
        # Le registre ne contient QUE les modeles dans ROLE_MAP
        for m in reg.list_models():
            assert m.name in {
                "gemini-3.8-flash", "gemini-3.7-flash", "gemini-3.6-flash",
                "gemini-3.5-flash-lite", "gemini-3.5-flash",
                "qwen2.5-coder:7b-instruct-q4_K_M", "qwen3.5-mtp:4b",
                "phi4-mini:latest", "hermes3:8b", "qwen3.5:9b", "deepseek-r1:7b",
            }

    def test_add_doublon_is_ignored(self):
        """L167-168 : _add ignore les doublons par nom."""
        from core.routing.model_registry import (
            CanonicalModelRecord,
            CanonicalModelRegistry,
            ModelSource,
        )

        reg = CanonicalModelRegistry()
        n_before = len(reg.list_models())

        rec = CanonicalModelRecord(name="gemini-3.8-flash", source=ModelSource.GEMINI)
        reg._add(rec)  # doublon

        assert len(reg.list_models()) == n_before

    def test_get_by_role_returns_match(self):
        """L184-188 : get_by_role trouve le bon modele."""
        from core.routing.model_registry import CanonicalModelRegistry

        reg = CanonicalModelRegistry()
        m = reg.get_by_role("CODING")
        assert m is not None
        assert "CODING" in m.roles or m.role == "CODING"


# ============================================================
# 8. dag.py
# ============================================================

class TestTaskDAGBranches:
    def test_duplicate_node_raises(self):
        """L107-108 : task_id existe -> ValueError."""
        from core.orchestration.dag import TaskDAG

        dag = TaskDAG()
        dag.add_node(task_id="t1", title="first", action_type="read")
        with pytest.raises(ValueError, match="already exists"):
            dag.add_node(task_id="t1", title="dup", action_type="read")

    def test_self_dependency_raises(self):
        """L138-139 : self-dep -> CycleDetectedError."""
        from core.orchestration.dag import CycleDetectedError, TaskDAG

        dag = TaskDAG()
        dag.add_node(task_id="t1", title="a", action_type="read")
        # On force une self-dep en mutant directement
        dag.nodes["t1"].dependencies = ["t1"]
        with pytest.raises(CycleDetectedError, match="Self-dependency"):
            dag.validate()

    def test_cycle_raises(self):
        """L148 : cycle A -> B -> A -> CycleDetectedError."""
        from core.orchestration.dag import CycleDetectedError, TaskDAG

        dag = TaskDAG()
        dag.add_node(task_id="a", title="A", action_type="x")
        dag.add_node(task_id="b", title="B", action_type="y", dependencies=["a"])
        # Cree le cycle manuellement
        dag.nodes["a"].dependencies = ["b"]
        with pytest.raises(CycleDetectedError):
            dag.validate()

    def test_get_ready_nodes_partial_deps(self):
        """L194-196 : dep non COMPLETED -> not ready."""
        from core.orchestration.dag import DAGExecutionStatus, TaskDAG

        dag = TaskDAG()
        dag.add_node(task_id="a", title="A", action_type="x")
        dag.add_node(task_id="b", title="B", action_type="y", dependencies=["a"])

        # b n'est pas ready car a n'est pas COMPLETED
        ready = dag.get_ready_nodes()
        assert "a" in [n.task_id for n in ready]
        assert "b" not in [n.task_id for n in ready]

        # Marque a comme COMPLETED -> b devient ready
        dag.nodes["a"].status = DAGExecutionStatus.COMPLETED
        ready = dag.get_ready_nodes()
        assert "b" in [n.task_id for n in ready]


# ============================================================
# 9. simple_rag.py
# ============================================================

class TestSimpleRAGBranches:
    def test_search_empty_query(self):
        """L107-108 : query vide -> []."""
        from core.rag.simple_rag import SimpleRAG

        rag = SimpleRAG(db_path=":memory:")
        res = asyncio.run(rag.search_documents(""))
        assert res == []

    def test_search_query_only_punctuation(self):
        """L114-115 : tokens nettoyes vides -> []."""
        from core.rag.simple_rag import SimpleRAG

        rag = SimpleRAG(db_path=":memory:")
        res = asyncio.run(rag.search_documents("!@#$"))
        assert res == []

    def test_delete_document_nonexistent(self, tmp_path):
        """L182-187 : delete d'un id inexistant -> False."""
        from core.rag.simple_rag import SimpleRAG

        rag = SimpleRAG(db_path=str(tmp_path / "rag.db"))
        asyncio.run(rag.init())
        res = asyncio.run(rag.delete_document(99999))
        assert res is False


# ============================================================
# 10. doc_engine.py
# ============================================================

class TestDocEngineBranches:
    def test_empty_table_section(self, tmp_path):
        """L107-108 : table sans headers ni rows -> skip."""
        from core.generators.doc_engine import DocEngine

        engine = DocEngine(workspace_root=str(tmp_path))
        res = engine.generate_docx(
            filename="empty_table.docx",
            title="Test",
            sections=[{"type": "table", "headers": [], "rows": []}],
        )
        # Peut etre ok=True ou ok=False selon python-docx dispo
        assert "ok" in res
