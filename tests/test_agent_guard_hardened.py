"""
E-ZZIO Test Suite — Agent Policy Guard & Anti-Tampering Hardening.
Certifie la sécurité résiduelle du noyau agentique :
1. Confinement strict par os.path.commonpath (rejet de dossiers voisins à préfixe similaire)
2. Protection du noyau contre toute auto-modification non autorisée
3. Interception exhaustive des commandes shell destructives (combinaisons de flags PowerShell/CMD)
"""
import pytest
from core.agent.agent_guard import AgentPolicyGuard


@pytest.fixture
def guard(tmp_path):
    return AgentPolicyGuard(workspace_root=str(tmp_path))


def test_guard_confinement_commonpath_vs_neighbor_prefix(guard, tmp_path):
    # Fichier légitime dans le workspace
    ok_valid, _ = guard.evaluate_intent("write_file", {"path": "projects/app/main.py"})
    assert ok_valid is True

    # Dossier voisin externe avec préfixe de nom similaire
    neighbor_path = f"{str(tmp_path)}_BACKUP\\malicious.py"
    ok_neighbor, reason_neighbor = guard.evaluate_intent("write_file", {"path": neighbor_path})
    assert ok_neighbor is False
    assert "[SECURITY DENY]" in reason_neighbor
    assert "Accès hors du workspace interdit" in reason_neighbor


def test_guard_anti_tampering_core_components(guard):
    protected_files = [
        "core/agent/agent_guard.py",
        "core/agent/patch_engine.py",
        "core/agent/tools_registry.py",
        "core/agent/coding_agent_loop.py",
        "core/agent/agent_provider.py",
        "core/identity/canonical_identity.py",
        "core/security/guardrail.py",
        "secrets/.env",
        "web_server.py",
        "pyproject.toml"
    ]
    for target in protected_files:
        ok_patch, reason_patch = guard.evaluate_intent("apply_patch", {"path": target})
        assert ok_patch is False, f"Le fichier critique {target} aurait dû être protégé !"
        assert "Modification d'un composant critique de sécurité interdit" in reason_patch

        ok_write, reason_write = guard.evaluate_intent("write_file", {"path": target})
        assert ok_write is False
        assert "Modification d'un composant critique de sécurité interdit" in reason_write


def test_guard_forbidden_shell_commands(guard):
    dangerous_commands = [
        "Remove-Item -Path secrets -Recurse -Force",
        "remove-item -force -recurse G:\\AI\\E-zzio",
        "del /s /f /q C:\\data",
        "rmdir /s /q runtime",
        "rm -rf /",
        "git reset --hard HEAD~1",
        "git clean -fd",
        "format D: /FS:NTFS",
        "shutdown /s /t 0",
        "stop-computer -force"
    ]
    for cmd in dangerous_commands:
        ok, reason = guard.evaluate_intent("run_powershell", {"command": cmd})
        assert ok is False, f"La commande dangereuse '{cmd}' aurait dû être bloquée !"
        assert "[SECURITY DENY]" in reason
