"""
Unit tests for SelfAwarenessGateway (Read-Only Introspection Subsystem).
"""

import pytest
from pathlib import Path
from core.knowledge.self_awareness import SelfAwarenessGateway, IntrospectionResult

@pytest.fixture
def gateway():
    gw = SelfAwarenessGateway()
    return gw

def test_gateway_initialization_and_integrity(gateway):
    res = gateway.verify_integrity()
    assert isinstance(res, IntrospectionResult)
    assert res.status == "FOUND"
    assert res.confidence == 1.0
    assert res.data["integrity_status"] == "SELF-KNOWLEDGE MAP COMPLETE"
    assert res.data["loaded_artifacts_count"] >= 10

def test_get_file_metadata_existing(gateway):
    res = gateway.get_file_metadata("core/decision_router.py")
    assert res.status == "FOUND"
    assert res.confidence == 1.0
    assert res.source_artifact == "FILE_MANIFEST.json"
    assert res.data["filename"] == "decision_router.py"
    assert res.data["size_bytes"] > 0
    assert len(res.data["sha256"]) == 64

def test_get_file_metadata_unknown(gateway):
    res = gateway.get_file_metadata("non_existent_random_file_xyz_12345.py")
    assert res.status == "UNKNOWN"
    assert res.confidence == 0.0
    assert res.data is None

def test_get_file_hash(gateway):
    res = gateway.get_file_hash("pyproject.toml")
    assert res.status == "FOUND"
    assert res.confidence == 1.0
    assert len(res.data["sha256"]) == 64
    assert res.source_artifact == "FILE_HASHES.json"

def test_find_symbol_class(gateway):
    res = gateway.find_symbol("IntentRouter", symbol_type="class")
    assert res.status == "FOUND"
    assert res.confidence == 1.0
    assert res.data["count"] >= 1
    assert any(s["definition"]["name"] == "IntentRouter" for s in res.data["symbols"])

def test_find_symbol_function(gateway):
    res = gateway.find_symbol("main", symbol_type="function")
    assert res.status == "FOUND"
    assert res.confidence == 1.0
    assert res.data["count"] >= 1

def test_find_symbol_unknown(gateway):
    res = gateway.find_symbol("function_that_does_not_exist_in_ezzio_os_999")
    assert res.status == "UNKNOWN"
    assert res.confidence == 0.0
    assert res.data["count"] == 0

def test_get_module_imports(gateway):
    res = gateway.get_module_imports("core/rag/simple_rag.py")
    assert isinstance(res, IntrospectionResult)
    # simple_rag is in import graph
    assert res.status in ("FOUND", "UNKNOWN")
    if res.status == "FOUND":
        assert "imported_modules" in res.data

def test_get_module_dependents(gateway):
    res = gateway.get_module_dependents("core/decision_router.py")
    assert isinstance(res, IntrospectionResult)
    assert res.status in ("FOUND", "UNKNOWN")

def test_get_api_routes(gateway):
    res = gateway.get_api_routes("/ws/chat")
    assert res.status == "FOUND"
    assert res.data["websocket_routes_count"] >= 1
    assert any("/ws/chat" in r["path"] for r in res.data["websocket_routes"])

def test_get_database_info(gateway):
    res = gateway.get_database_info("messages")
    assert res.status == "FOUND"
    assert "tables" in res.data
    assert any("messages" in k for k in res.data["tables"])

def test_get_tests_for_module(gateway):
    res = gateway.get_tests_for_module("core/decision_router.py")
    assert isinstance(res, IntrospectionResult)
    if res.status == "FOUND":
        assert len(res.data["test_files"]) >= 1

def test_get_analysis_gaps(gateway):
    res = gateway.get_analysis_gaps()
    assert res.status == "FOUND"
    assert "reconciliation_verdict" in res.data
    assert "equations" in res.data

def test_gateway_is_strictly_read_only(gateway):
    # Verify gateway has no write, update, delete or execution methods
    forbidden_prefixes = ("write", "delete", "remove", "update", "exec", "modify", "save", "patch", "heal")
    methods = [attr for attr in dir(gateway) if not attr.startswith("_")]
    for m in methods:
        for prefix in forbidden_prefixes:
            assert not m.startswith(prefix), f"Forbidden mutating method detected: {m}"
