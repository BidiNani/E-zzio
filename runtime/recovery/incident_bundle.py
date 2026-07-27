import json
import hashlib
import uuid
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional

from runtime.recovery.contracts import IncidentBundle, Severity, SEVERITY_SCORES, IncidentCategory, Finding
from runtime.recovery.store import IncidentStore
from runtime.recovery.analyzers import DEFAULT_ANALYZERS
from runtime.telemetry.collector import TelemetryCollector
from runtime.telemetry.events import TelemetryEvent, EventType

class IncidentBundleGenerator:
    """Générateur Forensique (v2.7.1.1) scellant à 100% l'intégrité et émettant vers le Ledger."""

    def __init__(self, store: Optional[IncidentStore] = None, collector: Optional[TelemetryCollector] = None, analyzers: Optional[List] = None):
        self.store = store or IncidentStore()
        self.collector = collector or TelemetryCollector()
        self.analyzers = analyzers if analyzers is not None else DEFAULT_ANALYZERS

    def generate_incident(
        self,
        execution_id: str,
        action_name: str,
        severity: Severity,
        category: IncidentCategory,
        payload: Dict[str, Any],
        context_signature_valid: bool,
        trace_id: Optional[str] = None,
        span_id: Optional[str] = None,
        state_trace: Optional[List[Dict[str, Any]]] = None,
        error_details: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> IncidentBundle:
        
        timestamp = datetime.now(timezone.utc).isoformat()
        incident_id = f"inc_{uuid.uuid4().hex[:8]}"
        
        severity_val = severity.value if isinstance(severity, Severity) else str(severity)
        severity_enum = Severity(severity_val) if severity_val in Severity.__members__ else Severity.INFO
        severity_score = SEVERITY_SCORES.get(severity_enum, 10)

        category_val = category.value if isinstance(category, IncidentCategory) else str(category)

        payload_str = json.dumps(payload, sort_keys=True, default=str)
        payload_hash = hashlib.sha256(payload_str.encode('utf-8')).hexdigest()
        
        telemetry_snapshot = self.collector.get_health_endpoint()
        
        eval_context = {
            "execution_id": execution_id,
            "action_name": action_name,
            "severity": severity_val,
            "category": category_val,
            "context_signature_valid": context_signature_valid,
            "telemetry_snapshot": telemetry_snapshot,
            "error_details": error_details
        }

        raw_findings: List[Finding] = []
        root_candidates = []
        for analyzer in self.analyzers:
            res = analyzer.analyze(eval_context)
            raw_findings.extend(res)
            for f in res:
                root_candidates.append(f"{f.type}: {f.evidence.get('details', f.evidence.get('error', 'Detected'))}")

        if error_details and not root_candidates:
            root_candidates.append(f"TRACE_DETAIL: {error_details}")

        findings_dict = [f.to_dict() for f in raw_findings]
        meta = metadata or {}
        if error_details:
            meta["error_details"] = error_details

        state_tr = state_trace or []

        # Construction du bundle temporaire sans hash
        temp_bundle = IncidentBundle(
            incident_id=incident_id,
            timestamp=timestamp,
            severity=severity_val,
            severity_score=severity_score,
            category=category_val,
            execution_id=execution_id,
            action_name=action_name,
            trace_id=trace_id,
            span_id=span_id,
            state_trace=state_tr,
            context_signature_valid=context_signature_valid,
            payload_hash=payload_hash,
            bundle_hash="",
            telemetry_snapshot=telemetry_snapshot,
            findings=findings_dict,
            root_candidates=root_candidates,
            metadata=meta
        )

        # Calcul du hash canonique à 100%
        final_hash = temp_bundle.compute_canonical_hash()

        bundle = IncidentBundle(
            incident_id=incident_id,
            timestamp=timestamp,
            severity=severity_val,
            severity_score=severity_score,
            category=category_val,
            execution_id=execution_id,
            action_name=action_name,
            trace_id=trace_id,
            span_id=span_id,
            state_trace=state_tr,
            context_signature_valid=context_signature_valid,
            payload_hash=payload_hash,
            bundle_hash=final_hash,
            telemetry_snapshot=telemetry_snapshot,
            findings=findings_dict,
            root_candidates=root_candidates,
            metadata=meta
        )

        # Persistance SQLite + Export JSON
        self.store.save_bundle(bundle)

        # Connexion avec l'Evidence Ledger via TelemetryEvent
        self.collector.record_event(TelemetryEvent(
            event_type=EventType.SYSTEM_HEALTH_CHECK,
            payload={
                "event": "INCIDENT_CREATED",
                "incident_id": bundle.incident_id,
                "severity": bundle.severity,
                "severity_score": bundle.severity_score,
                "bundle_hash": bundle.bundle_hash,
                "execution_id": bundle.execution_id,
                "timestamp": bundle.timestamp
            }
        ))

        return bundle
