"""Test regression and contract verification for get_symbol_map tool integration."""

import os
import tempfile

from core.agent.agent_guard import AgentPolicyGuard
from core.agent.codebase_indexer import CodebaseIndexer
from core.agent.tools_registry import ToolRegistry


def test_codebase_indexer_get_repo_map_filter():
    """Verify CodebaseIndexer.get_repo_map supports path filtering and file limit."""
    with tempfile.TemporaryDirectory() as tmpdir:
        mod_dir = os.path.join(tmpdir, "module_a")
        os.makedirs(mod_dir, exist_ok=True)
        with open(os.path.join(mod_dir, "service.py"), "w", encoding="utf-8") as f:
            f.write("class ServiceA:\n    pass\n\ndef run_a():\n    pass\n")

        with open(os.path.join(tmpdir, "helper.py"), "w", encoding="utf-8") as f:
            f.write("def help_func():\n    pass\n")

        indexer = CodebaseIndexer(workspace_root=tmpdir)

        # Unfiltered map
        full_map = indexer.get_repo_map(max_files=10)
        assert "ServiceA" in full_map
        assert "help_func" in full_map

        # Filtered map
        filtered_map = indexer.get_repo_map(max_files=10, path_filter="module_a")
        assert "ServiceA" in filtered_map
        assert "help_func" not in filtered_map


def test_tool_registry_get_symbol_map():
    """Verify ToolRegistry exposes and executes get_symbol_map tool correctly."""
    with tempfile.TemporaryDirectory() as tmpdir:
        sample_file = os.path.join(tmpdir, "app.py")
        with open(sample_file, "w", encoding="utf-8") as f:
            f.write("class CoreApp:\n    pass\n\nasync def start_app():\n    pass\n")

        registry = ToolRegistry(workspace_root=tmpdir)
        tools = registry.list_tools()

        # Tool registration check
        tool_names = [t.get("name") for t in tools]
        assert "get_symbol_map" in tool_names

        # Execution check
        res = registry.execute("get_symbol_map", {"max_files": 5})
        assert "app.py" in res
        assert "class CoreApp" in res
        assert "def start_app()" in res


def test_agent_policy_guard_get_symbol_map():
    """Verify AgentPolicyGuard classifies get_symbol_map as SAFE read-only tool."""
    with tempfile.TemporaryDirectory() as tmpdir:
        guard = AgentPolicyGuard(workspace_root=tmpdir)

        # Intent evaluation
        allowed, reason = guard.evaluate_intent("get_symbol_map", {"path_filter": "core"})
        assert allowed is True
        assert reason == "ALLOW"

        # Classification check
        cls, cat_reason = guard.classify_action("get_symbol_map", {})
        assert cls == "SAFE"
        assert "lecture ou recherche" in cat_reason.lower()
