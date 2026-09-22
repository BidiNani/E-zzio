"""Tests pour core/safe_actions.py.

Stratégie : les chemins QUEUE_PATH et RUNS_PATH sont module-level
(Path("G:/AI/E-zzio/state/safe_actions/...")). On les redirige vers
tmp_path via monkeypatch pour ne pas polluer l'état réel du projet.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from core import safe_actions

# ============================================================
# Fixtures
# ============================================================

@pytest.fixture
def isolated_state(monkeypatch, tmp_path):
    """Redirige QUEUE_PATH et RUNS_PATH vers tmp_path pour isolation."""
    queue_root = tmp_path / "safe_actions"
    queue_root.mkdir(parents=True, exist_ok=True)
    queue_path = queue_root / "queue.jsonl"
    runs_path = queue_root / "runs.jsonl"

    monkeypatch.setattr(safe_actions, "QUEUE_ROOT", queue_root)
    monkeypatch.setattr(safe_actions, "QUEUE_PATH", queue_path)
    monkeypatch.setattr(safe_actions, "RUNS_PATH", runs_path)

    return {"queue": queue_path, "runs": runs_path, "root": queue_root}


# ============================================================
# 1. Smoke tests
# ============================================================

class TestSmoke:
    def test_module_imports(self):
        """Le module s'importe sans erreur."""
        assert safe_actions is not None

    def test_action_registry_is_dict(self):
        """ACTION_REGISTRY est bien un dict."""
        assert isinstance(safe_actions.ACTION_REGISTRY, dict)

    def test_registry_returns_ok(self):
        """registry() retourne un dict avec ok=True."""
        result = safe_actions.registry()
        assert isinstance(result, dict)
        assert result["ok"] is True
        assert "actions" in result
        assert "version" in result
        assert "policy" in result


# ============================================================
# 2. Fonctions pures
# ============================================================

class TestPureFunctions:
    def test_now_format(self):
        """now() retourne un timestamp ISO-like."""
        ts = safe_actions.now()
        assert isinstance(ts, str)
        # Format attendu : %Y-%m-%dT%H:%M:%S
        assert len(ts) >= 19
        assert "T" in ts

    def test_read_jsonl_nonexistent(self, tmp_path):
        """read_jsonl sur fichier inexistant retourne []."""
        missing = tmp_path / "nope.jsonl"
        result = safe_actions.read_jsonl(missing)
        assert result == []

    def test_read_jsonl_valid(self, tmp_path):
        """read_jsonl lit des lignes JSON valides."""
        f = tmp_path / "test.jsonl"
        f.write_text(
            '{"a": 1}\n{"b": 2}\n',
            encoding="utf-8",
        )
        result = safe_actions.read_jsonl(f)
        assert result == [{"a": 1}, {"b": 2}]

    def test_read_jsonl_with_broken_line(self, tmp_path):
        """read_jsonl capture les lignes cassées avec broken_line."""
        f = tmp_path / "test.jsonl"
        f.write_text('{"ok": true}\nNOT JSON\n', encoding="utf-8")
        result = safe_actions.read_jsonl(f)
        assert len(result) == 2
        assert result[0] == {"ok": True}
        assert "broken_line" in result[1]

    def test_read_jsonl_respects_limit(self, tmp_path):
        """read_jsonl ne renvoie que les N dernières lignes."""
        f = tmp_path / "test.jsonl"
        lines = "\n".join(f'{{"i": {i}}}' for i in range(10))
        f.write_text(lines + "\n", encoding="utf-8")
        result = safe_actions.read_jsonl(f, limit=3)
        assert len(result) == 3
        assert result[-1] == {"i": 9}

    def test_append_jsonl_creates_file(self, tmp_path):
        """append_jsonl crée le fichier et ajoute la ligne."""
        f = tmp_path / "sub" / "test.jsonl"
        safe_actions.append_jsonl(f, {"event": "test"})
        assert f.exists()
        content = f.read_text(encoding="utf-8")
        assert json.loads(content.strip()) == {"event": "test"}


# ============================================================
# 3. propose_action
# ============================================================

class TestProposeAction:
    def test_propose_unknown_action(self, isolated_state):
        """Action inconnue retourne ok=False."""
        result = safe_actions.propose_action("__nonexistent_action__")
        assert result["ok"] is False
        assert "error" in result
        assert "known_actions" in result

    def test_propose_destructive_refused(self, isolated_state):
        """Action destructive est refusée."""
        # On cherche une action destructive dans le registre
        destructive = [
            name for name, spec in safe_actions.ACTION_REGISTRY.items()
            if spec.get("destructive") or not spec.get("safe")
        ]
        if not destructive:
            pytest.skip("Aucune action destructive dans le registre")

        result = safe_actions.propose_action(destructive[0])
        assert result["ok"] is False

    def test_propose_valid_action(self, isolated_state):
        """Action valide crée une proposition avec UUID."""
        # On cherche une action safe et non-destructive
        safe_actions_list = [
            name for name, spec in safe_actions.ACTION_REGISTRY.items()
            if spec.get("safe") and not spec.get("destructive")
        ]
        if not safe_actions_list:
            pytest.skip("Aucune action safe dans le registre")

        result = safe_actions.propose_action(safe_actions_list[0], reason="test")
        assert result["ok"] is True
        assert "id" in result
        assert result["action"] == safe_actions_list[0]
        assert result["status"] == "proposed"
        assert result["reason"] == "test"

        # Le fichier queue.jsonl doit contenir la proposition
        assert isolated_state["queue"].exists()
        lines = isolated_state["queue"].read_text(encoding="utf-8").strip().split("\n")
        assert len(lines) == 1
        assert json.loads(lines[0])["id"] == result["id"]


# ============================================================
# 4. queue / ledger / status
# ============================================================

class TestQueueLedgerStatus:
    def test_queue_empty(self, isolated_state):
        """queue() sur état vide retourne count=0."""
        result = safe_actions.queue()
        assert result["ok"] is True
        assert result["count"] == 0
        assert result["items"] == []

    def test_ledger_empty(self, isolated_state):
        """ledger() sur état vide retourne des compteurs à 0."""
        result = safe_actions.ledger()
        assert result["ok"] is True
        assert result["count"] == 0
        assert result["executed_count"] == 0
        assert result["pending_count"] == 0

    def test_status_empty(self, isolated_state):
        """status() retourne un dict complet même sur état vide."""
        result = safe_actions.status()
        assert result["ok"] is True
        assert "queue_path" in result
        assert "runs_path" in result
        assert "known_actions" in result
        assert result["queued_count"] == 0

    def test_queue_after_propose(self, isolated_state):
        """Après propose_action, queue() contient la proposition."""
        safe_list = [
            name for name, spec in safe_actions.ACTION_REGISTRY.items()
            if spec.get("safe") and not spec.get("destructive")
        ]
        if not safe_list:
            pytest.skip("Aucune action safe dans le registre")

        proposal = safe_actions.propose_action(safe_list[0])
        result = safe_actions.queue()
        assert result["count"] == 1
        assert result["items"][0]["id"] == proposal["id"]


# ============================================================
# 5. run_proposal (cas limites)
# ============================================================

class TestRunProposal:
    def test_run_nonexistent_proposal(self, isolated_state):
        """run_proposal sur ID inconnu ne doit pas crasher."""
        result = safe_actions.run_proposal("__no_such_id__")
        # Le comportement exact dépend de l'implémentation :
        # soit ok=False, soit une erreur structurée.
        assert isinstance(result, dict)

    def test_cancel_nonexistent_proposal(self, isolated_state):
        """cancel_proposal sur ID inconnu ne doit pas crasher."""
        result = safe_actions.cancel_proposal("__no_such_id__")
        assert isinstance(result, dict)

    def test_find_proposal_not_found(self, isolated_state):
        """find_proposal sur ID inconnu retourne None."""
        result = safe_actions.find_proposal("__no_such_id__")
        assert result is None
