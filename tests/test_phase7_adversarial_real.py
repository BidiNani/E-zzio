import pytest
from tools.fs_tools import observe_filesystem, read_file
from runtime.policy.engine import PolicyEngine, PolicyDecision
from runtime.tools.tool_registry import ToolRegistry

def test_phase7_adversarial_traversal_and_absolute_paths():
    # 1. Path traversal relatif
    r1 = observe_filesystem("../../../Windows/System32")
    assert r1["status"] == "DENIED"
    
    # 2. Chemin absolu interdit
    r2 = observe_filesystem("C:\\Windows\\System32")
    assert r2["status"] == "DENIED"

def test_phase7_adversarial_constitution_and_unknown_tools():
    # 1. Verrouillage constitutionnel
    policy = PolicyEngine(constitution={
        "kernel_lock": True,
        "immutable_paths": ["core/constitution", "secrets/"]
    })
    dec = policy.evaluate_intent(
        actor="hacker",
        action="modify",
        target="core/constitution/axioms.json",
        context_permissions=["modify"]
    )
    assert dec == PolicyDecision.DENY
    
    # 2. Outil inexistant
    reg = ToolRegistry()
    assert reg.authorize_tool("ghost_tool_999") is False
