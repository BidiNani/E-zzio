from runtime.contracts.identity_interface import IdentityInterface


class IdentityAdapter(IdentityInterface):
    def get_identity(self):
        raise NotImplementedError("Runtime implementation required")
