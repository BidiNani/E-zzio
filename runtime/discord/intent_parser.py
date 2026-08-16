"""
E-ZZIO V9.5.2 — Intent Parser & Classifier (Reinforced)
Transforme un message brut en une intention structurée et sécurisée.
"""
import re

class IntentParser:
    def parse(self, author: str, content: str) -> dict:
        content_lower = content.lower()

        # Détection stricte d'injection, de contournement de la Constitution ou d'ECOL
        invariants = ["ignore ecol", "ecol", "supprime les protections", "admin override", "plugin admin", "contourne"]
        if any(keyword in content_lower for keyword in invariants):
            return {
                "intent_id": "INTENT_SEC_001",
                "type": "PROTECTED_REQUEST",
                "source": "DISCORD",
                "author": author,
                "user_request": content,
                "decision": "DENIED",
                "reason": "SYSTEM_INVARIANT_PROTECTION"
            }

        # Détection d'ajout de capacité / acquisition
        if "ajoute" in content_lower or "installe" in content_lower or "créer un skill" in content_lower:
            capability = "MUSIC_CREATOR" if "musique" in content_lower else "IMAGE_CREATOR"
            return {
                "intent_id": "INTENT_ADD_001",
                "type": "ADD_CAPABILITY",
                "domain": "GENERATION",
                "source": "DISCORD",
                "author": author,
                "user_request": content,
                "required_capabilities": [capability],
                "risk": "MEDIUM"
            }

        # Détection d'analyse documentaire ou recherche
        if "résume" in content_lower or "analyse" in content_lower or "pdf" in content_lower:
            return {
                "intent_id": "INTENT_DOC_001",
                "type": "DOCUMENT_ANALYSIS",
                "source": "DISCORD",
                "author": author,
                "user_request": content,
                "required_capabilities": ["DOCUMENT_ANALYST"],
                "risk": "LOW"
            }

        # Par défaut : Requête de connaissance générique
        return {
            "intent_id": "INTENT_GEN_001",
            "type": "KNOWLEDGE_QUERY",
            "source": "DISCORD",
            "author": author,
            "user_request": content,
            "risk": "LOW"
        }
