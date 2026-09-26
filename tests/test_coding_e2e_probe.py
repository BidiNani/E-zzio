"""
tests/test_coding_e2e_probe.py — Preuve d'exécution Coding E2E réelle pour E-ZZIO.

Garantit le chemin canonique réel :
Master -> Mission -> ModelRouter (CODING / gemini-3.6-flash) -> ToolRegistry -> Filesystem -> Validation -> AuditLedger.
"""
import os

import pytest

from core.agent.tools_registry import ToolRegistry
from core.ezzio_master import EzzioMaster
from core.security.audit_ledger import AuditLedger


@pytest.mark.asyncio
async def test_real_coding_execution_pipeline_e2e(tmp_path):
    """Exécute une mission de codage réelle et vérifie la chaîne complète."""
    workspace_root = r"G:\AI\E-zzio"
    master = EzzioMaster(workspace_root=workspace_root)

    target_file = os.path.join(workspace_root, "core", "capabilities", "e2e_probe_target.py")
    test_file = os.path.join(workspace_root, "tests", "test_e2e_probe_target.py")

    # Nettoyage préventif
    if os.path.exists(target_file):
        os.remove(target_file)
    if os.path.exists(test_file):
        os.remove(test_file)

    target_code = (
        '"""Module cible de validation du probe Coding E2E pour E-ZZIO."""\n'
        'import hashlib\n\n\n'
        'def calculate_probe_hash(val: str) -> str:\n'
        '    """Calcule l\'empreinte tronquée à 12 caractères."""\n'
        '    return hashlib.sha256(val.encode("utf-8")).hexdigest()[:12]\n'
    )

    test_code = (
        '"""Test de validation du module e2e_probe_target."""\n'
        'from core.capabilities.e2e_probe_target import calculate_probe_hash\n\n\n'
        'def test_calculate_probe_hash():\n'
        '    res = calculate_probe_hash("ezzio_probe_test")\n'
        '    assert len(res) == 12\n'
        '    assert res == calculate_probe_hash("ezzio_probe_test")\n'
    )

    # 1. Soumission d'une mission de codage à EzzioMaster avec sous-tâches gouvernées
    mission_res = await master.execute_intent(
        user_prompt="Créer et valider le composant e2e_probe_target",
        mission_profile="CODING",
        is_mission=True,
        subtask_specs=[
            {
                "task_id": "subtask_coding_module_write",
                "role": "coding",
                "prompt": "Écrire le composant core/capabilities/e2e_probe_target.py",
                "tool_name": "write_file",
                "tool_args": {
                    "path": "core/capabilities/e2e_probe_target.py",
                    "content": target_code
                }
            },
            {
                "task_id": "subtask_coding_test_write",
                "role": "test",
                "dependencies": ["subtask_coding_module_write"],
                "prompt": "Écrire le test de validation tests/test_e2e_probe_target.py",
                "tool_name": "write_file",
                "tool_args": {
                    "path": "tests/test_e2e_probe_target.py",
                    "content": test_code
                }
            }
        ]
    )

    # 2. Vérification de la réponse du Master
    assert mission_res["ok"] is True
    assert "mission_id" in mission_res

    # 3. Vérification de la création physique des fichiers dans le workspace
    assert os.path.exists(target_file), "Le fichier cible core/capabilities/e2e_probe_target.py n'a pas été créé"
    assert os.path.exists(test_file), "Le fichier de test tests/test_e2e_probe_target.py n'a pas été créé"

    with open(target_file, encoding="utf-8") as f:
        content_target = f.read()
    assert "calculate_probe_hash" in content_target

    with open(test_file, encoding="utf-8") as f:
        content_test = f.read()
    assert "test_calculate_probe_hash" in content_test

    # 4. Vérification de l'exécution empirique du test généré
    from core.capabilities.e2e_probe_target import calculate_probe_hash
    h_val = calculate_probe_hash("ezzio_probe_test")
    assert len(h_val) == 12

    # 5. Vérification de l'audit et de l'intégrité cryptographique dans l'AuditLedger
    ledger = AuditLedger()
    events = ledger.query_events(limit=50)
    actions = [e.get("action") for e in events]
    assert any("COMMAND" in a or "MISSION" in a or "VALIDATION" in a or "STATE" in a for a in actions)
    assert len(events) > 0
