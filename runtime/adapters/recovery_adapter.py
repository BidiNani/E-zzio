from runtime.contracts.recovery_interface import RecoveryInterface


class RecoveryAdapter(RecoveryInterface):
    def recover(self):
        raise NotImplementedError("Runtime implementation required")
