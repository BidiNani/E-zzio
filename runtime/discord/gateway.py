"""
E-ZZIO V9.5.2 — Discord Gateway & Response Handler (Corrected)
Coordonne la réception du message, l'analyseur, le moteur de confiance et le ledger.
"""
from runtime.discord.intent_parser import IntentParser
from runtime.confidence.engine import ConfidenceEngine
from runtime.experience.experience_ledger import ExperienceLedger

class DiscordGateway:
    def __init__(self):
        self.parser = IntentParser()
        self.confidence_engine = ConfidenceEngine()
        self.ledger = ExperienceLedger()

    def process_message(self, author: str, content: str) -> dict:
        # 1. Parsing de l'intention
        intent = self.parser.parse(author, content)

        # Si l'Intent Parser a détecté une injection ou un contournement direct
        if intent.get("decision") == "DENIED":
            self.ledger.log_failure(intent["intent_id"], "DISCORD_GATEWAY", intent["type"], intent["reason"])
            return {
                "status": "DENIED",
                "intent": intent,
                "response": f"Requête rejetée : {intent['reason']}"
            }

        # 2. Vérification par le Confidence Engine (et Invariants ECOL)
        plan = {"target": intent.get("type", "UNKNOWN")}
        confidence_res = self.confidence_engine.analyze(intent["intent_id"], plan)

        if confidence_res["decision"] == "DENIED":
            self.ledger.log_failure(intent["intent_id"], "DISCORD_GATEWAY", intent["type"], "SYSTEM_INVARIANT_PROTECTION")
            return {
                "status": "DENIED",
                "intent": intent,
                "response": "Requête rejetée : Violation d'invariant systémique ou de la Constitution."
            }

        # 3. Traitement selon le type d'intention
        if intent["type"] == "ADD_CAPABILITY":
            self.ledger.log_success(intent["intent_id"], intent["required_capabilities"], 150.0, 300.0, confidence_res["confidence"])
            return {
                "status": "PROPOSAL_READY",
                "intent": intent,
                "confidence": confidence_res["confidence"],
                "response": f"Capacité candidate identifiée ({intent['required_capabilities'][0]}). Analyse de sécurité réussie. En attente de validation utilisateur."
            }

        if intent["type"] == "DOCUMENT_ANALYSIS":
            self.ledger.log_success(intent["intent_id"], intent["required_capabilities"], 250.0, 450.0, confidence_res["confidence"])
            return {
                "status": confidence_res["decision"],
                "intent": intent,
                "confidence": confidence_res["confidence"],
                "response": f"Intention document analysée. Décision du moteur de confiance : {confidence_res['decision']} (Score: {confidence_res['confidence']})."
            }

        # Par défaut
        return {
            "status": "SUCCESS",
            "intent": intent,
            "response": "Intention traitée et enregistrée dans le Ledger."
        }
