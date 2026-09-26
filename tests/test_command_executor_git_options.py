"""Test regression for GovernedCommandExecutor git options classification."""

import tempfile

from core.agent.command_executor import GovernedCommandExecutor


def test_classify_action_git_with_global_options():
    """Verify GovernedCommandExecutor correctly classifies git subcommands with global options."""
    with tempfile.TemporaryDirectory() as tmpdir:
        executor = GovernedCommandExecutor(workspace_root=tmpdir)

        # Basic safe git command
        cls, _ = executor.classify_action("git status")
        assert cls == "SAFE"

        # Safe git command with -C option
        cls_c, reason_c = executor.classify_action("git -C G:\\AI\\E-zzio status")
        assert cls_c == "SAFE", f"Expected SAFE for git -C status, got {cls_c}: {reason_c}"

        # Safe git command with --no-pager option
        cls_p, reason_p = executor.classify_action("git --no-pager diff")
        assert cls_p == "SAFE", f"Expected SAFE for git --no-pager diff, got {cls_p}: {reason_p}"

        # Safe git command with -c key=value option
        cls_cfg, reason_cfg = executor.classify_action("git -c core.autocrlf=false log")
        assert cls_cfg == "SAFE", f"Expected SAFE for git -c log, got {cls_cfg}: {reason_cfg}"

        # Modifying git command with -C option
        cls_commit, _ = executor.classify_action("git -C G:\\AI\\E-zzio commit -m 'test'")
        assert cls_commit == "SENSITIVE"
