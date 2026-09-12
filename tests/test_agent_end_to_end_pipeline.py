"""Tests de certification end-to-end pour le pipeline agentique multi-capacités dans EzzioMaster."""

import pytest
import asyncio
import tempfile
import shutil
from pathlib import Path
from core.ezzio_master import EzzioMaster
from core.providers.base_provider import CostClass, ProviderResponse


class FakePipelineMissionProvider:
    """Provider fake déterministe enregistrant la chaîne complète des prompts et contextes transmis."""

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
        resp_text = f"[Fake Pipeline Response for: {prompt[:30]}]"
        if "Échec du test Pytest" in prompt and self.fix_responses:
            if self.call_count < len(self.fix_responses):
                resp_text = self.fix_responses[self.call_count]
                self.call_count += 1
        elif "Audit forensic" in prompt or "inspecter" in prompt.lower():
            resp_text = "ANALYSE: La fonction multiply comporte une anomalie de signe."

        return ProviderResponse(
            content=resp_text,
            model=model,
            provider="fake_pipeline_provider",
            cost_class=CostClass.LOCAL,
        )


@pytest.mark.asyncio
async def test_pipeline_case_a_full_end_to_end_workflow():
    """CAS A : Mission complète enchaînant ANALYSE -> FILE -> CODING -> TEST -> VALIDATION -> SYNTHÈSE avec continuité de contexte."""
    fake_prov = FakePipelineMissionProvider()
    master = EzzioMaster(provider=fake_prov)

    sandbox_dir = Path("G:/AI/E-zzio/runtime/sandbox_pipeline_a").resolve()
    sandbox_dir.mkdir(parents=True, exist_ok=True)

    module_file = sandbox_dir / "math_mod.py"
    test_file = sandbox_dir / "test_math_mod.py"

    # Code initial avec bug
    module_file.write_text("def multiply(a: int, b: int) -> int:\n    return -1 * a * b\n", encoding="utf-8")
    test_file.write_text("from math_mod import multiply\n\ndef test_multiply():\n    assert multiply(3, 4) == 12\n", encoding="utf-8")

    corrected_code = "def multiply(a: int, b: int) -> int:\n    return a * b\n"

    try:
        subtasks = [
            {
                "task_id": "st-01-inspect",
                "role": "RESEARCH",
                "prompt": "Inspecter le module math_mod pour analyser la fonction multiply",
                "target": str(module_file),
                "complexity": 0.5
            },
            {
                "task_id": "st-02-coding-fix",
                "role": "CODING",
                "prompt": "Appliquer le correctif sur math_mod et valider par Pytest",
                "write_target": str(module_file),
                "write_content": corrected_code,
                "test_target": str(test_file),
                "complexity": 0.7
            }
        ]

        res = await master.orchestrate_multi_agent_mission(
            mission_prompt="Mission complète d me certification agentique end-to-end",
            subtask_specs=subtasks
        )

        assert res["ok"] is True
        assert len(res["subtasks"]) == 2

        st1, st2 = res["subtasks"]

        # Étape 1 : Inspection
        assert st1["action_executed"] is True
        assert st1["action_status"] == "READY"

        # Étape 2 : Modification + Pytest (Continuite du contexte de st1 verifiée)
        assert st2["action_executed"] is True
        assert st2["action_status"] == "READY"
        assert st2["action_valid"] is True

        # Preuve de la continuité contextuelle : le prompt de st2 DOIT contenir l'analyse de st1
        st2_prompt = fake_prov.calls[1]["prompt"]
        assert "[Contexte des sous-tâches précédentes]" in st2_prompt
        assert "ANALYSE: La fonction multiply" in st2_prompt

        # Preuve d'écriture sur le disque
        assert module_file.read_text(encoding="utf-8") == corrected_code

        # Synthèse Master
        assert res["synthesis"] is not None

    finally:
        shutil.rmtree(sandbox_dir, ignore_errors=True)


@pytest.mark.asyncio
async def test_pipeline_case_b_intermediate_action_failure():
    """CAS B : Action intermédiaire échoue -> L'orchestration capture l'échec proprement sans fausse affirmation."""
    fake_prov = FakePipelineMissionProvider()
    master = EzzioMaster(provider=fake_prov)

    subtasks = [
        {
            "task_id": "st-fail-01",
            "role": "RESEARCH",
            "prompt": "Tenter d'inspecter un fichier inexistant",
            "target": "G:/AI/E-zzio/runtime/missing_pipeline_file.py",
            "complexity": 0.5
        },
        {
            "task_id": "st-fail-02",
            "role": "CODING",
            "prompt": "Traiter le cas sur ressource absente",
            "complexity": 0.5
        }
    ]

    res = await master.orchestrate_multi_agent_mission(
        mission_prompt="Mission avec échec intermédiaire",
        subtask_specs=subtasks
    )

    assert res["ok"] is True
    st1 = res["subtasks"][0]
    assert st1["action_executed"] is True
    assert st1["action_status"] in ["UNAVAILABLE", "ERROR"]
    assert st1["action_valid"] is False


@pytest.mark.asyncio
async def test_pipeline_case_c_test_failure_with_auto_repair():
    """CAS C : Échec de test initial -> Boucle de réparation autonome active -> Succès final au cycle 2."""
    fixed_code = "```python\ndef divide(a: int, b: int) -> float:\n    return a / b\n```"
    fake_prov = FakePipelineMissionProvider(fix_responses=[fixed_code])
    master = EzzioMaster(provider=fake_prov)

    sandbox_dir = Path("G:/AI/E-zzio/runtime/sandbox_pipeline_c").resolve()
    sandbox_dir.mkdir(parents=True, exist_ok=True)

    module_file = sandbox_dir / "div_mod.py"
    test_file = sandbox_dir / "test_div_mod.py"

    # Bug initial
    module_file.write_text("def divide(a: int, b: int) -> float:\n    return a + b\n", encoding="utf-8")
    test_file.write_text("from div_mod import divide\n\ndef test_divide():\n    assert divide(10, 2) == 5.0\n", encoding="utf-8")

    try:
        subtasks = [
            {
                "task_id": "st-repair-01",
                "role": "CODING",
                "prompt": "Exécuter et réparer la fonction de division",
                "write_target": str(module_file),
                "test_target": str(test_file),
                "auto_repair": True,
                "max_cycles": 3,
                "complexity": 0.7
            }
        ]

        res = await master.orchestrate_multi_agent_mission(
            mission_prompt="Mission de réparation auto pipeline",
            subtask_specs=subtasks
        )

        assert res["ok"] is True
        st = res["subtasks"][0]

        assert st["action_executed"] is True
        assert st["action_status"] == "READY"
        assert st["action_valid"] is True
        assert "return a / b" in module_file.read_text(encoding="utf-8")

    finally:
        shutil.rmtree(sandbox_dir, ignore_errors=True)


@pytest.mark.asyncio
async def test_pipeline_case_d_forbidden_capability():
    """CAS D : Capacité/Chemin interdit -> BLOCKED immédiat, le pipeline reste sûr."""
    fake_prov = FakePipelineMissionProvider()
    master = EzzioMaster(provider=fake_prov)

    subtasks = [
        {
            "task_id": "st-forbidden-01",
            "role": "RESEARCH",
            "prompt": "Tenter un accès système non autorisé",
            "target": "C:/Windows/System32/config/SAM",
            "complexity": 0.5
        }
    ]

    res = await master.orchestrate_multi_agent_mission(
        mission_prompt="Mission avec tentative interdite",
        subtask_specs=subtasks
    )

    assert res["ok"] is True
    st = res["subtasks"][0]
    assert st["action_status"] == "BLOCKED"
    assert st["action_valid"] is False
