"""Tests pour core/coding/bridge.py.

Contrat durci (finalisation produit) : le bridge n'expose que du git en
LECTURE SEULE. Les opérations destructrices ou de publication (restore, reset,
clean, checkout, stash, commit, push, pull, merge, rebase, cherry-pick, ...)
sont refusées par défaut — y compris en dry_run et via run_command("git", ...).
"""
from __future__ import annotations

import pytest

from core.coding.bridge import (
    ALLOWED_GIT_COMMANDS,
    ALLOWED_SHELL_COMMANDS,
    GIT_MUTATING_OPERATIONS,
    InternalToolBridge,
)


@pytest.fixture
def bridge(tmp_path):
    return InternalToolBridge(root_dir=tmp_path, dry_run=True)


@pytest.fixture
def real_bridge(tmp_path):
    return InternalToolBridge(root_dir=tmp_path, dry_run=False)


class TestInternalToolBridgeInit:
    def test_init_ok(self, tmp_path):
        b = InternalToolBridge(root_dir=tmp_path)
        assert b.root_dir == tmp_path.resolve()
        assert b.dry_run is False

    def test_init_missing_dir_raises(self, tmp_path):
        with pytest.raises(ValueError):
            InternalToolBridge(root_dir=tmp_path / "does_not_exist")


class TestFileOperations:
    def test_read_missing_file(self, bridge):
        result = bridge.read_file("does_not_exist.txt")
        assert result.success is False

    def test_write_dry_run(self, bridge):
        result = bridge.write_file("foo.txt", "bar")
        assert result.success is True
        assert result.dry_run is True

    def test_write_then_read(self, real_bridge):
        w = real_bridge.write_file("foo.txt", "bar")
        assert w.success is True
        r = real_bridge.read_file("foo.txt")
        assert r.success is True
        assert r.stdout == "bar"

    def test_write_hors_workspace(self, real_bridge):
        result = real_bridge.write_file("../outside.txt", "bad")
        assert result.success is False
        assert "hors workspace" in result.error.lower()

    def test_file_exists(self, real_bridge):
        assert real_bridge.file_exists("foo.txt") is False
        real_bridge.write_file("foo.txt", "bar")
        assert real_bridge.file_exists("foo.txt") is True

    def test_list_files(self, real_bridge):
        real_bridge.write_file("a.txt", "a")
        real_bridge.write_file("b.txt", "b")
        files = real_bridge.list_files()
        assert len(files) >= 2


class TestShellCommands:
    def test_command_not_allowed(self, bridge):
        result = bridge.run_command("rm", ["-rf", "/"])
        assert result.success is False
        assert "non autorisée" in result.error

    def test_echo_allowed_dry_run(self, bridge):
        result = bridge.run_command("echo", ["hello"])
        assert result.success is True
        assert result.dry_run is True

    def test_ruff_allowed(self):
        assert "ruff" in ALLOWED_SHELL_COMMANDS

    def test_pytest_allowed(self):
        assert "pytest" in ALLOWED_SHELL_COMMANDS

    def test_git_allowed(self):
        assert "git" in ALLOWED_SHELL_COMMANDS


class TestGitCommands:
    # ---- Refus fail-closed des opérations destructrices / publication ----

    @pytest.mark.parametrize(
        "args",
        [
            ("reset",),
            ("reset", "--hard", "HEAD"),
            ("restore", "."),
            ("restore", "foo.txt"),
            ("clean", "-fd"),
            ("checkout", "--", "."),
            ("checkout", "-b", "feat"),
            ("stash",),
            ("stash", "pop"),
            ("commit", "-m", "msg"),
            ("push",),
            ("push", "origin", "main"),
            ("pull",),
            ("merge", "other"),
            ("rebase", "main"),
            ("cherry-pick", "abc123"),
            ("apply", "patch.diff"),
            ("tag", "v1"),
            ("rm", "foo.txt"),
            ("mv", "a.txt", "b.txt"),
            ("worktree", "add", "../wt"),
        ],
    )
    def test_git_mutating_refused_dry_run(self, bridge, args):
        result = bridge.git_command(*args)
        assert result.success is False
        assert "refusée par défaut" in result.error

    @pytest.mark.parametrize(
        "args",
        [
            ("commit", "-m", "msg"),
            ("push",),
            ("reset", "--hard", "HEAD"),
            ("restore", "."),
            ("clean", "-fd"),
        ],
    )
    def test_git_mutating_refused_real_mode(self, real_bridge, args):
        """Le refus ne dépend pas du dry_run : fail-closed dans les deux modes."""
        result = real_bridge.git_command(*args)
        assert result.success is False
        assert "refusée par défaut" in result.error

    def test_git_reset_via_run_command_refused(self, bridge):
        """Pas de contournement : run_command("git", ...) traverse le garde."""
        result = bridge.run_command("git", ["reset", "--hard", "HEAD"])
        assert result.success is False
        assert "refusée par défaut" in result.error

    def test_git_restore_helper_refused(self, bridge):
        result = bridge.git_restore("foo.txt")
        assert result.success is False
        assert "refusée par défaut" in result.error

    def test_git_commit_helper_refused(self, bridge):
        result = bridge.git_commit("test")
        assert result.success is False
        assert "refusée par défaut" in result.error

    def test_git_add_helper_refused(self, bridge):
        result = bridge.git_add("foo.txt")
        assert result.success is False
        assert "refusée par défaut" in result.error

    # ---- Contrat lecture seule conservé ----

    def test_git_status(self, bridge):
        result = bridge.git_status()
        assert result.success is True
        assert result.dry_run is True

    def test_git_diff_allowed(self, bridge):
        result = bridge.git_diff()
        assert result.success is True
        assert result.dry_run is True

    def test_git_log_allowed(self, bridge):
        result = bridge.git_log(limit=3)
        assert result.success is True
        assert result.dry_run is True

    def test_read_only_whitelist_content(self):
        assert ALLOWED_GIT_COMMANDS == frozenset({
            "status", "diff", "log", "branch", "ls-files", "show",
            "rev-parse", "rev-list", "config",
        })

    def test_mutating_whitelist_covers_destructive_ops(self):
        for op in ("restore", "reset", "clean", "checkout", "stash",
                   "commit", "push", "pull", "merge", "rebase", "cherry-pick"):
            assert op in GIT_MUTATING_OPERATIONS

    def test_git_force_forbidden(self, bridge):
        # push est refusé d'abord (opération de publication), avant l'analyse
        # des flags : le refus mutating est prioritaire.
        result = bridge.git_command("push", "--force")
        assert result.success is False
        assert "refusée par défaut" in result.error

    def test_git_forbidden_flag_on_read_only_command(self, bridge):
        # Un flag interdit sur une commande read-only reste refusé.
        result = bridge.git_command("show", "--hard")
        assert result.success is False
        assert "interdit" in result.error

    def test_git_unknown_command_refused(self, bridge):
        result = bridge.git_command("frobnicate")
        assert result.success is False
        assert "non autorisée" in result.error

    def test_git_empty_args_refused(self, bridge):
        result = bridge.git_command()
        assert result.success is False
        assert "Aucun argument git" in result.error

    # ---- Légitimité read-only réelle (mini-dépôt isolé) ----

    def test_read_only_git_real_repo(self, tmp_path):
        import subprocess

        repo_dir = tmp_path / "minirepo"
        repo_dir.mkdir()
        (repo_dir / "file.txt").write_text("v1\n", encoding="utf-8")
        env_git = ["git", "-C", str(repo_dir)]
        subprocess.run([*env_git, "init"], check=True, capture_output=True)
        subprocess.run([*env_git, "add", "-A"], check=True, capture_output=True)
        subprocess.run(
            [*env_git, "-c", "user.name=t", "-c", "user.email=t@t.local", "commit", "-m", "init"],
            check=True,
            capture_output=True,
        )

        b = InternalToolBridge(root_dir=repo_dir, dry_run=False)
        st = b.git_status()
        assert st.success is True
        log = b.git_log(limit=1)
        assert log.success is True
        assert log.stdout.strip() != ""
