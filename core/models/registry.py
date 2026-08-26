"""E-ZZIO dynamic model registry."""

from __future__ import annotations

import json
import os
import tempfile
import time
from dataclasses import asdict, dataclass
from enum import StrEnum
from pathlib import Path
from threading import Lock
from typing import Any


class ModelTier(StrEnum):
    FAST = "FAST"
    MID = "MID"
    HEAVY = "HEAVY"
    SPECIALIZED = "SPECIALIZED"
    UNQUALIFIED = "UNQUALIFIED"


class ModelLifecycle(StrEnum):
    DISCOVERED = "DISCOVERED"
    CANDIDATE = "CANDIDATE"
    QUALIFYING = "QUALIFYING"
    QUALIFIED = "QUALIFIED"
    ACTIVE = "ACTIVE"
    SUPERSEDED = "SUPERSEDED"
    QUARANTINED = "QUARANTINED"
    RETIRED = "RETIRED"


@dataclass(slots=True)
class ModelRecord:
    model_id: str
    provider: str

    updated_at: str | None = None
    last_quarantine_operator: str | None = None
    last_quarantine_reason: str | None = None
    last_quarantine_at: str | None = None
    rehabilitation_reason: str | None = None
    rehabilitated_by: str | None = None
    rehabilitated_at: str | None = None
    rehabilitation_count: int = 0
    historical_failures: int = 0
    tier: str = ModelTier.UNQUALIFIED.value
    lifecycle: str = ModelLifecycle.DISCOVERED.value

    context_window: int | None = None
    max_output_tokens: int | None = None

    supports_chat: bool = False
    supports_json: bool = False
    supports_tools: bool = False
    supports_reasoning: bool = False

    latency_ms: float | None = None
    qualification_score: float = 0.0

    discovered_at: float = 0.0
    last_verified: float = 0.0

    source_hash: str = ""

    failure_count: int = 0
    success_count: int = 0

    metadata: dict[str, Any] | None = None


class ModelRegistry:
    """Persistent registry with atomic JSON writes."""

    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)

        self._models: dict[str, ModelRecord] = {}
        self._lock = Lock()

        self.load()

    @staticmethod
    def key(provider: str, model_id: str) -> str:
        return f"{provider.lower()}:{model_id}"

    def load(self) -> None:
        if not self.path.exists():
            return

        try:
            data = json.loads(
                self.path.read_text(encoding="utf-8")
            )

            models = data.get("models", {})

            for key, raw in models.items():
                self._models[key] = ModelRecord(**raw)

        except Exception:
            self._models = {}

    def save(self) -> None:
        with self._lock:
            payload = {
                "schema_version": 1,
                "generated_at": time.time(),
                "models": {
                    key: asdict(record)
                    for key, record in self._models.items()
                },
            }

            self.path.parent.mkdir(parents=True, exist_ok=True)

            fd, temporary = tempfile.mkstemp(
                prefix=".registry_",
                suffix=".tmp",
                dir=self.path.parent,
                text=True,
            )

            try:
                with os.fdopen(fd, "w", encoding="utf-8") as handle:
                    json.dump(
                        payload,
                        handle,
                        ensure_ascii=False,
                        indent=2,
                        sort_keys=True,
                    )
                    handle.flush()
                    os.fsync(handle.fileno())

                os.replace(temporary, self.path)

            finally:
                if os.path.exists(temporary):
                    os.unlink(temporary)

    def upsert(self, record: ModelRecord) -> None:
        with self._lock:
            self._models[
                self.key(record.provider, record.model_id)
            ] = record

    def get(
        self,
        provider: str,
        model_id: str,
    ) -> ModelRecord | None:
        return self._models.get(
            self.key(provider, model_id)
        )

    