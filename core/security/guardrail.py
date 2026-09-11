class SecurityViolationError(ValueError):
    """Exception de sécurité levée lors d'une tentative d'injection de prompt."""

    pass


class PromptGuard:
    """Garde-fou d'assainissement et de filtrage des messages malveillants."""

    def sanitize(self, message: str) -> str:
        if not message or not isinstance(message, str):
            return ""
        lower_msg = message.lower()

        forbidden_patterns = [
            "ignore all previous instructions",
            "dump tokens",
            "mode développeur activé",
            "ignore tes directives",
            "unrestricted dan",
            "bypass security",
            "system : override",
            "system: override",
        ]

        if any(pat in lower_msg for pat in forbidden_patterns):
            raise SecurityViolationError("Tentative d'injection de prompt ou jailbreak détectée et bloquée.")

        return message.strip()

    def validate(self, message: str) -> tuple:
        """Valide un message et retourne (is_valid, reason)."""
        try:
            self.sanitize(message)
            return True, ""
        except SecurityViolationError as e:
            return False, str(e)
