"""
Nœuds asynchrones du graphe LangGraph pour E-ZzIO.
Découpage opérationnel Gemini :
- router_node -> gemini-3.5-flash-lite (classification JSON au vol)
- direct_node & rag_node -> gemini-3.7-flash (moteur d'équilibre et streaming SSE)
- self_repair_node -> gemini-3.1-pro (analyse AST et auto-guérison)
"""

import json
import logging
from typing import Any

from ezzio.config import settings
from ezzio.llm.client import get_llm_client
from ezzio.memory.context_window import get_context_manager
from ezzio.rag.engine import get_rag_engine
from ezzio.schemas import AgentState
from ezzio.tools.file_tools import list_project_files

logger = logging.getLogger("EzzioNodes")


async def router_node(state: AgentState) -> dict[str, Any]:
    """Analyse l'intention de la requête ultra-rapidement via gemini-3.5-flash-lite."""
    query = state.get("query", "")
    logger.info("Classification d'intention pour : '%s'", query[:60])

    system_prompt = (
        "Tu es le classifieur d'intention d'E-ZzIO.\n"
        "Analyse la requête de l'utilisateur et choisis la route optimale parmi :\n"
        "- 'self_repair' : Si la requête demande de scanner, lire, corriger, assainir, réparer ou modifier un fichier/code du projet.\n"
        "- 'rag' : Si la requête concerne l'architecture, la sécurité, les règles internes ou la documentation d'E-ZzIO.\n"
        "- 'direct' : Si c'est une question générale de programmation, logique, mathématiques ou conversation courante.\n\n"
        "Réponds STRICTEMENT au format JSON brut sans balises markdown :\n"
        '{"route": "rag" | "direct" | "self_repair", "reason": "courte justification"}'
    )

    llm = get_llm_client()
    try:
        raw_response, _ = await llm.ainvoke(
            prompt=query,
            system_prompt=system_prompt,
            temperature=0.0,
            model=settings.cloud_model_lite
        )
        clean_json = raw_response.strip()
        if clean_json.startswith("```"):
            clean_json = clean_json.split("\n", 1)[-1].rsplit("```", 1)[0].strip()
        parsed = json.loads(clean_json)
        decision = parsed.get("route", "direct").lower()
        if decision not in ["rag", "direct", "self_repair"]:
            decision = "direct"
    except Exception as err:
        logger.warning("Échec du parsing du routeur (%s) -> repli 'direct'", err)
        decision = "direct"

    logger.info("Route sélectionnée : [%s]", decision.upper())
    return {"route": decision}


async def rag_node(state: AgentState) -> dict[str, Any]:
    """Interroge la base documentaire et synthétise via gemini-3.7-flash."""
    query = state.get("query", "")
    thread_id = state.get("thread_id", "default_thread")
    logger.info("Exécution du pipeline RAG pour : '%s' via %s", query[:60], settings.cloud_model_primary)

    rag_engine = get_rag_engine()
    result = await rag_engine.aquery(query)

    # Enregistrement dans la mémoire de contexte
    ctx_mgr = get_context_manager()
    ctx_mgr.add_message(thread_id, "user", query)
    ctx_mgr.add_message(thread_id, "assistant", result.answer)

    return {
        "answer": result.answer,
        "sources": result.source_documents,
        "model_used": result.model_used
    }


async def direct_node(state: AgentState) -> dict[str, Any]:
    """Répond directement via gemini-3.7-flash avec injection du contexte glissant compressé."""
    query = state.get("query", "")
    thread_id = state.get("thread_id", "default_thread")
    logger.info("Exécution de la réponse directe via %s pour Thread: %s", settings.cloud_model_primary, thread_id)

    ctx_mgr = get_context_manager()
    history = ctx_mgr.get_pruned_context(thread_id)

    # Construction du prompt contextualisé
    context_blocks = []
    for msg in history[-6:]:
        role = "Utilisateur" if msg["role"] == "user" else "Assistant"
        context_blocks.append(f"{role}: {msg['content']}")

    history_str = "\n".join(context_blocks)
    full_prompt = f"Historique récent de la conversation :\n{history_str}\n\nNouvelle question : {query}" if history_str else query

    try:
        from core.cloud_brain_broker import build_system_prompt
        system_prompt = build_system_prompt()
    except Exception:
        system_prompt = (
            "Tu es E-ZZIO, l'âme numérique souveraine conçue par ton créateur et Mentor BidiNani. "
            "Réponds de façon technique, claire, structurée et précise."
        )

    llm = get_llm_client()
    answer, model_used = await llm.ainvoke(
        prompt=full_prompt,
        system_prompt=system_prompt,
        temperature=0.2,
        model=settings.cloud_model_primary
    )

    # Sauvegarde mémorielle
    ctx_mgr.add_message(thread_id, "user", query)
    ctx_mgr.add_message(thread_id, "assistant", answer)

    return {
        "answer": answer,
        "sources": [],
        "model_used": model_used
    }


async def self_repair_node(state: AgentState) -> dict[str, Any]:
    """Nœud d'auto-inspection et de réparation automatique du codebase via gemini-3.1-pro."""
    query = state.get("query", "")
    thread_id = state.get("thread_id", "default_thread")
    logger.info("Exécution de l'auto-réparation via %s pour : '%s'", settings.cloud_model_pro, query[:60])

    project_files = list_project_files()
    files_summary = "\n".join(project_files[:40])

    system_prompt = (
        "Tu es le module d'auto-diagnostic et d'auto-guérison profonde d'E-ZzIO.\n"
        "Tu as accès à l'arborescence et aux fichiers du projet.\n"
        f"Fichiers du projet actuellement disponibles ({len(project_files)} fichiers) :\n"
        f"{files_summary}\n\n"
        "Analyse la demande de l'utilisateur. Explique l'action de diagnostic ou de correction requise de façon claire et méthodique."
    )

    llm = get_llm_client()
    answer, model_used = await llm.ainvoke(
        prompt=query,
        system_prompt=system_prompt,
        temperature=0.1,
        model=settings.cloud_model_pro
    )

    ctx_mgr = get_context_manager()
    ctx_mgr.add_message(thread_id, "user", query)
    ctx_mgr.add_message(thread_id, "assistant", answer)

    return {
        "answer": answer,
        "sources": [{"metadata": {"source": "codebase_inspection", "total_files": len(project_files)}}],
        "model_used": f"{model_used} (Self-Repair)"
    }
