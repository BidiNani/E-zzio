"""
E-ZZIO — routers/registry.py
=============================
Déclencheur manuel du refresh Gemini via POST /api/models/registry/refresh/gemini.

Garanties :
  - N'active aucun modèle
  - Ne modifie pas le routage
  - Ne retourne aucun secret (API key, token, credential)
  - Retourne uniquement des informations opérationnelles sûres
"""
from __future__ import annotations

import logging
from fastapi import APIRouter

logger = logging.getLogger("EzzioRegistryRouter")

router = APIRouter(prefix="/api/models/registry", tags=["models-registry"])


@router.post("/refresh/gemini")
async def refresh_gemini(
) -> dict:
    """
    Déclenche manuellement la synchronisation du registre Gemini.

    Retourne :
      - status       : "success" | "skipped" | "failure"
      - provider     : toujours "gemini"
      - discovered_count : nombre de modèles vus par l'API Google
      - new_count    : nouveaux modèles ajoutés en CANDIDATE
      - superseded_count : modèles passés en QUARANTINED
      - registry_count : total d'entrées Gemini dans le registre
      - timestamp    : ISO 8601 UTC
      - stats        : compteurs agrégés (total/success/failure)

    NE RETOURNE JAMAIS :
      - API keys
      - credentials
      - tokens
      - secrets
    """
    from core.models.registry_refresh_service import gemini_registry_service

    logger.info("[REGISTRY-ROUTER] Refresh manuel demandé.")
    try:
        result = await gemini_registry_service.trigger()
    except Exception as exc:
        logger.warning(
            "[REGISTRY-ROUTER] Refresh manuel ÉCHEC : %s : %s",
            type(exc).__name__,
            exc,
        )
        return {
            "status": "failure",
            "provider": "gemini",
            "error_type": type(exc).__name__,
            # On ne retourne PAS exc.args / str(exc) — peut contenir des URLs/clés
            "stats": gemini_registry_service.stats(),
        }

    return result


@router.get("/stats/gemini")
async def gemini_registry_stats() -> dict:
    """
    Retourne les compteurs d'observabilité du refresh Gemini.
    Aucun secret dans la réponse.
    """
    from core.models.registry_refresh_service import gemini_registry_service

    return gemini_registry_service.stats()
