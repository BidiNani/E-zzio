"""
E-ZZIO V7.23.0
Secure Provider Secrets Loader
Responsabilité:
- Chargement contrôlé des secrets cloud
- Aucun stockage permanent
- Aucun affichage de valeur sensible
"""

import os
from pathlib import Path
from dotenv import load_dotenv

ROOT_DIR = Path("G:/AI/E-zzio").resolve()
ENV_PATH = ROOT_DIR / "secrets" / ".env"


def _load_environment():
    """
    Charge uniquement l'environnement provider.
    """
    if ENV_PATH.exists():
        load_dotenv(dotenv_path=ENV_PATH, override=False)


_load_environment()


def _collect_key_pool(prefix: str, maximum: int = 5):
    """
    Collecte un pool de clés:
    PREFIX
    PREFIX_2
    PREFIX_3
    ...
    Retour:
        liste nettoyée sans doublons
    """
    keys = []
    for index in range(1, maximum + 1):
        suffix = "" if index == 1 else f"_{index}"
        value = os.getenv(f"{prefix}{suffix}")
        if value and value.strip():
            keys.append(value.strip())
    return list(dict.fromkeys(keys))


def get_gemini_keys():
    """
    Retourne le pool Gemini actif.
    """
    return _collect_key_pool("GEMINI_API_KEY")


def get_groq_keys():
    """
    Retourne le pool Groq actif.
    """
    return _collect_key_pool("GROQ_API_KEY")


def provider_secret_status():
    return {"gemini_keys": len(get_gemini_keys()), "groq_keys": len(get_groq_keys()), "env_loaded": ENV_PATH.exists()}


if __name__ == "__main__":
    status = provider_secret_status()
    print("[E-ZZIO V7.23.0] Provider Secret Status")
    print(f" Gemini keys available : {status['gemini_keys']}")
    print(f" Groq keys available   : {status['groq_keys']}")
    print(f" ENV detected          : {status['env_loaded']}")
