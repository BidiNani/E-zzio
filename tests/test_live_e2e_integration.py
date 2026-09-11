"""
tests/test_live_e2e_integration.py — Real end-to-end integration test (1 call maximum)
"""
import asyncio
import logging
import pytest
from core.ezzio_master import ezzio_master

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("LiveE2EIntegration")

@pytest.mark.asyncio
async def run_live_e2e_integration_test():
    logger.info("=== INITIALISATION DU TEST D'INTÉGRATION RÉEL END-TO-END ===")

    mission_prompt = "Analyse les risques du composant vault et propose une correction sécurisée."
    session_id = "live-e2e-session-001"
    channel = "web"

    # Exécution réelle de l'orchestration multi-agents
    res = await ezzio_master.orchestrate_multi_agent_mission(
        mission_prompt=mission_prompt,
        session_id=session_id,
        channel=channel
    )

    logger.info("=== RÉSULTATS DE L'ORCHESTRATION ===")
    logger.info("Master Model : %s", res.get("master_model"))
    logger.info("Nombre de sous-tâches : %d", len(res.get("subtasks", [])))

    for sub in res.get("subtasks", []):
        logger.info(" - Sous-tâche [%s] | Rôle: %s | Modèle: %s | Thinking: %s",
                    sub.get("task_id"), sub.get("role"), sub.get("model"), sub.get("thinking_level"))

    logger.info("=== SYNTHÈSE MASTER ===")
    logger.info("%s", res.get("synthesis"))

    # Vérification de la mémoire persistée
    history = await ezzio_master.memory.get_session_history(session_id, limit=5)
    logger.info("Entrées enregistrées en mémoire : %d", len(history))

    assert res.get("ok") is True
    assert res.get("master_model") == "gemini-3.8-flash"
    assert len(res.get("subtasks", [])) == 2

    sub_forensic = res["subtasks"][0]
    sub_coding = res["subtasks"][1]

    assert sub_forensic["role"] == "forensic"
    assert sub_forensic["model"] == "gemini-3.6-flash"

    assert sub_coding["role"] == "coding"
    assert sub_coding["model"] == "gemini-3.7-flash"

    logger.info("✅ TEST INTÉGRATION RÉEL END-TO-END : SUCCÈS (PROVEN)")
    return res

if __name__ == "__main__":
    asyncio.run(run_live_e2e_integration_test())
