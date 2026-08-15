"""
E-ZZIO V7.29 — Global Identity Fingerprint
Agrège tous les fichiers de configuration, de constitution et de lore 
en une empreinte cryptographique unique et vérifiable.
"""
import hashlib
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent.parent
CONFIG_DIR = ROOT_DIR / "config"

class GlobalIdentityFingerprint:
    @staticmethod
    def compute_identity_root() -> str:
        """Calcule un hash SHA-256 combiné de tous les fichiers d'identité et de configuration."""
        if not CONFIG_DIR.exists():
            return "0" * 64

        hasher = hashlib.sha256()
        # Récupération de tous les fichiers de configuration de manière strictement ordonnée
        config_files = sorted(list(CONFIG_DIR.glob("**/*.*")))

        for file_path in config_files:
            if file_path.is_file():
                # On intègre le chemin relatif et le contenu brut de chaque fichier
                relative_path = file_path.relative_to(CONFIG_DIR)
                hasher.update(str(relative_path).encode("utf-8"))
                hasher.update(file_path.read_bytes())

        return hasher.hexdigest()

global_fingerprint = GlobalIdentityFingerprint()
