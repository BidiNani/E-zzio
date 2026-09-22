"""Tests pour core/tools/base.py + core/tools/registry.py.

BaseTool : classe abstraite pour les outils.
ToolRegistry : registre centralisant les outils enregistrés.
"""
from __future__ import annotations

from typing import Any

import pytest

from core.tools.base import BaseTool
from core.tools.registry import ToolRegistry

# ============================================================
# Fixtures
# ============================================================

class DummyTool(BaseTool):
    """Implémentation concrète pour tester."""
    def __init__(self, name: str = "dummy", description: str = "A dummy tool"):
        super().__init__(name=name, description=description)
        self.call_count = 0

    async def execute(self, **kwargs: Any) -> Any:
        self.call_count += 1
        return {"ok": True, "kwargs": kwargs}


@pytest.fixture
def dummy():
    return DummyTool()


@pytest.fixture
def registry():
    return ToolRegistry()


# ============================================================
# 1. BaseTool
# ============================================================

class TestBaseTool:
    def test_cannot_instantiate_abstract(self):
        """BaseTool ne peut pas être instancié directement."""
        with pytest.raises(TypeError):
            BaseTool(name="x", description="y")

    def test_subclass_init(self, dummy):
        assert dummy.name == "dummy"
        assert dummy.description == "A dummy tool"

    def test_subclass_custom(self):
        tool = DummyTool(name="custom", description="Custom desc")
        assert tool.name == "custom"
        assert tool.description == "Custom desc"

    @pytest.mark.asyncio
    async def test_execute_async(self, dummy):
        result = await dummy.execute(foo="bar", n=42)
        assert result["ok"] is True
        assert result["kwargs"] == {"foo": "bar", "n": 42}
        assert dummy.call_count == 1

    @pytest.mark.asyncio
    async def test_execute_no_kwargs(self, dummy):
        result = await dummy.execute()
        assert result["ok"] is True
        assert result["kwargs"] == {}


# ============================================================
# 2. ToolRegistry
# ============================================================

class TestToolRegistry:
    def test_init_empty(self, registry):
        assert registry.list_tools() == {}

    def test_register_tool(self, registry, dummy):
        registry.register(dummy)
        assert "dummy" in registry.list_tools()
        assert registry.list_tools()["dummy"] == "A dummy tool"

    def test_get_tool(self, registry, dummy):
        registry.register(dummy)
        retrieved = registry.get_tool("dummy")
        assert retrieved is dummy

    def test_get_unknown_returns_none(self, registry):
        assert registry.get_tool("nonexistent") is None

    def test_register_multiple(self, registry):
        tools = [
            DummyTool(name="t1", description="Tool 1"),
            DummyTool(name="t2", description="Tool 2"),
            DummyTool(name="t3", description="Tool 3"),
        ]
        for t in tools:
            registry.register(t)
        listed = registry.list_tools()
        assert len(listed) == 3
        assert set(listed.keys()) == {"t1", "t2", "t3"}

    def test_register_overrides_existing(self, registry):
        """Ré-enregistrer un nom écrase l'ancien."""
        t1 = DummyTool(name="same", description="First")
        t2 = DummyTool(name="same", description="Second")
        registry.register(t1)
        registry.register(t2)
        assert registry.get_tool("same") is t2
        assert registry.list_tools()["same"] == "Second"

    def test_list_tools_format(self, registry, dummy):
        registry.register(dummy)
        listed = registry.list_tools()
        assert isinstance(listed, dict)
        for name, description in listed.items():
            assert isinstance(name, str)
            assert isinstance(description, str)
