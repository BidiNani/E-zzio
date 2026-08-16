from __future__ import annotations
import os
from typing import Any, Dict, List, Optional
from core.router.intent_router import IntentRouter, IntentType
from core.memory.unified_gateway import UnifiedMemoryGateway
from core.decision_router import DecisionRouter, SearchMode
from core.providers.ollama_provider import OllamaProvider
from core.providers.tavily_provider import TavilyProvider
from core.providers.jina_provider import JinaProvider
from core.providers.gemini_provider import GeminiProvider

class EzzioPersona:
    """Définition de l'identité et des directives fondamentales d'E-ZZIO."""
    def get_system_prompt(self) -> str:
        return (
            "Tu es E-ZZIO, un agent IA souverain, technique et direct.\n"
            "Principes:\n"
            "1. Souveraineté locale d'abord (Ollama/Qwen en TIER-1)\n"
            "2. Escalade cloud maîtrisée (Gemini 3.7 en TIER-2)\n"
            "3. Traçabilité totale (audit via UnifiedMemoryGateway)\n"
            "4. Zéro complaisance, précision technique et concision."
        )

class EzzioCore:
    """Noyau central universel d'E-ZZIO avec pipeline cognitif autonome."""

    def __init__(
        self,
        telemetry: Optional[Any] = None,
        recovery: Optional[Any] = None,
        memory_gateway: Optional[UnifiedMemoryGateway] = None,
        intent_router: Optional[IntentRouter] = None,
        decision_router: Optional[DecisionRouter] = None
    ):
        self.telemetry = telemetry
        self.recovery = recovery
        self.persona = EzzioPersona()
        self.memory = memory_gateway or UnifiedMemoryGateway("runtime/evidence/evidence.db")
        self.intent_router = intent_router or IntentRouter()
        
        if decision_router:
            self.decision_router = decision_router
        else:
            self.decision_router = DecisionRouter([
                OllamaProvider(),
                TavilyProvider(),
                JinaProvider(),
                GeminiProvider()
            ])

    async def init(self) -> None:
        """Initialise la base de mémoire et de preuves (WAL)."""
        await self.memory.init()

    async def think(self, user_id: str, message: str, session_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Pipeline cognitif autonome:
        1. Enregistre le message utilisateur
        2. Extrait l'historique conversationnel récent
        3. Détermine l'intention (IntentRouter)
        4. Exécute l'action appropriée (Recherche Web, Raisonnement Cloud, Mémoire, ou Inférence Locale)
        5. Enregistre la réponse générée dans la mémoire de session
        6. Retourne le résultat structuré
        """
        effective_session = session_id or f"sess_{user_id}"
        
        # 1. Persistance message utilisateur
        await self.memory.record_message(effective_session, "user", message)
        
        # 2. Récupération contexte récent
        history = await self.memory.get_session_history(effective_session, limit=6)
        history_text = "\n".join([f"{m['role']}: {m['content']}" for m in history[:-1]])

        # 3. Détection d'intention
        classification = self.intent_router.classify(message)
        intent = classification.get("intent", IntentType.LOCAL_CHAT)
        
        system_prompt = self.persona.get_system_prompt()
        response_text = ""
        used_provider = classification.get("target_provider", "ollama")
        mode_used = "local"
        extra_data = {}

        # 4. Branchement d'exécution selon l'intention
        if intent == IntentType.MEMORY_QUERY:
            # Recherche croisée preuves + chat
            mem_results = await self.memory.search_memory(message, limit=5)
            extra_data = mem_results
            evidences = mem_results.get("evidences", [])
            chat_hist = mem_results.get("chat_history", [])
            
            context_summary = f"Preuves trouvées ({len(evidences)}):\n"
            for ev in evidences[:3]:
                context_summary += f"- [{ev.get('provider')}] {ev.get('query')}\n"
            context_summary += f"\nHistorique passé ({len(chat_hist)}):\n"
            for ch in chat_hist[:3]:
                context_summary += f"- [{ch.get('role')}]: {ch.get('content')}\n"

            synth_prompt = (
                f"{system_prompt}\n\n"
                f"Question mémoire:\n'{message}'\n\n"
                f"Données mémoire:\n{context_summary}\n\n"
                "Synthétise les faits retrouvés."
            )
            res = await self.decision_router.search(synth_prompt, mode=SearchMode.LOCAL)
            response_text = res.get("data", {}).get("text", "")
            used_provider = res.get("provider", "ollama")
            mode_used = "memory_recall"

        elif intent == IntentType.WEB_SEARCH:
            # Recherche Web augmentée
            search_res = await self.decision_router.search(message, mode=SearchMode.FAST)
            results = search_res.get("data", {}).get("results", [])
            used_provider = search_res.get("provider", "tavily")
            mode_used = "web_search"
            extra_data = search_res.get("data", {})
            
            context_web = "\n".join([f"- {r.get('title')}: {r.get('url')} | {r.get('content', '')[:120]}" for r in results[:4]])
            synth_prompt = (
                f"{system_prompt}\n\n"
                f"Question: {message}\n\n"
                f"Résultats Web ({used_provider}):\n{context_web}\n\n"
                "Synthétise une réponse directe."
            )
            synth_res = await self.decision_router.search(synth_prompt, mode=SearchMode.LOCAL)
            response_text = synth_res.get("data", {}).get("text", "")
            if not response_text:
                response_text = f"Recherche complétée ({len(results)} résultats trouvés via {used_provider})."

        elif intent == IntentType.DEEP_REASONING:
            # Raisonnement lourd Cloud (Gemini 3.7)
            full_prompt = f"{system_prompt}\n\nHistorique:\n{history_text}\n\nDemande:\n{message}"
            res = await self.decision_router.search(full_prompt, mode=SearchMode.GOOGLE)
            response_text = res.get("data", {}).get("text", "")
            used_provider = res.get("provider", "gemini")
            mode_used = "deep_reasoning"
            extra_data = res.get("data", {})

        else:  # LOCAL_CHAT
            # Inférence souveraine locale (Ollama / Qwen)
            full_prompt = f"{system_prompt}\n\nHistorique:\n{history_text}\n\nMessage:\n{message}"
            res = await self.decision_router.search(full_prompt, mode=SearchMode.LOCAL)
            response_text = res.get("data", {}).get("text", "")
            used_provider = res.get("provider", "ollama")
            mode_used = "local_chat"
            extra_data = res.get("data", {})

        # 5. Persistance de la réponse générée
        await self.memory.record_message(
            effective_session,
            "assistant",
            response_text,
            metadata={"provider": used_provider, "intent": intent.value, "mode": mode_used}
        )

        return {
            "response": response_text,
            "intent": intent.value,
            "provider": used_provider,
            "mode": mode_used,
            "session_id": effective_session,
            "data": extra_data
        }
