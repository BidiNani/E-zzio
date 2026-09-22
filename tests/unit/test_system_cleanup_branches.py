"""Tests complémentaires pour system_cleanup.py : branches archives."""
from __future__ import annotations

from pathlib import Path

import pytest

from core import system_cleanup

# Retrouver la classe de cleanup
CLEANUP_CLASS = None
for name in dir(system_cleanup):
    obj = getattr(system_cleanup, name)
    if isinstance(obj, type) and "clean" in name.lower():
        CLEANUP_CLASS = obj
        break

if CLEANUP_CLASS is None:
    for name in dir(system_cleanup):
        obj = getattr(system_cleanup, name)
        if hasattr(obj, "run_cleanup"):
            CLEANUP_CLASS = type(obj)
            break


class TestArchiveDirs:
    def test_detects_archive_dir(self, tmp_path):
        """Un dossier dans ARCHIVE_DIRS est détecté et supprimé."""
        # Trouver un nom de dossier archive
        if not CLEANUP_CLASS.ARCHIVE_DIRS:
            pytest.skip("ARCHIVE_DIRS vide")

        arch_name = list(CLEANUP_CLASS.ARCHIVE_DIRS)[0]
        arch_dir = tmp_path / arch_name
        arch_dir.mkdir()
        (arch_dir / "x.txt").write_text("y")

        c = CLEANUP_CLASS(root_dir=str(tmp_path))
        result = c.run_cleanup(dry_run=True)
        # Le dossier doit être dans folders_removed
        assert len(result["folders_removed"]) >= 1

    def test_archive_dir_removed_real(self, tmp_path):
        """dry_run=False -> dossier archive supprimé."""
        if not CLEANUP_CLASS.ARCHIVE_DIRS:
            pytest.skip("ARCHIVE_DIRS vide")

        arch_name = list(CLEANUP_CLASS.ARCHIVE_DIRS)[0]
        arch_dir = tmp_path / arch_name
        arch_dir.mkdir()
        (arch_dir / "x.txt").write_text("y" * 100)

        c = CLEANUP_CLASS(root_dir=str(tmp_path))
        c.run_cleanup(dry_run=False)
        assert not arch_dir.exists()

    def test_archive_dir_in_venv_skipped(self, tmp_path):
        """.venv n'est jamais touché même pour les archives."""
        if not CLEANUP_CLASS.ARCHIVE_DIRS:
            pytest.skip("ARCHIVE_DIRS vide")

        arch_name = list(CLEANUP_CLASS.ARCHIVE_DIRS)[0]
        venv_arch = tmp_path / ".venv" / arch_name
        venv_arch.mkdir(parents=True)
        (venv_arch / "x.txt").write_text("y")

        c = CLEANUP_CLASS(root_dir=str(tmp_path))
        result = c.run_cleanup(dry_run=False)
        # Le dossier .venv/arch doit exister encore
        assert venv_arch.exists()
        # Pas dans folders_removed
        assert not any(".venv" in f for f in result["folders_removed"])


class TestMultipleExtensions:
    def test_all_log_extensions(self, tmp_path):
        """Toutes les extensions de LOG_EXTENSIONS sont testées."""
        for ext in CLEANUP_CLASS.LOG_EXTENSIONS:
            (tmp_path / f"file{ext}").write_text("x")
        c = CLEANUP_CLASS(root_dir=str(tmp_path))
        result = c.run_cleanup(dry_run=True)
        for ext in CLEANUP_CLASS.LOG_EXTENSIONS:
            assert any(f.endswith(ext) for f in result["files_removed"])


class TestUvicornProtection:
    def test_uvicorn_log_protected(self, tmp_path):
        """uvicorn.log est protégé comme discord.log."""
        (tmp_path / "uvicorn.log").write_text("active")
        c = CLEANUP_CLASS(root_dir=str(tmp_path))
        result = c.run_cleanup(dry_run=False)
        assert (tmp_path / "uvicorn.log").exists()
