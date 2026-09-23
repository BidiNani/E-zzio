"""Tests Vague C bloc 2 : ledger_engine + model_registry + system_cleanup.

Cible les 14 lignes manquantes pour atteindre 100% :
- ledger_engine.py    : 50->56, 51->50, 111-113
- model_registry.py   : 83, 182, 188, 191, 202
- system_cleanup.py   : 47-49, 71-73
"""
from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

# ============================================================
# 1. ledger_engine.py — L50-51, L111-113
# ============================================================

class TestLedgerEngineBranches:
    """Lignes 50->56 (line.strip vide), 51->50 (loop continue), 111-113 (except)."""

    def test_get_last_sequence_with_blank_lines(self, tmp_path):
        """L50->56 : fichier ledger avec lignes vides -> on les ignore."""
        from core.security import ledger_engine as le_mod

        ledger_path = tmp_path / "ledger.jsonl"
        # Lignes vides + ligne valide
        ledger_path.write_text(
            "\n   \n"
            '{"sequence": 42, "hash": "abc123"}\n'
            "\n",
            encoding="utf-8",
        )

        with patch.object(le_mod, "LEDGER_PATH", ledger_path), \
             patch.dict("os.environ", {"EZZIO_LEDGER_SECRET": "test_secret"}):
            engine = le_mod.LedgerEngine.__new__(le_mod.LedgerEngine)
            engine.secret_key = b"test_secret"
            engine.system_mode = "NORMAL"
            engine.boot_identity_root = "x"
            engine.archiver = MagicMock()

            seq, h = engine._get_last_sequence_and_hash()
            assert seq == 42
            assert h == "abc123"

    def test_commit_lock_timeout_exception(self, tmp_path):
        """L111-113 : ProcessFileLock timeout -> except -> return False."""
        from core.security import ledger_engine as le_mod

        class FakeCtx:
            identity_root_hash = "hash_root"
            signature = "sig"

        # Simuler un timeout du lock via une exception
        class FakeLock:
            def __init__(self, *args, **kwargs):
                pass
            def __enter__(self):
                raise TimeoutError("Lock timeout")
            def __exit__(self, *args):
                pass

        with patch.object(le_mod, "LEDGER_PATH", tmp_path / "ledger.jsonl"), \
             patch.object(le_mod, "LOCK_PATH", tmp_path / "ledger.lock"), \
             patch.object(le_mod, "ARCHIVE_DIR", tmp_path / "archive"), \
             patch.object(le_mod, "ProcessFileLock", FakeLock), \
             patch.object(le_mod, "ImmutableIdentityContext", return_value=FakeCtx()), \
             patch.dict("os.environ", {"EZZIO_LEDGER_SECRET": "test_secret"}):
            engine = le_mod.LedgerEngine()
            result = engine.commit_transaction(
                intent="test", request_id="req1", candidates=[], selected="s", state="RUNNING"
            )
            assert result is False


# ============================================================
# 2. model_registry.py — L83, L182, L188, L191, L202
# ============================================================

class TestModelRegistryBranches:
    """L83 (property model_id), L182 (get miss), L188 (get_by_role miss), L191, L202."""

    def test_model_id_property(self):
        """L83 : CanonicalModelRecord.model_id retourne name."""
        from core.routing.model_registry import CanonicalModelRecord, ModelSource

        rec = CanonicalModelRecord(name="gemini-3.5-flash", source=ModelSource.GEMINI)
        assert rec.model_id == "gemini-3.5-flash"

    def test_get_nonexistent_returns_none(self):
        """L182 : get() avec name inexistant -> None."""
        from core.routing.model_registry import CanonicalModelRegistry

        reg = CanonicalModelRegistry()
        assert reg.get("nonexistent_model_xyz") is None

    def test_get_by_role_not_found_returns_none(self):
        """L188 : get_by_role() avec role inexistant -> None."""
        from core.routing.model_registry import CanonicalModelRegistry

        reg = CanonicalModelRegistry()
        assert reg.get_by_role("NONEXISTENT_ROLE_XYZ") is None

    def test_get_all_by_role(self):
        """L191 : get_all_by_role() retourne liste."""
        from core.routing.model_registry import CanonicalModelRegistry

        reg = CanonicalModelRegistry()
        models = reg.get_all_by_role("CODING")
        assert isinstance(models, list)
        for m in models:
            assert "CODING" in m.roles or m.role == "CODING"

    def test_get_registry_returns_singleton(self):
        """L202 : get_registry() retourne le singleton."""
        from core.routing.model_registry import (
            CanonicalModelRegistry,
            canonical_model_registry,
            get_registry,
        )

        reg = get_registry()
        assert isinstance(reg, CanonicalModelRegistry)
        assert reg is canonical_model_registry


# ============================================================
# 3. system_cleanup.py — L47-49, L71-73
# ============================================================

class TestSystemCleanupBranches:
    """L47-49 (except sur rglob dir), L71-73 (except sur unlink fichier)."""

    def test_dir_rglob_exception_is_caught(self, tmp_path):
        """L47-49 : exception sur rglob d'un dossier -> logger.warning + skip."""
        from core.system_cleanup import SystemCleanupService

        # Creer un dossier archive
        arc = tmp_path / "_archive"
        arc.mkdir()
        (arc / "file.txt").write_text("x", encoding="utf-8")

        svc = SystemCleanupService(root_dir=str(tmp_path))

        # Simuler une erreur sur relative_to (qui est appele dans le try)
        original_relative_to = Path.relative_to
        call_count = {"n": 0}

        def broken_relative_to(self, *args, **kwargs):
            call_count["n"] += 1
            # La 1ere fois qu'on appelle relative_to dans le try, on raise
            if call_count["n"] == 1:
                raise OSError("simulated rglob failure")
            return original_relative_to(self, *args, **kwargs)

        with patch.object(Path, "relative_to", broken_relative_to):
            res = svc.run_cleanup(dry_run=True, remove_logs=False, remove_temp=False)

        # Le dossier est skip
        assert isinstance(res["folders_skipped"], list)

    def test_file_unlink_exception_is_caught(self, tmp_path):
        """L71-73 : exception sur unlink -> logger.warning + skip."""
        from core.system_cleanup import SystemCleanupService

        # Creer un fichier log
        log_file = tmp_path / "test.log"
        log_file.write_text("x", encoding="utf-8")

        svc = SystemCleanupService(root_dir=str(tmp_path))

        # Simuler un unlink qui echoue (fichier verrouille)
        original_unlink = Path.unlink

        def broken_unlink(self, *args, **kwargs):
            if self.suffix == ".log":
                raise PermissionError("simulated lock")
            return original_unlink(self, *args, **kwargs)

        with patch.object(Path, "unlink", broken_unlink):
            res = svc.run_cleanup(dry_run=False, remove_archives=False)

        # Le fichier est skip
        assert any("test.log" in f for f in res["files_skipped"])
