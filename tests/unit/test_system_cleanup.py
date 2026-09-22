"""Tests réels pour core/system_cleanup.py.

SystemCleanup : nettoyage sécurisé des archives / logs / temporaires.
- dry_run=True : aucune suppression, retourne les candidats
- dry_run=False : suppression réelle
- protections : .venv ignoré, discord.log/uvicorn.log conservés
"""
from __future__ import annotations

from pathlib import Path

import pytest

# Import adaptatif (nom de classe à vérifier dans le module)
from core import system_cleanup

# Trouver la classe de cleanup dans le module
CLEANUP_CLASS = None
for name in dir(system_cleanup):
    obj = getattr(system_cleanup, name)
    if isinstance(obj, type) and "clean" in name.lower():
        CLEANUP_CLASS = obj
        break

if CLEANUP_CLASS is None:
    # Fallback : chercher un attribut qui a run_cleanup
    for name in dir(system_cleanup):
        obj = getattr(system_cleanup, name)
        if hasattr(obj, "run_cleanup"):
            CLEANUP_CLASS = type(obj)
            break


# ============================================================
# 1. Smoke
# ============================================================

class TestSmoke:
    def test_module_imports(self):
        assert system_cleanup is not None

    def test_module_file(self):
        assert Path(system_cleanup.__file__).exists()

    def test_cleanup_class_found(self):
        """Une classe de cleanup doit être trouvée."""
        assert CLEANUP_CLASS is not None, "Aucune classe de cleanup trouvée"


# ============================================================
# 2. Init
# ============================================================

class TestInit:
    def test_init_default(self):
        """Init avec root_dir par défaut."""
        c = CLEANUP_CLASS()
        assert c is not None

    def test_init_custom_root(self, tmp_path):
        c = CLEANUP_CLASS(root_dir=str(tmp_path))
        assert c.root == tmp_path.resolve()

    def test_archive_dirs_constant(self):
        assert hasattr(CLEANUP_CLASS, "ARCHIVE_DIRS")
        assert isinstance(CLEANUP_CLASS.ARCHIVE_DIRS, set)

    def test_log_extensions_constant(self):
        assert hasattr(CLEANUP_CLASS, "LOG_EXTENSIONS")
        assert isinstance(CLEANUP_CLASS.LOG_EXTENSIONS, set)


# ============================================================
# 3. run_cleanup — dry run
# ============================================================

class TestRunCleanupDry:
    def test_dry_run_on_empty_dir(self, tmp_path):
        """Dossier vide -> listes vides, rien supprimé."""
        c = CLEANUP_CLASS(root_dir=str(tmp_path))
        result = c.run_cleanup(dry_run=True)
        assert isinstance(result, dict)
        assert "folders_removed" in result
        assert "files_removed" in result
        assert result["space_freed_bytes"] == 0

    def test_dry_run_detects_log_file(self, tmp_path):
        """Un .log -> détecté, pas supprimé."""
        log = tmp_path / "test.log"
        log.write_text("log content")
        c = CLEANUP_CLASS(root_dir=str(tmp_path))
        result = c.run_cleanup(dry_run=True)
        assert "test.log" in result["files_removed"]
        # Fichier toujours présent
        assert log.exists()

    def test_dry_run_multiple_log_extensions(self, tmp_path):
        """Toutes les extensions de LOG_EXTENSIONS sont détectées."""
        for ext in [".log", ".tmp", ".bak", ".old"]:
            (tmp_path / f"file{ext}").write_text("x")
        c = CLEANUP_CLASS(root_dir=str(tmp_path))
        result = c.run_cleanup(dry_run=True)
        assert len(result["files_removed"]) >= 4

    def test_dry_run_skips_venv(self, tmp_path):
        """.venv est ignoré."""
        venv = tmp_path / ".venv" / "test.log"
        venv.parent.mkdir()
        venv.write_text("x")
        c = CLEANUP_CLASS(root_dir=str(tmp_path))
        result = c.run_cleanup(dry_run=True)
        # Le fichier dans .venv ne doit PAS être listé
        assert not any(".venv" in f for f in result["files_removed"])

    def test_dry_run_skips_discord_log(self, tmp_path):
        """discord.log est protégé (log actif)."""
        (tmp_path / "discord.log").write_text("active log")
        c = CLEANUP_CLASS(root_dir=str(tmp_path))
        result = c.run_cleanup(dry_run=True)
        # Le fichier doit être dans files_skipped, pas files_removed
        assert not any("discord.log" in f and "(actif)" not in f
                       for f in result["files_removed"])


# ============================================================
# 4. run_cleanup — réel (suppression)
# ============================================================

class TestRunCleanupReal:
    def test_real_removes_log_file(self, tmp_path):
        """dry_run=False -> le fichier est supprimé."""
        log = tmp_path / "test.log"
        log.write_text("log content")
        c = CLEANUP_CLASS(root_dir=str(tmp_path))
        result = c.run_cleanup(dry_run=False)
        assert not log.exists()
        assert "test.log" in result["files_removed"]

    def test_real_frees_space(self, tmp_path):
        """L'espace libéré est comptabilisé."""
        (tmp_path / "big.log").write_text("x" * 1000)
        c = CLEANUP_CLASS(root_dir=str(tmp_path))
        result = c.run_cleanup(dry_run=False)
        assert result["space_freed_bytes"] >= 1000

    def test_real_skips_venv(self, tmp_path):
        """.venv reste intact."""
        venv_log = tmp_path / ".venv" / "test.log"
        venv_log.parent.mkdir()
        venv_log.write_text("x")
        c = CLEANUP_CLASS(root_dir=str(tmp_path))
        c.run_cleanup(dry_run=False)
        assert venv_log.exists()

    def test_real_protects_discord_log(self, tmp_path):
        """discord.log survit au nettoyage."""
        active = tmp_path / "discord.log"
        active.write_text("active")
        c = CLEANUP_CLASS(root_dir=str(tmp_path))
        c.run_cleanup(dry_run=False)
        assert active.exists()


# ============================================================
# 5. Options désactivées
# ============================================================

class TestOptions:
    def test_remove_logs_false(self, tmp_path):
        """remove_logs=False -> pas de suppression des logs."""
        (tmp_path / "test.log").write_text("x")
        c = CLEANUP_CLASS(root_dir=str(tmp_path))
        result = c.run_cleanup(dry_run=False, remove_logs=False, remove_temp=False)
        assert (tmp_path / "test.log").exists()

    def test_remove_archives_false(self, tmp_path):
        """remove_archives=False -> pas de suppression des dossiers archives."""
        arch = tmp_path / "archive_old"
        arch.mkdir()
        (arch / "x.txt").write_text("y")
        c = CLEANUP_CLASS(root_dir=str(tmp_path))
        result = c.run_cleanup(dry_run=False, remove_archives=False)
        assert arch.exists()


# ============================================================
# 6. Structure résultat
# ============================================================

class TestResultStructure:
    def test_all_keys_present(self, tmp_path):
        c = CLEANUP_CLASS(root_dir=str(tmp_path))
        result = c.run_cleanup(dry_run=True)
        for key in ["folders_removed", "folders_skipped",
                    "files_removed", "files_skipped", "space_freed_bytes"]:
            assert key in result

    def test_sorted_lists(self, tmp_path):
        for name in ["a.log", "b.log", "c.log"]:
            (tmp_path / name).write_text("x")
        c = CLEANUP_CLASS(root_dir=str(tmp_path))
        result = c.run_cleanup(dry_run=True)
        assert result["files_removed"] == sorted(result["files_removed"])
