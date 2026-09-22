"""Tests pour core/human_loop.py.

Cycle cognitif : perceive -> choose_intention -> build_plan -> execute.
Les chemins module-level (JOURNAL_PATH, MEMORY_PATH, INTENT_PATH,
SNAPSHOT_PATH) sont redirigés vers tmp_path pour isolation.

Note : append_journal(event_type, payload) produit un dict avec les clés
"type" et "payload", pas "event_type" et "data" (découvert au run V3-b2).
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from core import human_loop

# ============================================================
# Fixtures
# ============================================================

@pytest.fixture
def isolated_state(monkeypatch, tmp_path):
    """Redirige tous les chemins human_loop vers tmp_path."""
    root = tmp_path / "human_loop"
    root.mkdir(parents=True, exist_ok=True)

    journal = root / "journal.jsonl"
    memory = root / "memory.json"
    intent = root / "current_intent.json"
    snapshot = root / "last_perception.json"

    monkeypatch.setattr(human_loop, "HUMAN_ROOT", root)
    monkeypatch.setattr(human_loop, "JOURNAL_PATH", journal)
    monkeypatch.setattr(human_loop, "MEMORY_PATH", memory)
    monkeypatch.setattr(human_loop, "INTENT_PATH", intent)
    monkeypatch.setattr(human_loop, "SNAPSHOT_PATH", snapshot)

    return {
        "root": root,
        "journal": journal,
        "memory": memory,
        "intent": intent,
        "snapshot": snapshot,
    }


@pytest.fixture
def minimal_perception():
    """Perception minimale valide pour les tests."""
    return {
        "ok": True,
        "created_at": "2026-09-22T12:00:00",
        "context": "test",
        "health": {
            "ok": True,
            "maintenance": {"ok": True, "bad_count": 0, "dust_candidate_count": 0},
        },
        "signals": {
            "system_clean": True,
            "maintenance_ok": True,
            "brain_known": True,
            "manual_tick": True,
            "destructive_actions_allowed": False,
        },
    }


@pytest.fixture
def minimal_intention():
    """Intention minimale valide pour les tests."""
    return {
        "ok": True,
        "goal": "rester prêt",
        "risk_level": "low",
        "risks": [],
    }


# ============================================================
# 1. Smoke + helpers purs
# ============================================================

class TestSmoke:
    def test_module_imports(self):
        assert human_loop is not None

    def test_now_format(self):
        ts = human_loop.now()
        assert isinstance(ts, str)
        assert len(ts) >= 19
        assert "T" in ts


class TestSafeJsonHelpers:
    def test_safe_read_json_nonexistent(self, tmp_path):
        """Fichier absent -> renvoie le default."""
        f = tmp_path / "nope.json"
        assert human_loop.safe_read_json(f, {"default": True}) == {"default": True}
        assert human_loop.safe_read_json(f, None) is None
        assert human_loop.safe_read_json(f, []) == []

    def test_safe_read_json_valid(self, tmp_path):
        """Fichier JSON valide -> renvoie le dict."""
        f = tmp_path / "ok.json"
        f.write_text('{"a": 1, "b": [2, 3]}', encoding="utf-8")
        assert human_loop.safe_read_json(f, {}) == {"a": 1, "b": [2, 3]}

    def test_safe_read_json_corrupt(self, tmp_path):
        """Fichier JSON corrompu -> renvoie le default (pas d'exception)."""
        f = tmp_path / "bad.json"
        f.write_text("NOT JSON {{{", encoding="utf-8")
        assert human_loop.safe_read_json(f, {"fallback": True}) == {"fallback": True}

    def test_safe_write_json_roundtrip(self, tmp_path):
        """safe_write_json écrit, safe_read_json relit."""
        f = tmp_path / "sub" / "test.json"
        human_loop.safe_write_json(f, {"k": "v", "n": 42})
        assert f.exists()
        assert human_loop.safe_read_json(f, None) == {"k": "v", "n": 42}


# ============================================================
# 2. append_journal + journal_tail
# ============================================================

class TestJournal:
    def test_append_journal_creates_file(self, isolated_state):
        """append_journal crée le fichier et retourne un event complet.

        L'event a les clés "type" et "payload" (pas "event_type" et "data").
        """
        event = human_loop.append_journal("test_event", {"data": "x"})
        assert isinstance(event, dict)
        assert event.get("type") == "test_event"
        assert event.get("payload") == {"data": "x"}
        assert "id" in event
        assert "created_at" in event
        assert isolated_state["journal"].exists()

    def test_journal_tail_empty(self, isolated_state):
        """journal_tail sur journal vide ne crashe pas."""
        result = human_loop.journal_tail()
        assert isinstance(result, dict)
        assert result.get("ok") is True
        assert result.get("count") == 0
        assert result.get("events") == []

    def test_journal_tail_after_writes(self, isolated_state):
        """journal_tail retourne les événements après écriture (clé "type")."""
        human_loop.append_journal("evt_1", {"i": 1})
        human_loop.append_journal("evt_2", {"i": 2})
        result = human_loop.journal_tail()
        assert result["count"] == 2
        assert result["events"][0]["type"] == "evt_1"
        assert result["events"][1]["type"] == "evt_2"

    def test_journal_tail_respects_limit(self, isolated_state):
        """journal_tail respecte la limite."""
        for i in range(5):
            human_loop.append_journal(f"evt_{i}", {})
        result = human_loop.journal_tail(limit=2)
        assert result["count"] == 2


# ============================================================
# 3. choose_intention — logique de décision
# ============================================================

class TestChooseIntention:
    def test_choose_intention_with_user_goal(self, isolated_state, minimal_perception):
        """Un goal explicite prime sur tout le reste."""
        result = human_loop.choose_intention(minimal_perception, user_goal="optimiser X")
        assert result["ok"] is True
        assert result["goal"] == "optimiser X"

    def test_choose_intention_system_clean(self, isolated_state, minimal_perception):
        """Système clean + pas de goal -> goal par défaut (prêt)."""
        result = human_loop.choose_intention(minimal_perception)
        assert result["ok"] is True
        assert "prêt" in result["goal"].lower() or "utile" in result["goal"].lower()

    def test_choose_intention_system_dirty(self, isolated_state):
        """Système non clean -> goal de stabilisation."""
        perception = {
            "health": {"maintenance": {"ok": False}},
            "signals": {"system_clean": False},
        }
        result = human_loop.choose_intention(perception)
        assert result["ok"] is True
        assert "stabiliser" in result["goal"].lower()

    def test_choose_intention_maintenance_warning(self, isolated_state):
        """maintenance.ok=False -> risk_level medium + risque listé."""
        perception = {
            "health": {"maintenance": {"ok": False}},
            "signals": {"system_clean": True},
        }
        result = human_loop.choose_intention(perception)
        assert result["risk_level"] == "medium"
        assert any("maintenance" in r.lower() for r in result["risks"])

    def test_choose_intention_writes_intent_file(self, isolated_state, minimal_perception):
        """choose_intention écrit INTENT_PATH."""
        human_loop.choose_intention(minimal_perception)
        assert isolated_state["intent"].exists()
        data = json.loads(isolated_state["intent"].read_text(encoding="utf-8"))
        assert data["ok"] is True


# ============================================================
# 4. build_plan — logique de planification
# ============================================================

class TestBuildPlan:
    def test_build_plan_minimal(self, isolated_state, minimal_perception, minimal_intention):
        """Plan minimal : au moins 3 étapes (verify_maintenance, verify_brain, record)."""
        plan = human_loop.build_plan(minimal_perception, minimal_intention)
        assert plan["ok"] is True
        ids = [s["id"] for s in plan["steps"]]
        assert "verify_maintenance" in ids
        assert "verify_brain_gateway" in ids
        assert "record_state" in ids

    def test_build_plan_with_bad_items(self, isolated_state, minimal_intention):
        """bad_count > 0 -> étape inspect_bad_items."""
        perception = {
            "health": {
                "maintenance": {"ok": False, "bad_count": 3, "dust_candidate_count": 0},
            },
        }
        plan = human_loop.build_plan(perception, minimal_intention)
        ids = [s["id"] for s in plan["steps"]]
        assert "inspect_bad_items" in ids
        assert "dust_dry_run_only" not in ids

    def test_build_plan_with_dust(self, isolated_state, minimal_intention):
        """dust_candidate_count > 0 -> étape dust_dry_run_only."""
        perception = {
            "health": {
                "maintenance": {"ok": True, "bad_count": 0, "dust_candidate_count": 5},
            },
        }
        plan = human_loop.build_plan(perception, minimal_intention)
        ids = [s["id"] for s in plan["steps"]]
        assert "dust_dry_run_only" in ids
        assert "inspect_bad_items" not in ids

    def test_build_plan_all_steps_are_safe(self, isolated_state, minimal_perception, minimal_intention):
        """Aucune étape ne doit être destructive."""
        plan = human_loop.build_plan(minimal_perception, minimal_intention)
        for step in plan["steps"]:
            assert step.get("safe") is True
            assert step.get("destructive") is False

    def test_build_plan_requires_confirmation_for_sensitive(self, isolated_state, minimal_perception, minimal_intention):
        """Le plan déclare les actions nécessitant confirmation."""
        plan = human_loop.build_plan(minimal_perception, minimal_intention)
        assert "requires_confirmation_for" in plan
        assert len(plan["requires_confirmation_for"]) >= 3


# ============================================================
# 5. summarize_tick — fonction PURE
# ============================================================

class TestSummarizeTick:
    def test_summarize_tick_ok(self):
        """summarize_tick avec ok=True."""
        intention = {"goal": "rester prêt"}
        results = [{"ok": True}, {"ok": True}]
        text = human_loop.summarize_tick(True, intention, results)
        assert isinstance(text, str)
        assert len(text) > 0
        assert "rester prêt" in text or "prêt" in text

    def test_summarize_tick_ko(self):
        """summarize_tick avec ok=False ne crashe pas."""
        intention = {"goal": "test"}
        results = [{"ok": False, "error": "boom"}]
        text = human_loop.summarize_tick(False, intention, results)
        assert isinstance(text, str)

    def test_summarize_tick_empty_results(self):
        """summarize_tick avec results vides ne crashe pas."""
        text = human_loop.summarize_tick(True, {"goal": "x"}, [])
        assert isinstance(text, str)


# ============================================================
# 6. status — état global
# ============================================================

class TestStatus:
    def test_status_empty(self, isolated_state):
        """status() sur état vide retourne un dict complet."""
        result = human_loop.status()
        assert isinstance(result, dict)
        assert result.get("ok") is True


# ============================================================
# 7. tick — pipeline complet en mode non-execute
# ============================================================

class TestTick:
    def test_tick_no_execute(self, isolated_state):
        """tick(execute=False) fait perception + intention + plan sans exécuter."""
        result = human_loop.tick(user_goal="test tick", execute=False)
        assert isinstance(result, dict)
        # Le tick doit avoir écrit un snapshot
        assert isolated_state["snapshot"].exists()
        assert isolated_state["intent"].exists()

    def test_tick_no_execute_journal(self, isolated_state):
        """tick(execute=False) journalise au moins perception + intention + plan."""
        human_loop.tick(user_goal="test journal", execute=False)
        content = isolated_state["journal"].read_text(encoding="utf-8")
        lines = [line for line in content.strip().split("\n") if line]
        assert len(lines) >= 3
