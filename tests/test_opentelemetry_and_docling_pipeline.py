"""
E-ZZIO Test Suite — OpenTelemetry, Docling Pipeline & OpenCode Candidate Certification.
Certifie :
1. Le pont OpenTelemetry (génération TraceID W3C 128-bit, SpanID 64-bit, calcul de durée, statuts)
2. La double voie d'UniversalReader (parseur natif déterministe + sas Docling pour documents complexes)
3. L'enregistrement contractuel de la capacité candidate OpenCode dans CapabilityRegistry
"""
import time
from pathlib import Path

import pytest

from core.capabilities.registry import CapabilityRegistry, QualificationStatus
from core.perception.universal_reader import UniversalFileReader, universal_reader
from core.telemetry.tracer import OpenTelemetryBridge, TraceSpan, tracer


def test_opentelemetry_tracer_span_lifecycle():
    bridge = OpenTelemetryBridge()

    # 1. Démarrage de Span
    trace_id = bridge.generate_trace_id()
    assert len(trace_id) == 32  # 128-bit hex
    span = bridge.start_span("cognitive_gateway_dispatch", trace_id=trace_id, attributes={"model": "gemini-3.7-flash"})

    assert span.name == "cognitive_gateway_dispatch"
    assert span.trace_id == trace_id
    assert len(span.span_id) == 16  # 64-bit hex
    assert span.attributes["model"] == "gemini-3.7-flash"
    assert span.attributes["service.name"] == "ezzio-runtime"
    assert span.status == "UNSET"

    # 2. Clôture de Span
    time.sleep(0.01)
    span.end(status="OK")
    assert span.status == "OK"
    assert span.end_time is not None
    assert span.attributes["duration_ms"] >= 5.0  # Au moins 5ms


def test_opentelemetry_tracer_error_handling():
    bridge = OpenTelemetryBridge()
    span = bridge.start_span("gemini_pool_rotation")
    span.end(error="429 Resource Exhausted")
    assert span.status == "ERROR"
    assert span.attributes["error.message"] == "429 Resource Exhausted"


def test_universal_reader_complex_document_dual_mode(tmp_path):
    # Création d'un document test Markdown
    sample_file = tmp_path / "sample_doc.md"
    sample_file.write_text("# Rapport d'Architecture E-ZzIO\n\n- Point 1: Gemini Pool Primary\n- Point 2: yt-dlp", encoding="utf-8")

    reader = UniversalFileReader()
    res = reader.read_complex_document(sample_file)

    assert res["ok"] is True
    assert res["file_path"] == str(sample_file)
    assert "Rapport d'Architecture E-ZzIO" in res["content"]
    assert res["parser"] in ("docling_v2", "native_universal_fallback")


def test_opencode_candidate_in_registry():
    reg = CapabilityRegistry()
    qual = reg.get_qualification("opencode-candidate")
    assert qual is not None
    assert qual.status == QualificationStatus.CANDIDATE
    assert qual.category == "coding_worker"
    assert "code.patch" in qual.permissions
    assert qual.fail_closed is True
