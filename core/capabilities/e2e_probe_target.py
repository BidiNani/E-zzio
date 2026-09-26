"""Module cible de validation du probe Coding E2E pour E-ZZIO."""
import hashlib


def calculate_probe_hash(val: str) -> str:
    """Calcule l'empreinte tronquée à 12 caractères."""
    return hashlib.sha256(val.encode("utf-8")).hexdigest()[:12]
