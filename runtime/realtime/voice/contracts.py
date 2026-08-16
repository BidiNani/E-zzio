from dataclasses import dataclass
from time import time

@dataclass
class VoiceRequest:
    request_id: str
    text: str
    voice: str = "af_bella"
    speed: float = 1.0

@dataclass
class VoiceMetrics:
    request_id: str
    ttfa_sec: float
    rtf: float
    audio_duration: float
    timestamp: float = time()
