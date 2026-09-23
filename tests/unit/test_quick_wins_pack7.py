"""Tests Pack 7 : 4 fichiers a 100%.

- core/security/immutable_audit.py : hash-chain ledger
- core/generators/slide_engine.py : PPTX generator
- core/tasks/store.py : SqliteTaskStore (branches)
- core/integrations/discord/hitl_bridge.py : HITL controller
"""
from __future__ import annotations

import hashlib
import json
import sqlite3
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

# ============================================================
# 1. core/security/immutable_audit.py
# ============================================================

class TestImmutableAuditLedger:
    def test_init_creates_parent_dir(self, tmp_path):
        from core.security.immutable_audit import ImmutableAuditLedger
        log_path = tmp_path / "sub" / "deep" / "audit.jsonl"
        assert not log_path.parent.exists()
        ledger = ImmutableAuditLedger(log_path)
        assert log_path.parent.exists()

    def test_get_last_hash_empty_when_absent(self, tmp_path):
        from core.security.immutable_audit import ImmutableAuditLedger
        ledger = ImmutableAuditLedger(tmp_path / "audit.jsonl")
        assert ledger._get_last_hash() == "0" * 64

    def test_get_last_hash_empty_file(self, tmp_path):
        from core.security.immutable_audit import ImmutableAuditLedger
        log_path = tmp_path / "audit.jsonl"
        log_path.write_text("", encoding="utf-8")
        ledger = ImmutableAuditLedger(log_path)
        assert ledger._get_last_hash() == "0" * 64

    def test_get_last_hash_invalid_json(self, tmp_path):
        from core.security.immutable_audit import ImmutableAuditLedger
        log_path = tmp_path / "audit.jsonl"
        log_path.write_text("not json\n", encoding="utf-8")
        ledger = ImmutableAuditLedger(log_path)
        # Doit catch l'exception et retourner 0*64
        assert ledger._get_last_hash() == "0" * 64

    def test_get_last_hash_valid(self, tmp_path):
        from core.security.immutable_audit import ImmutableAuditLedger
        log_path = tmp_path / "audit.jsonl"
        record = {"hash": "abc123", "event": "test"}
        log_path.write_text(json.dumps(record) + "\n", encoding="utf-8")
        ledger = ImmutableAuditLedger(log_path)
        assert ledger._get_last_hash() == "abc123"

    def test_append_event_first(self, tmp_path):
        from core.security.immutable_audit import ImmutableAuditLedger
        log_path = tmp_path / "audit.jsonl"
        ledger = ImmutableAuditLedger(log_path)
        record = ledger.append_event("login", {"user": "alice"})
        assert record["event"] == "login"
        assert record["data"] == {"user": "alice"}
        assert record["previous_hash"] == "0" * 64
        assert "hash" in record
        # Verifier le hash
        expected_hash = hashlib.sha256(
            json.dumps({k: v for k, v in record.items() if k != "hash"}, sort_keys=True).encode()
        ).hexdigest()
        assert record["hash"] == expected_hash
        # Fichier cree
        assert log_path.exists()

    def test_append_event_chain(self, tmp_path):
        from core.security.immutable_audit import ImmutableAuditLedger
        log_path = tmp_path / "audit.jsonl"
        ledger = ImmutableAuditLedger(log_path)
        r1 = ledger.append_event("e1", {"x": 1})
        r2 = ledger.append_event("e2", {"y": 2})
        # r2.previous_hash == r1.hash
        assert r2["previous_hash"] == r1["hash"]

    def test_verify_chain_absent_file(self, tmp_path):
        from core.security.immutable_audit import ImmutableAuditLedger
        ledger = ImmutableAuditLedger(tmp_path / "audit.jsonl")
        assert ledger.verify_chain() is True

    def test_verify_chain_valid(self, tmp_path):
        from core.security.immutable_audit import ImmutableAuditLedger
        log_path = tmp_path / "audit.jsonl"
        ledger = ImmutableAuditLedger(log_path)
        ledger.append_event("e1", {"x": 1})
        ledger.append_event("e2", {"y": 2})
        ledger.append_event("e3", {"z": 3})
        assert ledger.verify_chain() is True

    def test_verify_chain_invalid_json(self, tmp_path):
        from core.security.immutable_audit import ImmutableAuditLedger
        log_path = tmp_path / "audit.jsonl"
        log_path.write_text("not json\n", encoding="utf-8")
        ledger = ImmutableAuditLedger(log_path)
        assert ledger.verify_chain() is False

    def test_verify_chain_tampered_hash(self, tmp_path):
        from core.security.immutable_audit import ImmutableAuditLedger
        log_path = tmp_path / "audit.jsonl"
        ledger = ImmutableAuditLedger(log_path)
        ledger.append_event("e1", {"x": 1})
        # Corrompre le hash stocke
        content = log_path.read_text(encoding="utf-8")
        record = json.loads(content.strip())
        record["hash"] = "f" * 64
        log_path.write_text(json.dumps(record) + "\n", encoding="utf-8")
        assert ledger.verify_chain() is False

    def test_verify_chain_broken_link(self, tmp_path):
        from core.security.immutable_audit import ImmutableAuditLedger
        log_path = tmp_path / "audit.jsonl"
        ledger = ImmutableAuditLedger(log_path)
        ledger.append_event("e1", {"x": 1})
        # Ajouter un record avec previous_hash errone
        fake = {
            "timestamp": "2025-01-01T00:00:00Z",
            "event": "fake",
            "data": {},
            "previous_hash": "1" * 64,
            "hash": "2" * 64,
        }
        with open(log_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(fake) + "\n")
        assert ledger.verify_chain() is False

    def test_verify_chain_missing_hash_field(self, tmp_path):
        from core.security.immutable_audit import ImmutableAuditLedger
        log_path = tmp_path / "audit.jsonl"
        record = {"event": "no_hash", "previous_hash": "0" * 64}
        log_path.write_text(json.dumps(record) + "\n", encoding="utf-8")
        ledger = ImmutableAuditLedger(log_path)
        assert ledger.verify_chain() is False


# ============================================================
# 2. core/generators/slide_engine.py
# ============================================================

@pytest.fixture
def pptx_available():
    """Skip le module si python-pptx absent."""
    pytest.importorskip("pptx")


class TestSlideEngine:
    def test_engine_init_creates_outputs_dir(self, tmp_path, pptx_available):
        from core.generators.slide_engine import SlideEngine
        engine = SlideEngine(workspace_root=str(tmp_path))
        assert engine.exports_dir.exists()
        assert engine.exports_dir.name == "outputs"

    def test_generate_presentation_minimal(self, tmp_path, pptx_available):
        from core.generators.slide_engine import SlideEngine
        engine = SlideEngine(workspace_root=str(tmp_path))
        result = engine.generate_presentation(
            filename="test.pptx",
            title="Ma Presentation",
        )
        assert result["ok"] is True
        assert result["filename"] == "test.pptx"
        assert Path(result["path"]).exists()
        assert result["slides_count"] == 1  # juste le titre

    def test_generate_presentation_adds_extension(self, tmp_path, pptx_available):
        from core.generators.slide_engine import SlideEngine
        engine = SlideEngine(workspace_root=str(tmp_path))
        result = engine.generate_presentation(filename="sans_ext", title="Test")
        assert result["filename"] == "sans_ext.pptx"

    def test_generate_presentation_with_subtitle(self, tmp_path, pptx_available):
        from core.generators.slide_engine import SlideEngine
        engine = SlideEngine(workspace_root=str(tmp_path))
        result = engine.generate_presentation(
            filename="sub.pptx",
            title="Titre",
            subtitle="Sous-titre custom",
        )
        assert result["slides_count"] == 1

    def test_generate_presentation_with_bullets(self, tmp_path, pptx_available):
        from core.generators.slide_engine import SlideEngine
        engine = SlideEngine(workspace_root=str(tmp_path))
        result = engine.generate_presentation(
            filename="bullets.pptx",
            title="Main",
            slides_data=[
                {"title": "Slide 1", "bullets": ["Point A", "Point B"]},
                {"title": "Slide 2", "bullets": ["X", "Y", "Z"]},
            ],
        )
        # 1 titre + 2 contenu = 3
        assert result["slides_count"] == 3

    def test_generate_presentation_with_table(self, tmp_path, pptx_available):
        from core.generators.slide_engine import SlideEngine
        engine = SlideEngine(workspace_root=str(tmp_path))
        result = engine.generate_presentation(
            filename="table.pptx",
            title="Table",
            slides_data=[
                {
                    "title": "Metrics",
                    "table": {
                        "headers": ["Service", "Latence"],
                        "rows": [["Gateway", "1s"], ["DB", "3ms"]],
                    }
                },
            ],
        )
        assert result["slides_count"] == 2

    def test_filename_sanitized(self, tmp_path, pptx_available):
        from core.generators.slide_engine import SlideEngine
        engine = SlideEngine(workspace_root=str(tmp_path))
        result = engine.generate_presentation(
            filename="../../etc/hack",
            title="Test",
        )
        assert result["filename"] == "hack.pptx"


# ============================================================
# 3. core/tasks/store.py (branches non couvertes)
# ============================================================

class TestSqliteTaskStoreBranches:
    def test_get_by_id_not_found(self, tmp_path):
        """L79-80 : row absente -> return None."""
        from core.tasks.store import SqliteTaskStore
        store = SqliteTaskStore(tmp_path / "tasks.db")
        result = store.get_by_id("tsk_nonexistent")
        assert result is None

    def test_list_by_state_returns_tasks(self, tmp_path):
        """Test list_by_state avec plusieurs tasks."""
        from core.tasks.models import Task, TaskState
        from core.tasks.store import SqliteTaskStore
        store = SqliteTaskStore(tmp_path / "tasks.db")

        t1 = Task(title="a", workspace="w")
        t2 = Task(title="b", workspace="w")
        t2.transition_to(TaskState.SCOPED)
        store.save(t1)
        store.save(t2)

        drafts = store.list_by_state(TaskState.DRAFT)
        scopeds = store.list_by_state(TaskState.SCOPED)
        assert len(drafts) == 1
        assert len(scopeds) == 1
        assert drafts[0].title == "a"
        assert scopeds[0].title == "b"


# ============================================================
# 4. core/integrations/discord/hitl_bridge.py
# ============================================================

def _make_approval_request(
    approval_id="appr1",
    task_id="tsk1",
    agent_id="agent1",
    capability_name="file_write",
    scope=None,
    status=None,
    safe_summary="Resume safe",
    expires_at=None,
):
    """Mock d'une ApprovalRequest."""
    from datetime import UTC, datetime, timedelta

    from core.governance.approval import ApprovalStatus

    req = MagicMock()
    req.approval_id = approval_id
    req.task_id = task_id
    req.agent_id = agent_id
    req.capability_name = capability_name
    req.scope = scope if scope is not None else {"path": "/tmp"}
    req.status = status or ApprovalStatus.PENDING
    req.safe_summary = safe_summary
    req.expires_at = expires_at or (datetime.now(UTC) + timedelta(minutes=5)).isoformat()
    return req


class TestFormatTimeRemaining:
    def test_expired(self):
        from core.integrations.discord.hitl_bridge import format_time_remaining
        # Date dans le passe
        past = "2020-01-01T00:00:00+00:00"
        assert format_time_remaining(past) == "00:00 (Expiré)"

    def test_invalid_format(self):
        from core.integrations.discord.hitl_bridge import format_time_remaining
        assert format_time_remaining("not a date") == "00:00"

    def test_future_time(self):
        from datetime import UTC, datetime, timedelta

        from core.integrations.discord.hitl_bridge import format_time_remaining
        future = (datetime.now(UTC) + timedelta(minutes=2, seconds=30)).isoformat()
        result = format_time_remaining(future)
        # Format "MM:SS" attendu
        assert ":" in result
        assert "Expiré" not in result


class TestDiscordApprovalController:
    def test_init_default_manager(self):
        from core.integrations.discord.hitl_bridge import (
            DiscordApprovalController,
        )
        # Utilise le manager canonique par defaut
        ctrl = DiscordApprovalController()
        assert ctrl.manager is not None

    def test_init_custom_manager(self):
        from core.integrations.discord.hitl_bridge import (
            DiscordApprovalController,
        )
        mock_mgr = MagicMock()
        ctrl = DiscordApprovalController(manager=mock_mgr)
        assert ctrl.manager is mock_mgr

    def test_build_embed_unknown_approval(self):
        from core.integrations.discord.hitl_bridge import (
            DiscordApprovalController,
        )
        mock_mgr = MagicMock()
        mock_mgr.get = MagicMock(return_value=None)
        ctrl = DiscordApprovalController(manager=mock_mgr)
        with pytest.raises(KeyError, match="introuvable"):
            ctrl.build_approval_embed_payload("unknown")

    def test_build_embed_pending(self):
        from core.integrations.discord.hitl_bridge import (
            DiscordApprovalController,
        )
        req = _make_approval_request()
        mock_mgr = MagicMock()
        mock_mgr.get = MagicMock(return_value=req)
        ctrl = DiscordApprovalController(manager=mock_mgr)
        payload = ctrl.build_approval_embed_payload("appr1")
        assert "title" in payload
        assert payload["color"] == 0xFFA500  # orange (pending)

    def test_build_embed_approved(self):
        from core.governance.approval import ApprovalStatus
        from core.integrations.discord.hitl_bridge import (
            DiscordApprovalController,
        )
        req = _make_approval_request(status=ApprovalStatus.APPROVED)
        mock_mgr = MagicMock()
        mock_mgr.get = MagicMock(return_value=req)
        ctrl = DiscordApprovalController(manager=mock_mgr)
        payload = ctrl.build_approval_embed_payload("appr1")
        assert payload["color"] == 0x00FF00  # vert

    def test_build_embed_rejected(self):
        from core.governance.approval import ApprovalStatus
        from core.integrations.discord.hitl_bridge import (
            DiscordApprovalController,
        )
        # REJECTED ou EXPIRED -> rouge
        req = _make_approval_request(status=ApprovalStatus.REJECTED)
        mock_mgr = MagicMock()
        mock_mgr.get = MagicMock(return_value=req)
        ctrl = DiscordApprovalController(manager=mock_mgr)
        payload = ctrl.build_approval_embed_payload("appr1")
        assert payload["color"] == 0xFF0000

    def test_handle_decision_invalid_choice(self):
        from core.integrations.discord.hitl_bridge import (
            DiscordApprovalController,
        )
        ctrl = DiscordApprovalController()
        result = ctrl.handle_interaction_decision(
            approval_id="x", choice_str="INVALID", user_id="1", username="alice",
        )
        assert result["ok"] is False
        assert result["code"] == "INVALID_CHOICE"

    def test_handle_decision_unknown_id(self):
        from core.integrations.discord.hitl_bridge import (
            DiscordApprovalController,
        )
        mock_mgr = MagicMock()
        mock_mgr.decide = MagicMock(side_effect=KeyError("unknown"))
        ctrl = DiscordApprovalController(manager=mock_mgr)
        result = ctrl.handle_interaction_decision(
            approval_id="x", choice_str="APPROVE", user_id="1", username="alice",
        )
        assert result["ok"] is False
        assert result["code"] == "NOT_FOUND"

    def test_handle_decision_expired(self):
        from core.governance.approval import ApprovalExpiredError
        from core.integrations.discord.hitl_bridge import (
            DiscordApprovalController,
        )
        mock_mgr = MagicMock()
        mock_mgr.decide = MagicMock(side_effect=ApprovalExpiredError("expired"))
        ctrl = DiscordApprovalController(manager=mock_mgr)
        result = ctrl.handle_interaction_decision(
            approval_id="x", choice_str="APPROVE", user_id="1", username="alice",
        )
        assert result["ok"] is False
        assert result["code"] == "EXPIRED"

    def test_handle_decision_conflict(self):
        from core.governance.approval import StateTransitionError
        from core.integrations.discord.hitl_bridge import (
            DiscordApprovalController,
        )
        mock_mgr = MagicMock()
        mock_mgr.decide = MagicMock(side_effect=StateTransitionError("conflict"))
        ctrl = DiscordApprovalController(manager=mock_mgr)
        result = ctrl.handle_interaction_decision(
            approval_id="x", choice_str="APPROVE", user_id="1", username="alice",
        )
        assert result["ok"] is False
        assert result["code"] == "CONFLICT"

    def test_handle_decision_internal_error(self):
        from core.integrations.discord.hitl_bridge import (
            DiscordApprovalController,
        )
        mock_mgr = MagicMock()
        mock_mgr.decide = MagicMock(side_effect=RuntimeError("boom"))
        ctrl = DiscordApprovalController(manager=mock_mgr)
        result = ctrl.handle_interaction_decision(
            approval_id="x", choice_str="APPROVE", user_id="1", username="alice",
        )
        assert result["ok"] is False
        assert result["code"] == "INTERNAL_ERROR"

    def test_handle_decision_success(self):
        from core.integrations.discord.hitl_bridge import (
            DiscordApprovalController,
        )
        updated = _make_approval_request()
        updated.status = MagicMock()
        updated.status.value = "APPROVED"
        updated.decided_by = "discord:1 (alice)"

        mock_mgr = MagicMock()
        mock_mgr.decide = MagicMock(return_value=updated)
        ctrl = DiscordApprovalController(manager=mock_mgr)
        result = ctrl.handle_interaction_decision(
            approval_id="appr1", choice_str="APPROVE", user_id="1", username="alice",
        )
        assert result["ok"] is True
        assert "APPROVED" in result["message"]

# ============================================================
# 5. Tests complementaires pour 100% reel
# ============================================================

class TestSlideEngineEdgeCases:
    """Branches non couvertes : subtitle absent, table sans headers, col debordement."""

    def test_generate_presentation_slide_without_subtitle_placeholder(self, tmp_path):
        """L82->91 : si subtitle_shape est None, on skip le bloc."""
        from core.generators.slide_engine import SlideEngine
        engine = SlideEngine(workspace_root=str(tmp_path))
        # On utilise un slides_data avec bullets (pour ne pas planter)
        result = engine.generate_presentation(
            filename="no_sub.pptx",
            title="Sans subtitle",
            slides_data=[{"title": "S1"}],  # pas de bullets ni table
        )
        assert result["ok"] is True

    def test_generate_presentation_table_no_headers(self, tmp_path):
        """L135->144 : table sans headers -> num_rows = len(rows)."""
        from core.generators.slide_engine import SlideEngine
        engine = SlideEngine(workspace_root=str(tmp_path))
        result = engine.generate_presentation(
            filename="no_headers.pptx",
            title="Test",
            slides_data=[
                {
                    "title": "T",
                    "table": {
                        # Pas de headers
                        "rows": [["a", "b"], ["c", "d"]],
                    }
                }
            ],
        )
        assert result["ok"] is True
        assert result["slides_count"] == 2

    def test_generate_presentation_table_row_shorter_than_headers(self, tmp_path):
        """L146->145 : row plus courte que headers -> skip les colonnes manquantes."""
        from core.generators.slide_engine import SlideEngine
        engine = SlideEngine(workspace_root=str(tmp_path))
        result = engine.generate_presentation(
            filename="short_rows.pptx",
            title="Test",
            slides_data=[
                {
                    "title": "T",
                    "table": {
                        "headers": ["A", "B", "C"],
                        "rows": [["1"], ["x", "y"]],  # rows plus courtes
                    }
                }
            ],
        )
        assert result["ok"] is True


class TestSqliteTaskStoreFullLifecycle:
    """Couvre L81 (return _row_to_task) et les branches Protocol."""

    def test_save_then_get_by_id_returns_task(self, tmp_path):
        """L81 : get_by_id trouve un task -> _row_to_task."""
        from core.tasks.models import Task, TaskState
        from core.tasks.store import SqliteTaskStore
        store = SqliteTaskStore(tmp_path / "tasks.db")

        task = Task(title="test", workspace="ws")
        store.save(task)

        retrieved = store.get_by_id(task.task_id)
        assert retrieved is not None
        assert retrieved.task_id == task.task_id
        assert retrieved.title == "test"
        assert retrieved.workspace == "ws"
        assert retrieved.state == TaskState.DRAFT

    def test_save_then_get_preserves_full_state(self, tmp_path):
        """Test que tous les champs sont bien persistes/restitues."""
        from core.tasks.models import Task, TaskState
        from core.tasks.store import SqliteTaskStore
        store = SqliteTaskStore(tmp_path / "tasks.db")

        task = Task(title="full", workspace="ws", scope={"key": "value"}, plan=[{"step": 1}])
        task.transition_to(TaskState.SCOPED)
        store.save(task)

        retrieved = store.get_by_id(task.task_id)
        assert retrieved.scope == {"key": "value"}
        assert retrieved.plan == [{"step": 1}]
        assert retrieved.state == TaskState.SCOPED

    def test_save_overwrites_existing(self, tmp_path):
        """ON CONFLICT : save du meme task_id met a jour."""
        from core.tasks.models import Task, TaskState
        from core.tasks.store import SqliteTaskStore
        store = SqliteTaskStore(tmp_path / "tasks.db")

        task = Task(title="v1", workspace="ws")
        store.save(task)

        task.state = TaskState.SCOPED
        task.scope = {"updated": True}
        store.save(task)

        retrieved = store.get_by_id(task.task_id)
        assert retrieved.state == TaskState.SCOPED
        assert retrieved.scope == {"updated": True}
