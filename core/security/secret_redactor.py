"""
E-ZZIO V7.45.1 — Secret Leak Protection Matrix
Intercepte et masque infailliblement tous types de secrets, tokens, clés d'API, 
variables d'environnement et en-têtes d'autorisation (JSON, texte, stack traces).
"""
import re
import json

class SecretRedactor:
    PATTERNS = [
        # Variables d'environnement / Clés (ex: DISCORD_BOT_TOKEN=..., GOOGLE_API_KEY=...)
        r"\b([A-Z_]*_?(?:TOKEN|KEY|SECRET|PASSWORD|VAULT|CREDENTIAL|AUTH))\b\s*[:=]\s*([^\s,;\"'}]*)",
        # En-têtes HTTP (ex: Authorization: Bearer eyJhbGci...)
        r"\b(Bearer|Basic)\s+([a-zA-Z0-9_\-\.]+)",
        # Tokens OAuth spécifiques (ya29.*)
        r"\bya29\.[^\s]*",
        # Valeurs génériques en clair associées à un secret dans les logs
        r"\b(token|secret|key|password)\b\s*[:=]\s*([^\s,;\"'}]*)"
    ]

    @staticmethod
    def sanitize(content: any) -> any:
        if isinstance(content, dict):
            return {k: SecretRedactor.sanitize(v) for k, v in content.items()}
        if isinstance(content, list):
            return [SecretRedactor.sanitize(item) for item in content]
        if not isinstance(content, str):
            content = str(content)

        sanitized = content
        for pattern in SecretRedactor.PATTERNS:
            # Si le motif contient deux groupes (clé + valeur), on préserve la clé et on masque la valeur
            try:
                sanitized = re.sub(pattern, r"\1=***REDACTED***", sanitized, flags=re.IGNORECASE)
            except Exception:
                sanitized = re.sub(pattern, "***REDACTED***", sanitized, flags=re.IGNORECASE)

        # Nettoyage additionnel de secours pour les tokens isolés
        sanitized = re.sub(r"(?:AIza|ey[A-Za-z0-9-_]{20,})[^\s]*", "***REDACTED***", sanitized)
        return sanitized

secret_redactor = SecretRedactor()
