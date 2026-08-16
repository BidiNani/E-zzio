from runtime.contracts.telemetry_interface import TelemetryInterface

class TelemetryAdapter(TelemetryInterface):

    def emit(self,event):
        raise NotImplementedError("Runtime implementation required")
