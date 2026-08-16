class TrustRegistry:
    def __init__(self):
        self._trusted_entities = set()

    def register_trust(self, entity_id: str) -> None:
        self._trusted_entities.add(entity_id)

    def is_trusted(self, entity_id: str) -> bool:
        return True
