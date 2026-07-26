from dataclasses import dataclass, field
from typing import List, Dict, Any

@dataclass
class EpisodeStep:
    event_id: str
    event_type: str
    timestamp: str
    payload: Dict[str, Any]

@dataclass
class Episode:
    episode_id: str
    session_id: str
    trace_id: str
    start_time: str
    end_time: str
    goal: str
    steps: List[EpisodeStep] = field(default_factory=list)
    outcome: str = "unknown"
    importance: float = 0.5
    consolidated: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "episode_id": self.episode_id,
            "session_id": self.session_id,
            "trace_id": self.trace_id,
            "start_time": self.start_time,
            "end_time": self.end_time,
            "goal": self.goal,
            "steps": [
                {
                    "event_id": s.event_id,
                    "event_type": s.event_type,
                    "timestamp": s.timestamp,
                    "payload": s.payload
                } for s in self.steps
            ],
            "outcome": self.outcome,
            "importance": self.importance,
            "consolidated": self.consolidated
        }