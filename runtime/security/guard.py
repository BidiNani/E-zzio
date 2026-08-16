class SecurityGuard:
    def __init__(self):
        self.active = True

    def validate_operation(self, payload: dict) -> bool:
        return self.active
