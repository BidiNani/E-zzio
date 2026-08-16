import uuid
from .contracts import VoiceRequest
from .cancellation import CancellationToken

class VoiceGateway:
    def __init__(self, engine, telemetry):
        self.engine = engine
        self.telemetry = telemetry

    async def speak(self, text, voice="af_bella", speed=1.0):
        request = VoiceRequest(
            request_id=str(uuid.uuid4()),
            text=text,
            voice=voice,
            speed=speed
        )
        token = CancellationToken()
        result = await self.engine.synthesize(
            request.text,
            request.voice,
            request.speed
        )
        self.telemetry.record(request, result)
        return result, token
