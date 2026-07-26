import uuid
from datetime import datetime
from typing import List, Dict, Any
from runtime.memory.episode import Episode, EpisodeStep

class EpisodeExtractor:
    """Transforme une séquence d'événements bruts en épisodes cognitifs segmentés, incluant les échecs."""

    def __init__(self, max_duration_sec: int = 30):
        self.max_duration_sec = max_duration_sec

    def _parse_time(self, t_str: str) -> datetime:
        try:
            return datetime.fromisoformat(t_str)
        except Exception:
            return datetime.now()

    def extract_from_events(self, events: List[Dict[str, Any]]) -> List[Episode]:
        if not events:
            return []

        sorted_events = sorted(events, key=lambda x: x.get("timestamp", ""))
        episodes: List[Episode] = []
        current_steps: List[EpisodeStep] = []

        if not sorted_events:
            return []

        first_ev = sorted_events[0]
        current_session = first_ev.get("session_id", "system")
        current_trace = first_ev.get("trace_id", "unknown")
        current_goal = "General Execution"
        start_time_str = first_ev.get("timestamp", "")
        start_dt = self._parse_time(start_time_str)
        end_time_str = start_time_str
        outcome = "success"

        for ev in sorted_events:
            session_id = ev.get("session_id", "system")
            trace_id = ev.get("trace_id", "unknown")
            timestamp = ev.get("timestamp", "")
            current_dt = self._parse_time(timestamp)
            event_type = ev.get("event_type", "Unknown")
            payload = ev.get("payload", {})

            time_diff = (current_dt - start_dt).total_seconds()
            is_break = (
                session_id != current_session or
                trace_id != current_trace or
                time_diff > self.max_duration_sec
            )

            if is_break and current_steps:
                episode = Episode(
                    episode_id=str(uuid.uuid4()),
                    session_id=current_session,
                    trace_id=current_trace,
                    start_time=start_time_str,
                    end_time=end_time_str,
                    goal=current_goal,
                    steps=current_steps,
                    outcome=outcome,
                    importance=0.8 if outcome == "failure" else 0.6
                )
                episodes.append(episode)
                current_steps = []
                current_session = session_id
                current_trace = trace_id
                start_time_str = timestamp
                start_dt = current_dt
                current_goal = "General Execution"
                outcome = "success"

            # Détection du goal
            if "capability" in payload and "tool" in payload["capability"]:
                current_goal = f"Execute tool: {payload['capability']['tool']}"
            elif "event_type" in ev:
                current_goal = f"Event: {ev['event_type']}"

            # Analyse stricte du succès ou de l'échec
            execution = payload.get("execution", {})
            if "success" in payload and payload["success"] is False:
                outcome = "failure"
            elif "success" in execution and execution["success"] is False:
                outcome = "failure"

            step = EpisodeStep(
                event_id=ev.get("event_id", str(uuid.uuid4())),
                event_type=event_type,
                timestamp=timestamp,
                payload=payload
            )
            current_steps.append(step)
            end_time_str = timestamp

        # Dernier épisode
        if current_steps:
            episode = Episode(
                episode_id=str(uuid.uuid4()),
                session_id=current_session,
                trace_id=current_trace,
                start_time=start_time_str,
                end_time=end_time_str,
                goal=current_goal,
                steps=current_steps,
                outcome=outcome,
                importance=0.8 if outcome == "failure" else 0.6
            )
            episodes.append(episode)

        return episodes