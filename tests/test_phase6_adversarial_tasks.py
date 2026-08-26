import pytest
from tools.fs_tools import observe_filesystem, read_file
from runtime.policy.engine import PolicyEngine, PolicyDecision
from runtime.tools.tool_registry import ToolRegistry
from runtime.tools.tool_schema import ToolRequest

def test_adversarial_path_traversal_defense():
    # Tentative d'accès hors du périmètre autorisé
    res_obs = observe_filesystem("../../Windows/System32")
    assert res_obs["status"] == "DENIED"
    
    res_read = read_file("../../../secret_keys.json")
    assert "introuvable" in res_read or "Erreur" in res_read or "❌" in res_read

def test_adversarial_immutable_path_lock():
    policy = PolicyEngine(constitution={
        "kernel_lock": True,
        "immutable_paths": ["core/constitution", "secrets/"]
    })
    
    dec = policy.evaluate_intent(
        actor="adversary",
        action="modify_constitution",
        target="core/constitution/axioms.json",
        context_permissions=["modify_constitution"]
    )
    assert dec == PolicyDecision.DENY

def test_adversarial_unknown_and_unauthorized_tool():
    reg = ToolRegistry()
    
    # Outil inexistant
    assert reg.authorize_tool("malicious_shell_exec") is False
    
    # Outil existant mais capability manquante
    ctx = {"capabilities": ["other:cap"], "target": "data/test.txt"}
    assert reg.authorize_tool("filesystem.read", ctx) is False
