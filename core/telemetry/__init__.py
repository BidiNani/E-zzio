"""E-ZZIO Core — Telemetry package."""
from core.telemetry.tracer import OpenTelemetryBridge, TraceSpan, tracer

__all__ = ["OpenTelemetryBridge", "TraceSpan", "tracer"]
