import os
from pathlib import Path
from dotenv import load_dotenv


def get_secrets_path():
    """Retourne le chemin vers secrets/.env"""
    ROOT_DIR = Path(__file__).resolve().parent.parent
    return ROOT_DIR / "secrets" / ".env"


def load_secrets():
    """Charge les secrets depuis secrets/.env"""
    secrets_path = get_secrets_path()

    if secrets_path.exists():
        load_dotenv(secrets_path, override=True)
        return True
    return False


def get_api_key(name: str) -> str:
    """Récupère une clé API par nom"""
    load_secrets()
    return os.getenv(name)
