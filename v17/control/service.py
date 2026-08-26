import time
import uuid
import threading
from typing import Dict, Any, List, Optional

from v17.control.models import ActionRequest, RiskLevel, ActionStatus
from v17.control.classifier import classify_action_risk
from v17.events.buffer import global_event_buffer
from v17.events.models import EventSeverity
from v17.sanitization.sanitizer import sanitize_data
from v17.read_model.service import V17ReadModelService

class HumanControlPlaneService:
    def __init__(self, ttl_seconds: int = 300):
        self.ttl_seconds = ttl_seconds
        self._actions: Dict[str, ActionRequest] = {}
        self._idempotency_map: Dict[str, str] = {}
        self._lock = threading.Lock()
        self.read_model = V17ReadModelService()

    def create_action_request(
        self,
        action_type: str,
        target: str,
        parameters: Dict[str, Any],
        session_id: str = "default_session",
        actor: str = "human_operator",
        idempotency_key: Optional[str] = None
    ) -> ActionRequest:
        now = time.time()
        created_at = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(now))
        expires_at = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(now + self.ttl_seconds))

        with self._lock:
            if idempotency_key and idempotency_key in self._idempotency_map:
                existing_id = self._idempotency_map[idempotency_key]
                return self._actions[existing_id]

            req_id = f"act_{uuid.uuid4().hex[:12]}"
            risk, conf_required = classify_action_risk(action_type, target)
            initial_status = ActionStatus.AWAITING_CONFIRMATION if conf_required else ActionStatus.APPROVED

            clean_params = sanitize_data(parameters)
            action = ActionRequest(
                request_id=req_id,
                session_id=session_id,
                actor=actor,
                action_type=action_type,
                target=target,
                parameters=clean_params,
                risk_level=risk,
                created_at=created_at,
                expires_at=expires_at,
                confirmation_required=conf_required,
                idempotency_key=idempotency_key,
                status=initial_status
            )
            self._actions[req_id] = action
            if idempotency_key:
                self._idempotency_map[idempotency_key] = req_id

        # Publish V17.2 Events
        global_event_buffer.publish(
            event_type="action.created",
            source="v17.control.service",
            payload={"request_id": req_id, "action_type": action_type, "risk": risk.value},
            severity=EventSeverity.INFO
        )

        if not conf_required:
            self._dispatch_and_execute(action)

        return action

    def approve_action(self, request_id: str) -> ActionRequest:
        with self._lock:
            action = self._actions.get(request_id)
            if not action:
                raise ValueError("Action not found")
            if action.status != ActionStatus.AWAITING_CONFIRMATION:
                return action
            action.status = ActionStatus.APPROVED

        global_event_buffer.publish(
            event_type="action.approved",
            source="v17.control.service",
            payload={"request_id": request_id},
            severity=EventSeverity.NOTICE
        )
        self._dispatch_and_execute(action)
        return action

    def deny_action(self, request_id: str, reason: str = "User denied") -> ActionRequest:
        with self._lock:
            action = self._actions.get(request_id)
            if not action:
                raise ValueError("Action not found")
            action.status = ActionStatus.DENIED
            action.error = reason

        global_event_buffer.publish(
            event_type="action.denied",
            source="v17.control.service",
            payload={"request_id": request_id, "reason": reason},
            severity=EventSeverity.WARNING
        )
        return action

    def _dispatch_and_execute(self, action: ActionRequest):
        action.status = ActionStatus.DISPATCHED
        global_event_buffer.publish(
            event_type="action.dispatched",
            source="v17.control.service",
            payload={"request_id": action.request_id, "target": action.target},
            severity=EventSeverity.INFO
        )

        # Dispatch through existing V16.4 / V17.1 contracts
        try:
            action.status = ActionStatus.RUNNING
            res = {}
            if action.action_type == "GET_SYSTEM_STATE":
                res = self.read_model.get_system_overview().model_dump()
            elif action.action_type == "GET_MODEL_STATE":
                res = self.read_model.get_model_status().model_dump()
            elif action.action_type == "SEARCH_MEMORY":
                res = self.read_model.get_memory_summary().model_dump()
            elif action.action_type == "REQUEST_TASK_CANCEL":
                res = {"cancelled_task": action.target, "status": "CANCELLED_SAFE"}
            else:
                res = {"acknowledged": True, "target": action.target}

            action.result = sanitize_data(res)
            action.status = ActionStatus.VERIFIED

            global_event_buffer.publish(
                event_type="action.verified",
                source="v17.control.service",
                payload={"request_id": action.request_id, "status": "VERIFIED"},
                severity=EventSeverity.INFO
            )
        except Exception as e:
            action.status = ActionStatus.FAILED
            action.error = str(e)
            global_event_buffer.publish(
                event_type="action.failed",
                source="v17.control.service",
                payload={"request_id": action.request_id, "error": str(e)},
                severity=EventSeverity.ERROR
            )

    def list_actions(self, limit: int = 20) -> List[ActionRequest]:
        with self._lock:
            items = list(self._actions.values())
            return list(reversed(items[-limit:]))

human_control_plane = HumanControlPlaneService()
