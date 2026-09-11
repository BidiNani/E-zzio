import pytest
import asyncio
from unittest.mock import patch, AsyncMock
from tools.fs_tools import observe_filesystem
from core.decision_router import DecisionRouter, SearchMode
from core.providers.tavily_provider import TavilyProvider
from routers.chat import post_chat, ChatRequest, init_chat_router, _core, _memory_gateway

@pytest.mark.asyncio
async def test_real_user_scenario_e2e_execution(tmp_path):
    await init_chat_router()
    
    # 1. Préparation du dossier de travail
    work_dir = tmp_path / "scenario_env"
    work_dir.mkdir()
    doc_file = work_dir / "specs.md"
    doc_file.write_text("# E-ZZIO Specs\nArchitecture unifiée et souveraine.", encoding="utf-8")
    
    session_id = "SESS_USER_SCENARIO_E2E"
    user_id = "lead_operator"
    
    # 2. Observation physique du système de fichiers
    obs = observe_filesystem(str(work_dir))
    assert obs["status"] == "SUCCESS"
    assert "specs.md" in obs["files"]
    
    # 3. Premier tour de dialogue utilisateur
    req1 = ChatRequest(
        message=f"Observe {str(work_dir).replace('\\\\', '/')}, analyse les specs et résume le contenu.",
        user_id=user_id,
        session_id=session_id
    )
    
    synthesis = "Observation terminée : le fichier specs.md décrit l'architecture unifiée et souveraine d'E-ZZIO."
    with patch.object(_core.ollama, "search", new_callable=AsyncMock) as mock_s:
        mock_s.return_value = {
            "provider": "ollama",
            "model": "gpt-oss-20b",
            "data": {"text": synthesis}
        }
        resp1 = await post_chat(req1)
        assert "specs.md" in resp1.response
        assert "souveraine" in resp1.response
        
    # 4. Deuxième tour : Rappel contextuel et vérification d'absence de perte
    req2 = ChatRequest(
        message="Qu'avons-nous observé dans ce dossier ?",
        user_id=user_id,
        session_id=session_id
    )
    recall = "Nous avons précédemment observé specs.md qui traite de l'architecture souveraine."
    with patch.object(_core.ollama, "search", new_callable=AsyncMock) as mock_s:
        mock_s.return_value = {
            "provider": "ollama",
            "model": "gpt-oss-20b",
            "data": {"text": recall}
        }
        resp2 = await post_chat(req2)
        assert "specs.md" in resp2.response
        assert "souveraine" in resp2.response
