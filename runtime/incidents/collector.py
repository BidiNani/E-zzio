from __future__ import annotations
import uuid
import json
from datetime import datetime, timezone
from typing import Any, Callable, Dict, List, Optional

from .model import IncidentRecord, IncidentSeverity, IncidentCategory


class IncidentCollector:
    """
    Observateur non-intrusif du runtime V4.2.
    Collecte les exceptions, erreurs et événements pour générer des IncidentRecords normalisés.

    GARDE-FOU STRICT : Le collector ne possède AUCUN droit de mutation ou d'intervention
    sur le noyau V4.2 (pas de modification de FSM, pas de libération de lock, pas de bypass).
    """

    def __init__(self, sink_callback: Optional[Callable[[IncidentRecord], None]] = None) -> None:
        self._sink_callback = sink_callback

    def register_sink(self, sink_callback: Callable[[IncidentRecord], None]) -> None:
        """Enregistre un récepteur de preuves (ex: Evidence Ledger / Stockage append-only)."""
        self._sink_callback = sink_callback

    def capture_exception(
        self,
        exc: Exception,
        source: str = "kernel.unknown",
        phase: str = "PRE_BOOT",
        runtime_state: str = "PRE_BOOT",
        severity: IncidentSeverity = IncidentSeverity.CRITICAL,
        category: IncidentCategory = IncidentCategory.EXECUTION_ERROR,
        evidence: Optional[List[Dict[str, Any]]] = None,
        context_hash: str = "",
    ) -> IncidentRecord:
        """
        Capture une exception levée dans le runtime et produit un enregistrement d'incident normalisé.
        """
        incident_id = str(uuid.uuid4())
        timestamp = datetime.now(timezone.utc).isoformat()
        error_type = type(exc).__name__
        message = str(exc)

        record = IncidentRecord(
            incident_id=incident_id,
            timestamp=timestamp,
            severity=severity,
            category=category,
            source=source,
            phase=phase,
            error_type=error_type,
            message=message,
            context_hash=context_hash,
            runtime_state=runtime_state,
            evidence=evidence or [],
        )
        # Fixation immédiate du hash cryptographique du payload pour sceller l'incident
        record.payload_hash = record.compute_payload_hash()

        if self._sink_callback:
            try:
                self._sink_callback(record)
            except Exception:
                # Le collecteur ne doit jamais faire crasher le runtime observer s'il y a un souci de sink
                pass

        return record

    def capture_event(
        self,
        event_type: str,
        payload: Dict[str, Any],
        source: str = "kernel.bus",
        phase: str = "RUNNING",
        runtime_state: str = "READY",
        severity: IncidentSeverity = IncidentSeverity.INFO,
        category: IncidentCategory = IncidentCategory.FSM_TRANSITION,
        context_hash: str = "",
    ) -> IncidentRecord:
        """
        Capture un événement brut (ex: publication du bus du noyau) pour analyse de gouvernance.
        """
        incident_id = str(uuid.uuid4())
        timestamp = datetime.now(timezone.utc).isoformat()
        message = payload.get("message", json.dumps(payload, sort_keys=True))

        record = IncidentRecord(
            incident_id=incident_id,
            timestamp=timestamp,
            severity=severity,
            category=category,
            source=source,
            phase=phase,
            error_type=event_type,
            message=message,
            context_hash=context_hash,
            runtime_state=runtime_state,
            evidence=[payload],
        )
        record.payload_hash = record.compute_payload_hash()

        if self._sink_callback:
            try:
                self._sink_callback(record)
            except Exception:
                pass

        return record
