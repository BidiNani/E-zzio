from runtime.core.events import EventBus

class TelemetryManager:
    """Observe les performances et les métriques sans bloquer le runtime."""
    def __init__(self):
        EventBus.subscribe("ExecutionFinished", self._on_execution_finished)
        EventBus.subscribe("PolicyGranted", self._on_policy_granted)

    def _on_execution_finished(self, payload):
        # payload = {"request_id": id, "duration": float, "success": bool}
        # Ici on pourrait envoyer vers Prometheus/OpenTelemetry
        pass

    def _on_policy_granted(self, token):
        pass