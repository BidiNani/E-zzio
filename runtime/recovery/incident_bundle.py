import json
import hashlib
import uuid
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional

from runtime.recovery.contracts import IncidentBundle, Severity, SEVERITY_SCORES, IncidentCategory
from runtime.recovery.store import IncidentStore
from runtime.recovery.analyzers import DEFAULT_ANALYZERS
from runtime.telemetry.collector import TelemetryCollector

class IncidentBundleGenerator:
    """Générateur d'Incidents Forensiques scellés avec chaîne d'analyseurs extensibles."""

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
        
        # Contexte d'analyse pour les plugins
        eval_context = {
            "execution_id": execution_id,
            "action_name": action_name,
            "severity": severity_val,
            "category": category_val,
            "context_signature_valid": context_signature_valid,
            "telemetry_snapshot": telemetry_snapshot,
            "error_details": error_details
        }

        root_candidates = []
        for analyzer in self.analyzers:
            root_candidates.extend(analyzer.analyze(eval_context))

        if error_details:
            root_candidates.append(f"TRACE_DETAIL: {error_details}")

        meta = metadata or {}
        if error_details:
            meta["error_details"] = error_details

        # Calcul du digest d'intégrité canonique
        canonical = {
            "incident_id": incident_id,
            "timestamp": timestamp,
            "severity": severity_val,
            "severity_score": severity_score,
            "category": category_val,
            "execution_id": execution_id,
            "action_name": action_name,
            "context_signature_valid": context_signature_valid,
            "payload_hash": payload_hash
        }
        bundle_hash = hashlib.sha256(json.dumps(canonical, sort_keys=True).encode('utf-8')).hexdigest()

        bundle = IncidentBundle(
            incident_id=incident_id,
            timestamp=timestamp,
            severity=severity_val,
            severity_score=severity_score,
            category=category_val,
            execution_id=execution_id,
            action_name=action_name,
            state_trace=state_trace or [],
            context_signature_valid=context_signature_valid,
            payload_hash=payload_hash,
            bundle_hash=bundle_hash,
            telemetry_snapshot=telemetry_snapshot,
            root_candidates=root_candidates,
            metadata=meta
        )

        self.store.save_bundle(bundle)
        return bundle
