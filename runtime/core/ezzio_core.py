from runtime.identity.persona import EzzioPersona
from runtime.cognition.router import HybridCognitiveRouter
from runtime.telemetry.collector import TelemetryCollector
from runtime.recovery.queue.bus import RecoveryEventBus

class EzzioCore:
    """Noyau central universel d'E-zzio. Gère la pensée, la mémoire et la sécurité de manière agnostique."""
    
    def __init__(self, telemetry: TelemetryCollector, recovery: RecoveryEventBus):
        self.telemetry = telemetry
        self.recovery = recovery
        self.persona = EzzioPersona()
        self.router = HybridCognitiveRouter()

    async def think(self, user_id: str, message: str, context_history: list) -> str:
        system_prompt = self.persona.get_system_prompt()
        history_text = "\n".join([f"{msg['role']}: {msg['content']}" for msg in context_history[-5:]])
        full_prompt = f"Historique:\n{history_text}\n\nNouveau message:\n{message}"

        # Le routeur décide s'il utilise le CPU Local ou Gemini Pro
        response = await self.router.generate_response(
            prompt=full_prompt,
            system_prompt=system_prompt,
            force_local=False 
        )
        return response
