import os
from pathlib import Path
from typing import Optional
from dotenv import load_dotenv
from contracts.config_port import IConfigProvider


class DotEnvConfigProvider(IConfigProvider):
    """
    Implémentation physique du port de configuration.
    Isole l'utilisation de python-dotenv et la lecture du système de fichiers.
    """

    def __init__(self, env_path: Optional[str] = None):
        self._loaded = False
        if env_path:
            self._env_path = Path(env_path)
        else:
            # Fallback automatique vers le chemin standard du projet E-ZZIO
            root_dir = Path(__file__).resolve().parent.parent.parent.parent
            self._env_path = root_dir / "secrets" / ".env"

    def _ensure_loaded(self):
        if not self._loaded:
            if self._env_path.exists():
                load_dotenv(dotenv_path=str(self._env_path), override=True)
            else:
                # Fallback ultime sur l'environnement système si le fichier n'existe pas
                load_dotenv(override=True)
            self._loaded = True

    def get(self, key: str, default: Optional[str] = None) -> Optional[str]:
        self._ensure_loaded()
        return os.environ.get(key, default)

    def require(self, key: str) -> str:
        self._ensure_loaded()
        val = os.environ.get(key)
        if val is None or str(val).strip() == "":
            raise RuntimeError(f"[E-ZZIO FATAL] Configuration requise manquante : {key}")
        return str(val)
