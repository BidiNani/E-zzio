"""Tests unitaires déterministes pour la boucle autonome de test et de correction dans EzzioMaster."""

import pytest
import asyncio
import tempfile
import shutil
from pathlib import Path
from core.ezzio_master import EzzioMaster
from core.providers.base_provider import CostClass, ProviderResponse


class FakeRepairMissionProvider:
    """Provider fake déterministe simulant les réponses de correction du modèle."""

    def __init__(self, fix_responses=None):
        self.calls = []
        self.fix_responses = fix_responses or []
        self.call_count = 0

    async def generate(
        self,
        prompt: str = "",
        system_prompt: str = None,
        model: str = "gemini-3.8-flash",
        temperature: float = 0.2,
        max_tokens: int = 512,
        thinking_level: str = "off",
        **kwargs
    ) -> ProviderResponse:
        self.calls.append({
            "prompt": prompt,
            "system_prompt": system_prompt,
            "model": model,
            "thinking_level": thinking_level,
        })
        resp_text = "[Fake LLM Response]"
        if self.fix_responses and self.call_count < len(self.fix_responses):
            resp_text = self.fix_responses[self.call_count]
            self.call_count += 1
        return ProviderResponse(
            content=resp_text,
            model=model,
            provider="fake_repair_provider",
            cost_class=CostClass.LOCAL,
        )


@pytest.mark.asyncio
async def test_repair_loop_case_a_nominal_pass_first_try():
    """CAS A : Fichier correct -> pytest PASS dès le 1er essai -> 0 appel LLM de correction."""
    fake_prov = FakeRepairMissionProvider()
    master = EzzioMaster(provider=fake_prov)

    sandbox_dir = Path("G:/AI/E-zzio/runtime/sandbox_repair_a").resolve()
    sandbox_dir.mkdir(parents=True, exist_ok=True)

    module_file = sandbox_dir / "mod_a.py"
    test_file = sandbox_dir / "test_mod_a.py"

    module_file.write_text("def mul(a: int, b: int) -> int:\n    return a * b\n", encoding="utf-8")
    test_file.write_text("from mod_a import mul\n\ndef test_mul():\n    assert mul(3, 4) == 12\n", encoding="utf-8")

    try:
        subtasks = [
            {
                "task_id": "subtask-repair-a-01",
                "role": "CODING",
                "prompt": "Vérifier le module de multiplication",
                "test_target": str(test_file),
                "complexity": 0.5
            }
        ]

        res = await master.orchestrate_multi_agent_mission(
            mission_prompt="Mission avec code déjà valide",
            subtask_specs=subtasks
        )

        assert res["ok"] is True
        st = res["subtasks"][0]
        assert st["action_executed"] is True
        assert st["action_status"] == "READY"
        assert st["action_valid"] is True

        # 0 appel LLM supplémentaire de correction (seuls les appels sous-tâche + synthèse)
        assert len(fake_prov.calls) == 2

    finally:
        shutil.rmtree(sandbox_dir, ignore_errors=True)


@pytest.mark.asyncio
async def test_repair_loop_case_b_fail_first_try_fixed_second_try():
    """CAS B : Bug initial -> Pytest FAIL -> Rapport transmis au modèle -> Correction écrite -> Pytest PASS au cycle 2."""
    fixed_code = "```python\ndef sub(a: int, b: int) -> int:\n    return a - b\n```"
    fake_prov = FakeRepairMissionProvider(fix_responses=[fixed_code])
    master = EzzioMaster(provider=fake_prov)

    sandbox_dir = Path("G:/AI/E-zzio/runtime/sandbox_repair_b").resolve()
    sandbox_dir.mkdir(parents=True, exist_ok=True)

    module_file = sandbox_dir / "mod_b.py"
    test_file = sandbox_dir / "test_mod_b.py"

    # Bug initial (a + b au lieu de a - b)
    module_file.write_text("def sub(a: int, b: int) -> int:\n    return a + b\n", encoding="utf-8")
    test_file.write_text("from mod_b import sub\n\ndef test_sub():\n    assert sub(10, 4) == 6\n", encoding="utf-8")

    try:
        subtasks = [
            {
                "task_id": "subtask-repair-b-01",
                "role": "CODING",
                "prompt": "Corriger la soustraction",
                "write_target": str(module_file),
                "test_target": str(test_file),
                "auto_repair": True,
                "max_cycles": 3,
                "complexity": 0.7
            }
        ]

        res = await master.orchestrate_multi_agent_mission(
            mission_prompt="Mission d me réparation autonome",
            subtask_specs=subtasks
        )

        assert res["ok"] is True
        st = res["subtasks"][0]

        # Le fichier a été corrigé et le test passe
        assert "return a - b" in module_file.read_text(encoding="utf-8")
        assert st["action_executed"] is True
        assert st["action_status"] == "READY"
        assert st["action_valid"] is True

    finally:
        shutil.rmtree(sandbox_dir, ignore_errors=True)


@pytest.mark.asyncio
async def test_repair_loop_case_c_persistent_failure_max_cycles():
    """CAS C : Erreur persistante -> Max 3 cycles d'essais -> Arrêt strict et statut FAILED_VALIDATION."""
    bad_code = "```python\ndef broken(): return 0\n```"
    fake_prov = FakeRepairMissionProvider(fix_responses=[bad_code, bad_code, bad_code])
    master = EzzioMaster(provider=fake_prov)

    sandbox_dir = Path("G:/AI/E-zzio/runtime/sandbox_repair_c").resolve()
    sandbox_dir.mkdir(parents=True, exist_ok=True)

    module_file = sandbox_dir / "mod_c.py"
    test_file = sandbox_dir / "test_mod_c.py"

    module_file.write_text("def broken(): return -1\n", encoding="utf-8")
    test_file.write_text("from mod_c import broken\n\ndef test_broken():\n    assert broken() == 999\n", encoding="utf-8")

    try:
        subtasks = [
            {
                "task_id": "subtask-repair-c-01",
                "role": "CODING",
                "prompt": "Tenter la réparation d'un test impossible",
                "write_target": str(module_file),
                "test_target": str(test_file),
                "auto_repair": True,
                "max_cycles": 3,
                "complexity": 0.7
            }
        ]

        res = await master.orchestrate_multi_agent_mission(
            mission_prompt="Mission avec échec persistant",
            subtask_specs=subtasks
        )

        assert res["ok"] is True
        st = res["subtasks"][0]

        # La limite de 3 cycles s'est appliquée sans boucle infinie
        assert st["action_executed"] is True
        assert st["action_status"] == "FAILED_VALIDATION"
        assert st["action_valid"] is False

    finally:
        shutil.rmtree(sandbox_dir, ignore_errors=True)


@pytest.mark.asyncio
async def test_repair_loop_case_d_security_blocked_outside_workspace():
    """CAS D : Cible hors workspace -> Bloqué immédiatement sans exécution ni boucle."""
    fake_prov = FakeRepairMissionProvider()
    master = EzzioMaster(provider=fake_prov)

    subtasks = [
        {
            "task_id": "subtask-repair-d-01",
            "role": "CODING",
            "prompt": "Tenter un test hors périmètre",
            "test_target": "C:/Windows/System32/drivers/etc/hosts",
            "complexity": 0.7
        }
    ]

    res = await master.orchestrate_multi_agent_mission(
        mission_prompt="Mission de test hors périmètre",
        subtask_specs=subtasks
    )

    assert res["ok"] is True
    st = res["subtasks"][0]
    assert st["action_executed"] is True
    assert st["action_status"] == "BLOCKED"
    assert st["action_valid"] is False
