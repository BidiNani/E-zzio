class CapabilityRevocationRegistry:
    """
    Registry for blacklisted or revoked capability tokens.
    Once revoked, a token can never return to active status.
    """
    def __init__(self):
        self._revoked = set()

    def revoke(self, token_id: str):
        self._revoked.add(token_id)

    def is_revoked(self, token_id: str) -> bool:
        return token_id in self._revoked
