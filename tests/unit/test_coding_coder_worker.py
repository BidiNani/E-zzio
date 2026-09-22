"""Tests pour core/coding/coder_worker.py (unit, mockés)."""
from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from core.coding.coder_worker import CoderWorker, FileEdit
from core.coding.protocol import (
    CodingRequest,
    ExecutionMode,
)


@pytest.fixture
def worker(tmp_path):
    return CoderWorker(root_dir=tmp_path, dry_run=True)


class TestCoderWorkerInit:
    def test_init(self, tmp_path):
        w = CoderWorker(root_dir=tmp_path)
        assert w.root_dir == tmp_path.resolve()
        assert w.max_iterations == 3
        assert w.bridge is not None
        assert w.policy is not None


class TestPolicyValidation:
    def test_invalid_request_rejected(self, worker):
        request = CodingRequest(task_description="")
        response = worker.execute(request)
        assert response.success is False
        assert "policy" in response.error.lower()

    def test_read_only_sandbox_accepted(self, worker):
        request = CodingRequest(
            task_description="test",
            mode=ExecutionMode.READ_ONLY_SANDBOX,
        )
        # En dry_run, va simuler
        with patch.object(worker, "_call_llm", return_value='{"plan": [], "files": []}'):
            response = worker.execute(request)
            # Plan vide => échec attendu
            assert response.success is False


class TestPlanParsing:
    def test_parse_valid_json(self, worker):
        llm_response = '''{"plan": ["step 1"], "files": [{"path": "foo.py", "content": "print(1)"}]}'''
        with patch.object(worker, "_call_llm", return_value=llm_response):
            edits = worker._plan(CodingRequest(task_description="test"), 1)
            assert len(edits) == 1
            assert edits[0].path == "foo.py"

    def test_parse_invalid_json(self, worker):
        with patch.object(worker, "_call_llm", return_value="No JSON here"):
            edits = worker._plan(CodingRequest(task_description="test"), 1)
            assert edits == []

    def test_parse_malformed_json(self, worker):
        with patch.object(worker, "_call_llm", return_value='{"plan": ["step 1"]'):
            edits = worker._plan(CodingRequest(task_description="test"), 1)
            assert edits == []


class TestExecuteDryRun:
    def test_execute_dry_run_success(self, worker):
        llm_response = '''{"plan": ["create test"], "files": [{"path": "test_foo.py", "content": "def test(): pass"}]}'''
        with patch.object(worker, "_call_llm", return_value=llm_response):
            request = CodingRequest(
                task_description="create test",
                mode=ExecutionMode.READ_ONLY_SANDBOX,
            )
            response = worker.execute(request)
            # En dry_run, la vérification est simulée => succès
            assert response.success is True
            assert response.iterations >= 1

    def test_execute_no_provider(self, worker):
        """Si aucun provider n'est disponible, execute retourne un échec.

        Note : on patche ``_call_llm`` directement car l'import est fait
        localement dans la méthode (pas patchable via module.function).
        """
        with patch.object(worker, "_call_llm", side_effect=RuntimeError("Aucun provider LLM disponible")):
            request = CodingRequest(task_description="test", mode=ExecutionMode.READ_ONLY_SANDBOX)
            response = worker.execute(request)
            assert response.success is False
