import pytest

from runtime.tools.tool_registry import ToolRegistry
from runtime.tools.tool_schema import ToolRequest


def test_tool_registry_discovery_and_schema():
    reg = ToolRegistry()
    tools = reg.list_tools()
    assert len(tools) >= 3

    tool_names = [t["name"] for t in tools]
    assert "filesystem.read" in tool_names
    assert "filesystem.list" in tool_names
    assert "filesystem.observe" in tool_names

    # Vérification schéma
    meta_obs = reg.get_tool("filesystem.observe")
    assert meta_obs is not None
    assert meta_obs["version"] == "1.0.0"
    assert "directory_path" in meta_obs["input_schema"]

def test_tool_registry_authorization_rules():
    reg = ToolRegistry()

    # 1. Autorisé avec capabilities complètes
    ctx_ok = {"capabilities": ["fs:read", "fs:observe"], "target": "data/sample.txt"}
    assert reg.authorize_tool("filesystem.read", ctx_ok) is True

    # 2. Refusé pour mismatch de capabilities
    ctx_mismatch = {"capabilities": ["fs:list"], "target": "data/sample.txt"}
    assert reg.authorize_tool("filesystem.read", ctx_mismatch) is False

    # 3. Refusé sur cible immuable/protégée
    ctx_protected = {"capabilities": ["fs:read"], "target": "core/constitution/rules.json"}
    assert reg.authorize_tool("filesystem.read", ctx_protected) is False

def test_tool_registry_unknown_tool_deny():
    reg = ToolRegistry()
    assert reg.authorize_tool("unregistered_arbitrary_tool") is False

    req = ToolRequest(name="unregistered_arbitrary_tool", arguments={})
    res = reg.dispatch(req)
    assert res.success is False
    assert "inconnu" in res.error
