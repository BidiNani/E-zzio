from pathlib import Path
import json

class MemoryReplay:
    def __init__(self, store_path: str = "runtime/memory/events.jsonl"):
        self.store_path = Path(store_path)

    def load_all(self) -> list:
        if not self.store_path.exists():
            return []
        lines = self.store_path.read_text(encoding="utf-8").strip().splitlines()
        return [json.loads(line) for line in lines if line.strip()]

    def get_recent_skills(self, limit: int = 5) -> list:
        events = self.load_all()
        skill_events = [e for e in events if e.get("type") == "SKILL_EXECUTED"]
        return skill_events[-limit:]

    def summarize(self) -> dict:
        events = self.load_all()
        total = len(events)
        skills = [e for e in events if e.get("type") == "SKILL_EXECUTED"]
        return {
            "total_events": total,
            "total_skills_executed": len(skills),
            "last_skill": skills[-1].get("payload", {}).get("skill") if skills else None
        }

if __name__ == "__main__":
    replay = MemoryReplay()
    summary = replay.summarize()
    print(f"[REPLAY SUMMARY] Total: {summary['total_events']} | Skills: {summary['total_skills_executed']} | Dernier: {summary['last_skill']}")
