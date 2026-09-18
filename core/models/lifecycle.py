"""E-ZZIO model lifecycle manager."""

from __future__ import annotations

import hashlib
import json
import time
from typing import Any

from .registry import (
    ModelLifecycle,
    ModelRecord,
    ModelRegistry,
)


class ModelLifecycleManager:
    """Converts provider discoveries into registry state."""

    def __init__(self, registry: ModelRegistry) -> None:
        self.registry = registry

    @staticmethod
    def fingerprint(metadata: dict[str, Any]) -> str:
        canonical = json.dumps(
            metadata,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        )

        return hashlib.sha256(
            canonical.encode("utf-8")
        ).hexdigest()

    def ingest_discovery(
        self,
        provider: str,
        discovered: list[dict[str, Any]],
    ) -> list[ModelRecord]:

        records: list[ModelRecord] = []
        now = time.time()

        for item in discovered:
            model_id = str(item["model_id"])
            source_hash = self.fingerprint(item)

            existing = self.registry.get(
                provider,
                model_id,
            )

            if existing:
                existing.metadata = item
                existing.source_hash = source_hash
                existing.last_verified = now
                records.append(existing)
                continue

            record = ModelRecord(
                model_id=model_id,
                provider=provider,
                lifecycle=ModelLifecycle.CANDIDATE.value,
                context_window=item.get("context_window"),
                max_output_tokens=item.get("max_output_tokens"),
                supports_chat=bool(item.get("supports_chat", False)),
                supports_json=bool(item.get("supports_json", False)),
                supports_tools=bool(item.get("supports_tools", False)),
                supports_reasoning=bool(
                    item.get("supports_reasoning", False)
                ),
                discovered_at=now,
                last_verified=now,
                source_hash=source_hash,
                metadata=item,
            )

            self.registry.upsert(record)
            records.append(record)

        self.registry.save()
        return records
