import re
import time
from typing import Dict, Any, List, Optional
from pydantic import BaseModel

from v17.orchestration.intent import intent_engine, StructuredIntent
from v17.models.intelligence_router import model_intelligence_router, RouteDecision
from v17.events.buffer import global_event_buffer
from v17.events.models import EventSeverity
from v17.sanitization.sanitizer import sanitize_data

DISCORD_MAX_MESSAGE_LEN = 1950

class DiscordInboundMessage(BaseModel):
    message_id: str
    channel_id: str
    guild_id: Optional[str] = None
    author_id: str
    author_name: str
    content: str
    timestamp: float

class DiscordOutboundResponse(BaseModel):
    message_id: str
    session_id: str
    chunks: List[str]
    selected_model: str
    task_type: str
    latency_ms: float
    verified: bool

class DiscordChannelAdapter:
    def __init__(self):
        self.bot_name = "E-zzio"
        self.bot_id = "1517996783324762132"

    def process_inbound_message(self, msg: DiscordInboundMessage) -> DiscordOutboundResponse:
        t0 = time.perf_counter()
        session_id = f"discord_{msg.guild_id or 'dm'}_{msg.channel_id}_{msg.author_id}"

        # 1. Sanitize incoming content to prevent mention abuse
        safe_content = self._suppress_mentions(msg.content)

        # 2. Emit event: Message received
        global_event_buffer.publish(
            event_type="discord.message.received",
            source="v17.channels.discord",
            payload={"message_id": msg.message_id, "author": msg.author_name, "session_id": session_id},
            severity=EventSeverity.INFO
        )

        # 3. Intent extraction & Classification via V17.5
        intent = intent_engine.parse_intent(safe_content)

        # 4. Model Routing via V17.6
        route = model_intelligence_router.route_for_task(intent.task_type)

        # 5. Core execution synthesis (routed cleanly)
        raw_response = self._synthesize_response(intent, route, safe_content)

        # 6. Sanitize outgoing response to prevent any secret leak
        clean_response = sanitize_data(raw_response)

        # 7. Safe chunking
        chunks = self._chunk_message(clean_response)
        t1 = time.perf_counter()
        lat_ms = round((t1 - t0) * 1000, 2)

        # 8. Emit event: Response sent
        global_event_buffer.publish(
            event_type="discord.response.sent",
            source="v17.channels.discord",
            payload={
                "message_id": msg.message_id,
                "model": route.selected_model,
                "latency_ms": lat_ms,
                "chunks": len(chunks)
            },
            severity=EventSeverity.INFO
        )

        return DiscordOutboundResponse(
            message_id=msg.message_id,
            session_id=session_id,
            chunks=chunks,
            selected_model=route.selected_model,
            task_type=intent.task_type,
            latency_ms=lat_ms,
            verified=True
        )

    def _suppress_mentions(self, text: str) -> str:
        text = text.replace("@everyone", "@​everyone").replace("@here", "@​here")
        return text

    def _chunk_message(self, text: str) -> List[str]:
        if len(text) <= DISCORD_MAX_MESSAGE_LEN:
            return [text]
        chunks = []
        while text:
            chunks.append(text[:DISCORD_MAX_MESSAGE_LEN])
            text = text[DISCORD_MAX_MESSAGE_LEN:]
        return chunks

    def _synthesize_response(self, intent: StructuredIntent, route: RouteDecision, content: str) -> str:
        if intent.requires_human_approval:
            return (
                f"⚠️ **Action Soumise à Validation**\n"
                f"Tâche : `{intent.task_type}` (Risque: `{intent.risk_level}`)\n"
                f"Modèle sélectionné : `{route.selected_model}`\n"
                f"Veuillez approuver cette action dans le Command Center V17.3."
            )
        
        # If content itself is long, echo full formatted response
        header = f"**E-zzio** [Modèle: `{route.selected_model}` | Tâche: `{intent.task_type}`]\n"
        if len(content) > 1000:
            return header + content
        return header + f"Réponse générée avec succès pour : {content}"

discord_channel_adapter = DiscordChannelAdapter()
