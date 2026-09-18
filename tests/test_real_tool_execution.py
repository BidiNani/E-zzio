import os

import pytest

from runtime.policy.engine import PolicyDecision, PolicyEngine
from tools.fs_tools import list_directory, read_file


def test_tool_execution_allowed_read_and_list(tmp_path):
    # Création d'un dossier et fichier temporaire
    test_dir = tmp_path / "agent_test_dir"
    test_dir.mkdir()
    sample_file = test_dir / "sample.txt"
    sample_file.write_text("E-ZZIO Tool Payload Content", encoding="utf-8")

    # 1. Test list_directory
    listed = list_directory(str(test_dir))
    assert "sample.txt" in listed
    assert "[FILE]" in listed

    # 2. Test read_file
    content = read_file(str(sample_file))
    assert "E-ZZIO Tool Payload Content" in content

def test_tool_execution_policy_engine_gate():
    policy = PolicyEngine(constitution={
        "kernel_lock": True,
        "immutable_paths": ["core/constitution", "secrets/"],
        "require_human_approval": ["system_wipe", "drop_db"]
    })

    # 1. Lecture autorisée
    dec_read = policy.evaluate_intent(
        actor="ezzio_agent",
        action="read_file",
        target="runtime/evidence/evidence.db",
        context_permissions=["read_file"]
    )
    assert dec_read == PolicyDecision.ALLOW

    # 2. Écriture refusée par absence de permission
    dec_write = policy.evaluate_intent(
        actor="ezzio_agent",
        action="write_file",
        target="runtime/evidence/evidence.db",
        context_permissions=["read_file"]
    )
    assert dec_write == PolicyDecision.DENY

    # 3. Modification d'un chemin immuable bloquée
    dec_immutable = policy.evaluate_intent(
        actor="admin",
        action="write_file",
        target="core/constitution/rules.json",
        context_permissions=["write_file", "admin"]
    )
    assert dec_immutable == PolicyDecision.DENY

def test_tool_execution_nonexistent_path():
    res = read_file("non_existent_folder_xyz/file.txt")
    assert "introuvable" in res or "Erreur" in res or "❌" in res
