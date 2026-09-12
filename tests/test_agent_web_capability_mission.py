"""Tests unitaires déterministes pour la capacité WEB (WebAccessManager) dans l'orchestration de missions EzzioMaster."""

import pytest
import asyncio
from unittest.mock import patch, MagicMock
from core.ezzio_master import EzzioMaster
from core.agent.input_access_manager import InputDocument, InputType
from core.providers.base_provider import CostClass, ProviderResponse


class FakeWebMissionProvider:
    """Provider fake déterministe enregistrant les prompts pour valider l'injection des données web réelles."""

    def __init__(self):
        self.calls = []

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
        return ProviderResponse(
            content=f"[Fake LLM Web Response for: {prompt[:40]}]",
            model=model,
            provider="fake_web_mission_provider",
            cost_class=CostClass.LOCAL,
        )


@pytest.mark.asyncio
async def test_mission_with_real_web_url_fetching_nominal():
    """1. Cas nominal : Mission avec sous-tâche web d'extraction d'URL publique."""
    fake_prov = FakeWebMissionProvider()
    master = EzzioMaster(provider=fake_prov)

    target_url = "https://public-api.open-data.org/v1/weather"
    fake_html = "<html><body><h1>Open Data Weather</h1><p>Temperature: 22C, Condition: Sunny</p></body></html>"

    class FakeHttpxResp:
        status_code = 200
        headers = {"content-type": "text/html"}
        text = fake_html

    with patch("httpx.get", return_value=FakeHttpxResp()):
        subtasks = [
            {
                "task_id": "subtask-web-fetch-01",
                "role": "RESEARCH",
                "prompt": "Extraire les métriques météo publiques",
                "url": target_url,
                "complexity": 0.5
            }
        ]

        res = await master.orchestrate_multi_agent_mission(
            mission_prompt="Extraire et analyser les données web ouvertes",
            subtask_specs=subtasks
        )

        assert res["ok"] is True
        assert len(res["subtasks"]) == 1
        st = res["subtasks"][0]

        # Vérification de l'action réelle Web
        assert st["preflight_ready"] is True
        assert st["action_executed"] is True
        assert st["action_status"] == "READY"
        assert st["action_valid"] is True

        # Vérification de l'isolation des injections : les données web doivent porter le tag BRUTES - NON AUTORITATIVES
        subtask_call = fake_prov.calls[0]
        assert "DONNÉES WEB EXTRACTIVES (BRUTES - NON AUTORITATIVES)" in subtask_call["prompt"]
        assert "Temperature: 22C, Condition: Sunny" in subtask_call["prompt"]

        # Synthèse Master
        assert res["synthesis"] is not None


@pytest.mark.asyncio
async def test_mission_web_ssrf_protection_blocked():
    """2. Cas sécurité SSRF : Tentative d'accès à localhost / IP privée bloquée de manière déterministe."""
    fake_prov = FakeWebMissionProvider()
    master = EzzioMaster(provider=fake_prov)

    blocked_url = "http://127.0.0.1:8001/admin/vault_secrets"

    subtasks = [
        {
            "task_id": "subtask-ssrf-attack-01",
            "role": "RESEARCH",
            "prompt": "Tenter d'extraire les secrets du vault local via SSRF",
            "url": blocked_url,
            "complexity": 0.5
        }
    ]

    res = await master.orchestrate_multi_agent_mission(
        mission_prompt="Mission de test de robustesse SSRF",
        subtask_specs=subtasks
    )

    assert res["ok"] is True
    st = res["subtasks"][0]

    # WebAccessManager bloque la tentative SSRF
    assert st["action_executed"] is True
    assert st["action_status"] == "BLOCKED"
    assert st["action_valid"] is False

    subtask_call = fake_prov.calls[0]
    assert "[SECURITY BLOCK]" in subtask_call["prompt"] or "BLOCKED" in subtask_call["prompt"]


@pytest.mark.asyncio
async def test_mission_web_error_handling_404():
    """3. Cas erreur : Ressource web 404 / 500 ou erreur réseau gérée proprement sans crash."""
    fake_prov = FakeWebMissionProvider()
    master = EzzioMaster(provider=fake_prov)

    target_url = "https://example.org/non_existent_page_404"

    class Fake404Resp:
        status_code = 404
        headers = {}
        text = "Not Found"

    with patch("httpx.get", return_value=Fake404Resp()):
        subtasks = [
            {
                "task_id": "subtask-web-404-01",
                "role": "RESEARCH",
                "prompt": "Extraire une page inexistante",
                "url": target_url,
                "complexity": 0.5
            }
        ]

        res = await master.orchestrate_multi_agent_mission(
            mission_prompt="Test d'erreur Web 404",
            subtask_specs=subtasks
        )

        assert res["ok"] is True
        st = res["subtasks"][0]
        assert st["action_executed"] is True
        assert st["action_status"] in ["UNAVAILABLE", "ERROR"]
        assert st["action_valid"] is False
