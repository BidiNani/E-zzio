from __future__ import annotations
import logging
from runtime.kernel.context import RuntimeContext
from runtime.events.types import EventTypes
from runtime.events.bus import Event
from runtime.recovery.actions import RecoveryActions
from runtime.incidents.registry import IncidentRegistry

class RecoveryController:
    """
    Système immunitaire du Runtime. 
    Écoute le bus d'événements et déclenche des actions correctives automatiques.
    """

    def __init__(self, context: RuntimeContext, incident_registry: IncidentRegistry):
        self.context = context
        self.incidents = incident_registry
        self._register_listeners()

    def _register_listeners(self):
        # Abonnement aux signaux critiques du bus
        self.context.bus.subscribe(EventTypes.WORKER_TIMEOUT, self.handle_worker_timeout)
        self.context.bus.subscribe(EventTypes.WORKER_KILLED, self.handle_worker_crash)

    def handle_worker_timeout(self, event: Event):
        actor = event.actor
        exec_id = event.correlation_id
        logging.warning(f"[RECOVERY] Intervention suite au Timeout de l'acteur '{actor}' (Exec: {exec_id})")
        
        # 1. Enregistrement incident
        self.incidents.report("ActiveRecoveryTriggered", actor, "MEDIUM", {"action": "WorkspacePurge", "exec_id": exec_id})
        
        # 2. Remédiation : Nettoyage de l'espace de travail
        RecoveryActions.purge_execution_workspace(exec_id)

    def handle_worker_crash(self, event: Event):
        actor = event.actor
        exec_id = event.correlation_id
        logging.error(f"[RECOVERY] Alerte critique : Crash de l'acteur '{actor}' (Exec: {exec_id})")

        # 1. Enregistrement incident
        self.incidents.report("ActiveRemediation", actor, "HIGH", {"action": "QuarantineAndPurge", "exec_id": exec_id})

        # 2. Remédiation active : Quarantaine immédiate de l'agent et purge de son espace
        RecoveryActions.force_quarantine(self.context, actor, reason=f"Worker crashed during execution {exec_id}")
        RecoveryActions.purge_execution_workspace(exec_id)

        # 3. Émission d'un événement de résolution sur le bus
        self.context.bus.publish(Event(
            type="AgentQuarantined",
            actor="RecoveryController",
            source="recovery.controller",
            payload={"target_actor": actor, "reason": "Automatic recovery remediation"},
            correlation_id=exec_id
        ))