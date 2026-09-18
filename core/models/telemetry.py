"""E-ZZIO secret-safe telemetry."""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any


class SafeTelemetry:

    FORBIDDEN_KEYS = {
        "api_key",
        "apikey",
        "secret",
        "token",
        "password",
        "authorization",
        "credential",
        "secret_value",
    }

    def __init__(
        self,
        directory: str | Path,
    ) -> None:

        self.directory = Path(directory)
        self.directory.mkdir(
            parents=True,
            exist_ok=True,
        )

    @classmethod
    def sanitize(
        cls,
        value: Any,
    ) -> Any:

        if isinstance(value, dict):
            result = {}
            for key, item in value.items():
                if str(key).lower() in cls.FORBIDDEN_KEYS:
                    result[key] = "[REDACTED]"
                else:
                    result[key] = cls.sanitize(item)
            return result

        if isinstance(value, (list, tuple)):
            return [cls.sanitize(item) for item in value]

        return value

    def emit(
        self,
        event: str,
        payload: dict[str, Any],
    ) -> None:

        record = {
            "timestamp": time.time(),
            "event": event,
            "payload": self.sanitize(payload),
        }

        path = self.directory / "fabric_telemetry.jsonl"

        with path.open("a", encoding="utf-8") as handle:
            handle.write(
                json.dumps(
                    record,
                    ensure_ascii=False,
                    sort_keys=True,
                )
                + "\n"
            )
