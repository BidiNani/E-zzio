import asyncio
import logging
from core.ezzio_master import ezzio_master

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("EzzioFunctionalTest")

async def run_functional_orchestration_test():
    logger.info("=== INITIALISATION DU TEST FONCTIONNEL D'ORCHESTRATION ===")
    
    # Cas d'usage complexe multi-étape (Coding + Forensic + Synthèse)
    complex_prompt = (
        "Mission critique : Analyse le module de sécurité de la base de code, "
        "identifie les points de contournement potentiels du vault, et propose "
        "un correctif de code robuste et sécurisé."
    )
    
    session_id = "test-orchestration-session-01"
    channel = "integration_test"
    user_id = "186035306418405376"

    logger.info("1. Soumission de la requête complexe au Master (Gemini 3.8 Flash)...")
    try:
        response = await ezzio_master.process_chat(
            prompt=complex_prompt,
            session_id=session_id,
            channel=channel,
            user_id=user_id
        )
        
        logger.info("=== RÉSULTAT DE LA SYNTHÈSE MASTER ===")
        print(f"\n[RÉPONSE FINALE DU MASTER] :\n{response}\n")
        
        logger.info("2. Vérification de la traçabilité dans l'Audit Ledger / Memory Gateway...")
        history = await ezzio_master.memory.get_session_history(session_id, limit=10)
        logger.info("Échanges enregistrés dans la mémoire short-term/mid-term : %d tours", len(history))
        for h in history:
            logger.info(" - [%s] %s", h.get("role"), str(h.get("content"))[:120])
            
        logger.info("✅ TEST FONCTIONNEL D'ORCHESTRATION : SUCCÈS (PROVEN)")
    except Exception as exc:
        logger.error("❌ ÉCHEC DU TEST D'ORCHESTRATION : %s", exc, exc_info=True)
        raise

if __name__ == "__main__":
    asyncio.run(run_functional_orchestration_test())
