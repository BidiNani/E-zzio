from enum import Enum

class CognitiveState(Enum):
    IDLE = "IDLE"
    OBSERVING = "OBSERVING"
    ANALYZING = "ANALYZING"
    REASONING = "REASONING"
    ACTING = "ACTING"
    LEARNING = "LEARNING"
    ERROR = "ERROR"
