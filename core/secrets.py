import os
from pathlib import Path
from dotenv import load_dotenv


def get_secrets_path():
    """Retourne le chemin vers secrets/.env"""
    ROOT_DIR = Path(__file__).resolve().parent.parent
    return ROOT_DIR / "secrets" / ".env"


def load_secrets(override: bool = True) -> bool:
    """Charge les secrets depuis secrets/.env via secrets_loader canonique."""
    from core.config import secrets_loader
    loaded = secrets_loader.load(override=override)
    return bool(loaded)


def get_api_key(name: str) -> str:
    """Récupère une clé API par nom"""
    load_secrets()
    return os.getenv(name, "")
