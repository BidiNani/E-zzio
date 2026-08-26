from __future__ import annotations
import json
import threading
from pathlib import Path


class TrustScorer:
    """Moteur de réputation persistant (scores sur disque et historique d'audit)."""

    def __init__(self, storage_dir: Path = Path("runtime/governance/trust"), default_score: float = 100.0):
        self.storage_dir = storage_dir
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        self.scores_file = self.storage_dir / "scores.json"
        self.history_file = self.storage_dir / "history.jsonl"
        self._default_score = default_score
        self._lock = threading.RLock()
        self._scores = self._load_scores()

    def _load_scores(self) -> dict:
        if self.scores_file.exists():
            try:
                return json.loads(self.scores_file.read_text(encoding="utf-8"))
            except Exception:
                pass
        return {}

    def _save_scores(self):
        self.scores_file.write_text(json.dumps(self._scores, indent=2), encoding="utf-8")

    def get_score(self, actor: str) -> float:
        with self._lock:
            return self._scores.get(actor, self._default_score)

    def penalize(self, actor: str, points: float = 15.0, reason: str = "Unspecified"):
        with self._lock:
            current = self.get_score(actor)
            new_score = max(0.0, current - points)
            self._scores[actor] = new_score
            self._save_scores()

            history_entry = {"actor": actor, "delta": -points, "score": new_score, "reason": reason}
            with open(self.history_file, "a", encoding="utf-8") as f:
                f.write(json.dumps(history_entry) + "\n")

    def reward(self, actor: str, points: float = 2.0, reason: str = "Success"):
        with self._lock:
            current = self.get_score(actor)
            new_score = min(100.0, current + points)
            self._scores[actor] = new_score
            self._save_scores()

            history_entry = {"actor": actor, "delta": points, "score": new_score, "reason": reason}
            with open(self.history_file, "a", encoding="utf-8") as f:
                f.write(json.dumps(history_entry) + "\n")

    def is_trusted(self, actor: str, threshold: float = 50.0) -> bool:
        return self.get_score(actor) >= threshold
