import re
from typing import List, Tuple

class SecurityViolationError(Exception):
    """Exception levée en cas de détection d'une injection de prompt ou d'un contournement."""
    pass

class PromptGuard:
    """Garde-fou heuristique contre les attaques par injection de prompt et l'évasion de contexte."""

    INJECTION_PATTERNS: List[re.Pattern] = [
        re.compile(r"ignore\s+(all\s+)?(previous|prior|above)\s+instructions?", re.IGNORECASE),
        re.compile(r"you\s+are\s+now\s+(unrestricted|dan|jailbroken)", re.IGNORECASE),
        re.compile(r"system\s*:\s*override", re.IGNORECASE),
        re.compile(r"(reveal|print|show)\s+(your\s+)?(system\s+prompt|initial\s+instructions?)", re.IGNORECASE),
        re.compile(r"bypass\s+(safety|security|policy|restrictions?)", re.IGNORECASE),
        re.compile(r"mode\s+développeur\s+activé", re.IGNORECASE),
        re.compile(r"ignore\s+tes\s+directives", re.IGNORECASE)
    ]

    MAX_INPUT_LENGTH: int = 4000

    def validate(self, prompt: str) -> Tuple[bool, str]:
        """
        Valide la conformité et la sécurité d'un prompt utilisateur.
        Retourne (is_safe: bool, reason: str).
        """
        if not prompt or not prompt.strip():
            return False, "Prompt vide ou non conforme."

        if len(prompt) > self.MAX_INPUT_LENGTH:
            return False, f"Dépassement de la longueur maximale autorisée ({len(prompt)}/{self.MAX_INPUT_LENGTH} caractères)."

        for pattern in self.INJECTION_PATTERNS:
            if pattern.search(prompt):
                return False, f"Violation de sécurité : tentative d'injection détectée ({pattern.pattern})."

        return True, "OK"

    def sanitize(self, prompt: str) -> str:
        """Valide et assainit le texte avant traitement."""
        is_safe, reason = self.validate(prompt)
        if not is_safe:
            raise SecurityViolationError(reason)
        return prompt.strip()
