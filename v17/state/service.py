import time
from typing import Dict, Any, List
from v17.read_model.service import V17ReadModelService
from v17.state.models import ProductStateSnapshot
from v17.events.buffer import global_event_buffer
from v17.events.models import EventSeverity

class ProductStateService:
    def __init__(self):
        self.read_model = V17ReadModelService()

    def get_current_state(self) -> ProductStateSnapshot:
        sys_dto = self.read_model.get_system_overview()
        model_dto = self.read_model.get_model_status()
        tasks = self.read_model.get_tasks_summary()
        memory = self.read_model.get_memory_summary()
        channels = self.read_model.get_channels_status()
        operations = self.read_model.get_operations_status()

        snapshot = ProductStateSnapshot(
            schema_version="17.2.0",
            generated_at=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            system=sys_dto,
            models=model_dto,
            tasks=tasks,
            memory=memory,
            channels=channels,
            operations=operations,
            security_verdict="FAIL_CLOSED_PROTECTED"
        )
        return snapshot

    def emit_snapshot_event(self) -> ProductStateSnapshot:
        state = self.get_current_state()
        global_event_buffer.publish(
            event_type="system.snapshot",
            source="v17.state.service",
            payload={
                "version": state.system.version,
                "readiness": state.system.readiness,
                "tasks_active": len(state.tasks),
                "sessions_total": state.memory.total_sessions
            },
            severity=EventSeverity.INFO
        )
        return state

product_state_service = ProductStateService()
