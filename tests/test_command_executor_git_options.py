"""Comprehensive forensic qualification matrix for GovernedCommandExecutor git options classification."""

import tempfile

from core.agent.agent_guard import AgentPolicyGuard
from core.agent.command_executor import GovernedCommandExecutor
from core.agent.tools_registry import ToolRegistry


def test_git_classification_qualification_matrix():
    """Verify full matrix of git command classification and fail-closed security properties."""
    with tempfile.TemporaryDirectory() as tmpdir:
        executor = GovernedCommandExecutor(workspace_root=tmpdir)
        guard = AgentPolicyGuard(workspace_root=tmpdir)
        registry = ToolRegistry(workspace_root=tmpdir)

        # 1. SAFE CASES (Read-only inspection commands with/without global options)
        safe_matrix = [
            "git status",
            "git -C G:\\AI\\E-zzio status",
            "git --no-pager status",
            "git -c core.pager=cat status",
            "git -C G:\\AI\\E-zzio --no-pager status",
            "git --no-pager -C G:\\AI\\E-zzio status",
            "git status --short",
            "git diff --stat",
            "git log -n 5",
            "git -C \"C:\\Program Files\\repo\" status",
        ]
        for cmd in safe_matrix:
            cls, reason = executor.classify_action(cmd)
            assert cls == "SAFE", f"Expected SAFE for '{cmd}', got {cls}: {reason}"

        # 2. SENSITIVE CASES (State-modifying commands with global options)
        sensitive_matrix = [
            "git -C G:\\AI\\E-zzio commit -m 'test'",
            "git --no-pager reset --hard-ref",
            "git -c user.name=x push origin main",
            "git -C G:\\AI\\E-zzio checkout feat/test",
            "git --no-pager clean -n",
        ]
        for cmd in sensitive_matrix:
            cls, reason = executor.classify_action(cmd)
            assert cls == "SENSITIVE", f"Expected SENSITIVE for '{cmd}', got {cls}: {reason}"

        # 3. FAIL-CLOSED CASES (Missing subcommand, consumed argument, or bare git)
        fail_closed_matrix = [
            "git",
            "git -C G:\\AI\\E-zzio",
            "git --no-pager",
            "git -C status",  # 'status' consumed as -C path argument, leaving no subcommand
        ]
        for cmd in fail_closed_matrix:
            cls, reason = executor.classify_action(cmd)
            assert cls in ["SENSITIVE", "CRITICAL"], f"Expected FAIL-CLOSED (SENSITIVE/CRITICAL) for '{cmd}', got {cls}: {reason}"

        # 4. CROSS-COMPONENT INTEGRATION (GovernedCommandExecutor -> AgentPolicyGuard -> ToolRegistry)
        cls_exec, _ = executor.classify_action("git -C G:\\AI\\E-zzio status")
        cls_guard, _ = guard.classify_action("run_powershell", {"command": "git -C G:\\AI\\E-zzio status"})
        res_registry = registry.execute("run_powershell", {"command": "git -C G:\\AI\\E-zzio status"})

        assert cls_exec == "SAFE"
        assert cls_guard == "SAFE"
        assert "[RUNTIME POLICY BLOCKED]" not in res_registry
