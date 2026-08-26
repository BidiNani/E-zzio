import re
from enum import Enum
from typing import Dict, Any, List, Optional


class IntentType(Enum):
    LOCAL_CHAT = "local_chat"  # Conversation courante -> Ollama
    DEEP_REASONING = "deep_reasoning"  # Raisonnement / Architecture complexe -> Gemini
    WEB_SEARCH = "web_search"  # Actualité / Liens / Doc récente -> Tavily / Jina
    MEMORY_QUERY = "memory_query"  # Rappel d'actions passées -> EvidenceStore
    CODE_EXECUTION = "code_execution"  # Exécution / Génération de scripts / Terminal
    VOICE_ACTION = "voice_action"  # Interaction vocale / Synthèse / Microphone
    CREATIVE_SYNTHESIS = "creative_synthesis"  # Création d'histoire, poème, persona


class IntentRouter:
    """Classifieur d'intention déterministe avec scoring de confiance et priorités contextuelles."""

    SEARCH_TRIGGERS = [
        r"\b(cherche|trouve|search|google|dernier|dernière|news|actualité|cours|prix)\b",
        r"\b(qui est|qu'est-ce que|documentation sur|doc de|changelog)\b",
        r"https?://",
    ]

    REASONING_TRIGGERS = [
        r"\b(architecture|refactor|analyse de code|optimise|benchmark|complexe|stratégie)\b",
        r"\b(pense pas à pas|step-by-step|conception|sécurité approfondie)\b",
    ]

    MEMORY_TRIGGERS = [r"\b(qu'avons-nous fait|rappel|historique|mémoire|précédemment|hier|audit)\b"]

    CODE_TRIGGERS = [
        r"\b(exécute|lance la commande|script python|terminal|powershell|bash|npm install|git commit|compile)\b",
        r"```(python|bash|sh|powershell|js|ts|json)",
    ]

    VOICE_TRIGGERS = [
        r"\b(écoute|parle|lis à voix haute|active le micro|tts|stt|synthèse vocale|audio)\b"
    ]

    CREATIVE_TRIGGERS = [
        r"\b(raconte une histoire|écris un poème|invente|compose|génère un dialogue créatif)\b"
    ]

    def classify(self, query: str) -> Dict[str, Any]:
        query_lower = query.lower()

        # 1. Détection mémoire / audit
        for pattern in self.MEMORY_TRIGGERS:
            if re.search(pattern, query_lower):
                return {"intent": IntentType.MEMORY_QUERY, "confidence": 0.90, "target_provider": "evidence_store"}

        # 2. Détection recherche web
        for pattern in self.SEARCH_TRIGGERS:
            if re.search(pattern, query_lower):
                return {"intent": IntentType.WEB_SEARCH, "confidence": 0.85, "target_provider": "tavily"}

        # 3. Détection exécution de code / commandes système
        for pattern in self.CODE_TRIGGERS:
            if re.search(pattern, query_lower):
                return {"intent": IntentType.CODE_EXECUTION, "confidence": 0.88, "target_provider": "system_executor"}

        # 4. Détection vocale
        for pattern in self.VOICE_TRIGGERS:
            if re.search(pattern, query_lower):
                return {"intent": IntentType.VOICE_ACTION, "confidence": 0.92, "target_provider": "voice_gateway"}

        # 5. Détection raisonnement lourd / architecture
        for pattern in self.REASONING_TRIGGERS:
            if re.search(pattern, query_lower):
                return {"intent": IntentType.DEEP_REASONING, "confidence": 0.80, "target_provider": "gemini"}

        # 6. Détection créative
        for pattern in self.CREATIVE_TRIGGERS:
            if re.search(pattern, query_lower):
                return {"intent": IntentType.CREATIVE_SYNTHESIS, "confidence": 0.85, "target_provider": "gemini"}

        # 7. Fallback par défaut : inférence souveraine locale
        return {"intent": IntentType.LOCAL_CHAT, "confidence": 1.0, "target_provider": "ollama"}
