"""Test regression for codebase_indexer AST async function inclusion."""

import os
import tempfile

from core.agent.codebase_indexer import CodebaseIndexer


def test_get_repo_map_includes_async_functions():
    """Verify CodebaseIndexer.get_repo_map includes async function definitions."""
    with tempfile.TemporaryDirectory() as tmpdir:
        sample_file = os.path.join(tmpdir, "sample_service.py")
        with open(sample_file, "w", encoding="utf-8") as f:
            f.write(
                "class SampleService:\n"
                "    pass\n\n"
                "def sync_func():\n"
                "    pass\n\n"
                "async def async_func():\n"
                "    pass\n"
            )

        indexer = CodebaseIndexer(workspace_root=tmpdir)
        repo_map = indexer.get_repo_map()

        assert "sample_service.py" in repo_map
        assert "class SampleService" in repo_map
        assert "def sync_func()" in repo_map
        assert "def async_func()" in repo_map
