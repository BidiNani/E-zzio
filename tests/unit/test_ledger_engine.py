"""Tests pour core/security/ledger_engine.py.

Le module a des effets de bord à l'import (load_dotenv, instanciation
module-level). On teste la classe LedgerEngine avec des mocks ciblés.

Découvertes pré-test :
- secrets/.env est absent → EZZIO_LEDGER_SECRET non défini
- ImmutableIdentityContext() échoue probablement sans secret → FAIL_CLOSED
- ProcessFileLock(lock_file_path, timeout) est un context manager
- LedgerArchiveEngine(rotation_threshold).check_and_rotate() → bool
"""
from __future__ import annotations

import hashlib
import hmac
import json
import os
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from core.security import ledger_engine
from core.security.ledger_engine import LedgerEngine

# ============================================================
# Fixtures
# ============================================================

@pytest.fixture
def mock_archiver(monkeypatch):
    """Remplace LedgerArchiveEngine par un mock no-op."""
    fake = MagicMock()
    fake.check_and_rotate = MagicMock(return_value=True)
    monkeypatch.setattr(ledger_engine, "LedgerArchiveEngine", lambda **kwargs: fake)
    return fake


@pytest.fixture
def mock_identity_ok(monkeypatch):
    """ImmutableIdentityContext mocké qui réussit toujours."""
    class FakeCtx:
        def __init__(self):
            self.identity_root_hash = "a" * 64
            self.signature = "b" * 64

    monkeypatch.setattr(ledger_engine, "ImmutableIdentityContext", FakeCtx)
    return FakeCtx


@pytest.fixture
def mock_lock_noop(monkeypatch):
    """ProcessFileLock mocké en no-op (pas de vrai verrou fichier)."""
    class FakeLock:
        def __init__(self, *args, **kwargs):
            pass
        def __enter__(self):
            return self
        def __exit__(self, *args):
            return False

    monkeypatch.setattr(ledger_engine, "ProcessFileLock", FakeLock)
    return FakeLock


@pytest.fixture
def isolated_ledger_path(monkeypatch, tmp_path):
    """Redirige LEDGER_PATH vers tmp_path."""
    ledger_path = tmp_path / "decisions" / "router_decisions.jsonl"
    monkeypatch.setattr(ledger_engine, "LEDGER_PATH", ledger_path)
    return ledger_path


# ============================================================
# 1. Smoke
# ============================================================

class TestSmoke:
    def test_module_imports(self):
        assert ledger_engine is not None

    def test_class_exists(self):
        assert LedgerEngine is not None

    def test_module_level_instance_exists(self):
        """Le module crée une instance ledger_engine à l'import."""
        assert ledger_engine.ledger_engine is not None
        assert isinstance(ledger_engine.ledger_engine, LedgerEngine)


# ============================================================
# 2. __init__ — modes
# ============================================================

class TestInit:
    def test_no_secret_leads_to_fail_closed(self, mock_archiver, monkeypatch, mock_identity_ok):
        """Sans EZZIO_LEDGER_SECRET → FAIL_CLOSED."""
        monkeypatch.delenv("EZZIO_LEDGER_SECRET", raising=False)
        engine = LedgerEngine(archive_threshold=100)
        assert engine.system_mode == "FAIL_CLOSED"

    def test_with_secret_and_identity_ok(self, mock_archiver, mock_identity_ok, monkeypatch):
        """Avec secret + identité OK → NORMAL."""
        monkeypatch.setenv("EZZIO_LEDGER_SECRET", "supersecret")
        engine = LedgerEngine(archive_threshold=100)
        assert engine.system_mode == "NORMAL"

    def test_with_secret_but_identity_fails(self, mock_archiver, monkeypatch):
        """Avec secret mais identité qui échoue → FAIL_CLOSED."""
        monkeypatch.setenv("EZZIO_LEDGER_SECRET", "supersecret")

        class BadCtx:
            def __init__(self):
                raise RuntimeError("identity fail")

        monkeypatch.setattr(ledger_engine, "ImmutableIdentityContext", BadCtx)
        engine = LedgerEngine(archive_threshold=100)
        assert engine.system_mode == "FAIL_CLOSED"

    def test_archiver_created_with_threshold(self, monkeypatch, mock_identity_ok):
        """L'archiver est instancié avec le threshold passé."""
        captured = {}

        class FakeArchiver:
            def __init__(self, rotation_threshold=5000):
                captured["threshold"] = rotation_threshold

        monkeypatch.setattr(ledger_engine, "LedgerArchiveEngine", FakeArchiver)
        monkeypatch.setenv("EZZIO_LEDGER_SECRET", "s")
        LedgerEngine(archive_threshold=1234)
        assert captured["threshold"] == 1234


# ============================================================
# 3. _get_last_sequence_and_hash
# ============================================================

class TestGetLastSequenceAndHash:
    def test_no_file(self, mock_archiver, monkeypatch, mock_identity_ok, isolated_ledger_path):
        """Sans fichier → (0, '0'*64)."""
        monkeypatch.setenv("EZZIO_LEDGER_SECRET", "s")
        engine = LedgerEngine()
        seq, h = engine._get_last_sequence_and_hash()
        assert seq == 0
        assert h == "0" * 64

    def test_empty_file(self, mock_archiver, monkeypatch, mock_identity_ok, isolated_ledger_path):
        """Fichier vide → (0, '0'*64)."""
        monkeypatch.setenv("EZZIO_LEDGER_SECRET", "s")
        isolated_ledger_path.parent.mkdir(parents=True, exist_ok=True)
        isolated_ledger_path.write_text("", encoding="utf-8")
        engine = LedgerEngine()
        seq, h = engine._get_last_sequence_and_hash()
        assert seq == 0
        assert h == "0" * 64

    def test_one_record(self, mock_archiver, monkeypatch, mock_identity_ok, isolated_ledger_path):
        """Un enregistrement → (seq, hash)."""
        monkeypatch.setenv("EZZIO_LEDGER_SECRET", "s")
        isolated_ledger_path.parent.mkdir(parents=True, exist_ok=True)
        rec = {"sequence": 5, "hash": "c" * 64, "data": "x"}
        isolated_ledger_path.write_text(json.dumps(rec) + "\n", encoding="utf-8")
        engine = LedgerEngine()
        seq, h = engine._get_last_sequence_and_hash()
        assert seq == 5
        assert h == "c" * 64

    def test_multiple_records_returns_last(self, mock_archiver, monkeypatch, mock_identity_ok, isolated_ledger_path):
        """Plusieurs enregistrements → retourne le dernier."""
        monkeypatch.setenv("EZZIO_LEDGER_SECRET", "s")
        isolated_ledger_path.parent.mkdir(parents=True, exist_ok=True)
        lines = [
            json.dumps({"sequence": 1, "hash": "a" * 64}),
            json.dumps({"sequence": 2, "hash": "b" * 64}),
            json.dumps({"sequence": 3, "hash": "c" * 64}),
        ]
        isolated_ledger_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
        engine = LedgerEngine()
        seq, h = engine._get_last_sequence_and_hash()
        assert seq == 3
        assert h == "c" * 64

    def test_corrupted_file_returns_defaults(self, mock_archiver, monkeypatch, mock_identity_ok, isolated_ledger_path):
        """Fichier JSON corrompu → (0, '0'*64)."""
        monkeypatch.setenv("EZZIO_LEDGER_SECRET", "s")
        isolated_ledger_path.parent.mkdir(parents=True, exist_ok=True)
        isolated_ledger_path.write_text("NOT JSON {{{", encoding="utf-8")
        engine = LedgerEngine()
        seq, h = engine._get_last_sequence_and_hash()
        assert seq == 0
        assert h == "0" * 64


# ============================================================
# 4. commit_transaction — modes
# ============================================================

class TestCommitTransactionFailClosed:
    def test_fails_without_secret(self, mock_archiver, monkeypatch, mock_identity_ok, mock_lock_noop):
        """Sans secret → FAIL_CLOSED → commit retourne False."""
        monkeypatch.delenv("EZZIO_LEDGER_SECRET", raising=False)
        engine = LedgerEngine()
        assert engine.system_mode == "FAIL_CLOSED"
        result = engine.commit_transaction(
            intent="test", request_id="r1", candidates=[], selected="none", state="proposed"
        )
        assert result is False

    def test_fails_if_identity_drifts(self, mock_archiver, monkeypatch, mock_lock_noop):
        """Si l'identité change entre boot et commit → False."""
        monkeypatch.setenv("EZZIO_LEDGER_SECRET", "s")

        # 1ère instanciation : boot_identity_root = "a"*64
        class CtxV1:
            def __init__(self):
                self.identity_root_hash = "a" * 64
                self.signature = "sig_a"

        monkeypatch.setattr(ledger_engine, "ImmutableIdentityContext", CtxV1)
        engine = LedgerEngine()
        assert engine.system_mode == "NORMAL"

        # 2e instanciation : identité différente
        class CtxV2:
            def __init__(self):
                self.identity_root_hash = "b" * 64
                self.signature = "sig_b"

        monkeypatch.setattr(ledger_engine, "ImmutableIdentityContext", CtxV2)
        result = engine.commit_transaction(
            intent="x", request_id="r", candidates=[], selected="n", state="s"
        )
        assert result is False
        assert engine.system_mode == "FAIL_CLOSED"

    def test_fails_if_current_ctx_raises(self, mock_archiver, monkeypatch, mock_identity_ok, mock_lock_noop):
        """Si ImmutableIdentityContext() lève au commit → False."""
        monkeypatch.setenv("EZZIO_LEDGER_SECRET", "s")
        engine = LedgerEngine()
        assert engine.system_mode == "NORMAL"

        class BadCtx:
            def __init__(self):
                raise RuntimeError("drift detected")

        monkeypatch.setattr(ledger_engine, "ImmutableIdentityContext", BadCtx)
        result = engine.commit_transaction(
            intent="x", request_id="r", candidates=[], selected="n", state="s"
        )
        assert result is False
        assert engine.system_mode == "FAIL_CLOSED"


class TestCommitTransactionNormal:
    def test_writes_record(
        self,
        mock_archiver,
        mock_identity_ok,
        mock_lock_noop,
        monkeypatch,
        isolated_ledger_path,
    ):
        """En mode NORMAL, commit écrit un enregistrement complet."""
        monkeypatch.setenv("EZZIO_LEDGER_SECRET", "supersecret")
        engine = LedgerEngine()
        assert engine.system_mode == "NORMAL"

        result = engine.commit_transaction(
            intent="route",
            request_id="req-42",
            candidates=["a", "b"],
            selected="a",
            state="executed",
            execution_details={"latency_ms": 100},
        )
        assert result is True
        assert isolated_ledger_path.exists()

        # Vérifier le contenu
        line = isolated_ledger_path.read_text(encoding="utf-8").strip()
        rec = json.loads(line)
        assert rec["sequence"] == 1
        assert rec["intent"] == "route"
        assert rec["request_id"] == "req-42"
        assert rec["selected"] == "a"
        assert rec["transaction_state"] == "executed"
        assert rec["previous_hash"] == "0" * 64
        assert "hash" in rec
        assert "signature" in rec
        assert len(rec["hash"]) == 64
        assert len(rec["signature"]) == 64

    def test_chains_sequences(
        self,
        mock_archiver,
        mock_identity_ok,
        mock_lock_noop,
        monkeypatch,
        isolated_ledger_path,
    ):
        """Deux commits → sequence 1, 2 et chaining."""
        monkeypatch.setenv("EZZIO_LEDGER_SECRET", "s")
        engine = LedgerEngine()

        engine.commit_transaction("i1", "r1", [], "a", "s1")
        engine.commit_transaction("i2", "r2", [], "b", "s2")

        lines = isolated_ledger_path.read_text(encoding="utf-8").strip().splitlines()
        assert len(lines) == 2
        r1 = json.loads(lines[0])
        r2 = json.loads(lines[1])
        assert r1["sequence"] == 1
        assert r2["sequence"] == 2
        assert r2["previous_hash"] == r1["hash"]

    def test_hmac_signature_is_deterministic(
        self,
        mock_archiver,
        mock_identity_ok,
        mock_lock_noop,
        monkeypatch,
        isolated_ledger_path,
    ):
        """La signature HMAC dépend du secret + seq + previous_hash + hash."""
        monkeypatch.setenv("EZZIO_LEDGER_SECRET", "fixed-secret")
        engine = LedgerEngine()
        engine.commit_transaction("i", "r", [], "a", "s")

        rec = json.loads(isolated_ledger_path.read_text(encoding="utf-8").strip())
        # Recalculer la signature
        payload = f"{rec['sequence']}:{rec['previous_hash']}:{rec['hash']}".encode()
        expected_sig = hmac.new(b"fixed-secret", payload, hashlib.sha256).hexdigest()
        assert rec["signature"] == expected_sig

    def test_archiver_called(
        self,
        mock_archiver,
        mock_identity_ok,
        mock_lock_noop,
        monkeypatch,
        isolated_ledger_path,
    ):
        """commit_transaction appelle archiver.check_and_rotate()."""
        monkeypatch.setenv("EZZIO_LEDGER_SECRET", "s")
        engine = LedgerEngine()
        engine.commit_transaction("i", "r", [], "a", "s")
        assert mock_archiver.check_and_rotate.called


# ============================================================
# 5. Autres branches
# ============================================================

class TestEdgeCases:
    def test_commit_with_execution_details_none(
        self,
        mock_archiver,
        mock_identity_ok,
        mock_lock_noop,
        monkeypatch,
        isolated_ledger_path,
    ):
        """execution_details=None → devient {} dans le record."""
        monkeypatch.setenv("EZZIO_LEDGER_SECRET", "s")
        engine = LedgerEngine()
        engine.commit_transaction("i", "r", [], "a", "s", execution_details=None)
        rec = json.loads(isolated_ledger_path.read_text(encoding="utf-8").strip())
        assert rec["execution_details"] == {}

    def test_commit_with_custom_execution_details(
        self,
        mock_archiver,
        mock_identity_ok,
        mock_lock_noop,
        monkeypatch,
        isolated_ledger_path,
    ):
        """execution_details custom → préservé."""
        monkeypatch.setenv("EZZIO_LEDGER_SECRET", "s")
        engine = LedgerEngine()
        details = {"latency_ms": 42, "cache_hit": True}
        engine.commit_transaction("i", "r", [], "a", "s", execution_details=details)
        rec = json.loads(isolated_ledger_path.read_text(encoding="utf-8").strip())
        assert rec["execution_details"] == details
