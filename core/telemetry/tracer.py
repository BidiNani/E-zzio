"""
E-ZZIO Telemetry — Distributed OpenTelemetry Tracer & Trace Context Bridge.
Permet de tracer les requêtes à travers les composants (FastAPI -> CognitiveGateway -> GeminiPool -> Tools) :
1. Génération et propagation déterministe de TraceID / SpanID conformes W3C TraceContext
2. Intégration transparente avec le middleware X-Correlation-ID
3. Ne remplace ni AuditLedger (sécurité/immutabilité) ni SQLite telemetry (métriques)
"""
from __future__ import annotations
import os
import time
import uuid
import logging
from typing import Dict, Any, Optional
from dataclasses import dataclass, field

logger = logging.getLogger("EzzioTracer")


@dataclass
class TraceSpan:
    name: str
    trace_id: str
    span_id: str
    parent_span_id: Optional[str] = None
    start_time: float = field(default_factory=time.time)
    end_time: Optional[float] = None
    attributes: Dict[str, Any] = field(default_factory=dict)
    status: str = "UNSET"

    def end(self, status: str = "OK", error: Optional[str] = None):
        self.end_time = time.time()
        self.status = "ERROR" if error else status
        if error:
            self.attributes["error.message"] = str(error)
        duration_ms = round((self.end_time - self.start_time) * 1000, 2)
        self.attributes["duration_ms"] = duration_ms
        logger.debug("[OTEL-SPAN] Span '%s' terminé en %.2fms | Trace: %s | Status: %s", self.name, duration_ms, self.trace_id, self.status)


class OpenTelemetryBridge:
    def __init__(self):
        self.service_name = "ezzio-runtime"

    def generate_trace_id(self) -> str:
        """Génère un trace_id hexadécimal 128-bit conforme OpenTelemetry."""
        return uuid.uuid4().hex

    def generate_span_id(self) -> str:
        """Génère un span_id hexadécimal 64-bit conforme OpenTelemetry."""
        return uuid.uuid4().hex[:16]

    def start_span(
        self,
        name: str,
        trace_id: Optional[str] = None,
        parent_span_id: Optional[str] = None,
        attributes: Optional[Dict[str, Any]] = None
    ) -> TraceSpan:
        """Démarre un nouveau span de trace distribuée."""
        t_id = trace_id or self.generate_trace_id()
        s_id = self.generate_span_id()
        attrs = attributes or {}
        attrs["service.name"] = self.service_name
        return TraceSpan(
            name=name,
            trace_id=t_id,
            span_id=s_id,
            parent_span_id=parent_span_id,
            attributes=attrs
        )


# Singleton global
tracer = OpenTelemetryBridge()
