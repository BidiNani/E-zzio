"""Tests pour core/coding/bridge.py."""
from __future__ import annotations

import pytest

from core.coding.bridge import (
    ALLOWED_GIT_COMMANDS,
    ALLOWED_SHELL_COMMANDS,
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
    def test_git_status(self, bridge):
        result = bridge.git_status()
        assert result.success is True
        assert result.dry_run is True

    def test_git_status_not_allowed(self, bridge):
        result = bridge.git_command("reset")
        assert result.success is False
        assert "non autorisée" in result.error

    def test_git_force_forbidden(self, bridge):
        result = bridge.git_command("push", "--force")
        assert result.success is False
        assert "interdit" in result.error

    def test_git_push_no_force_allowed(self, bridge):
        result = bridge.git_command("push")
        assert result.success is True  # dry-run

    def test_git_commit_allowed(self, bridge):
        result = bridge.git_commit("test")
        assert result.success is True

    def test_git_add_allowed(self, bridge):
        result = bridge.git_add("foo.txt")
        assert result.success is True
