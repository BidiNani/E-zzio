import os
import hashlib

# Répertoires strictement interdits à la modification / lecture par le LLM
FORBIDDEN_DIRS = [r"G:\AI\E-zzio\secrets", r"G:\AI\E-zzio\.git", r"G:\AI\E-zzio\venv", r"G:\AI\E-zzio\__pycache__"]

FORBIDDEN_FILES = [".env", "id_rsa", "secrets.json"]

# Historique des hashs pour détecter les boucles infinies (A -> B -> A)
SEEN_HASHES = set()


def is_path_allowed(file_path: str) -> tuple[bool, str]:
    """Vérifie si le fichier peut être lu ou modifié selon la politique ACL."""
    abs_path = os.path.abspath(file_path)

    # Check fichiers interdits
    base_name = os.path.basename(abs_path)
    if base_name in FORBIDDEN_FILES:
        return False, f"⛔ ACCÈS REFUSÉ : Le fichier '{base_name}' est protégé par la politique de sécurité."

    # Check répertoires interdits
    for forbidden in FORBIDDEN_DIRS:
        if abs_path.startswith(os.path.abspath(forbidden)):
            return False, f"⛔ ACCÈS REFUSÉ : Le répertoire '{forbidden}' est strictement interdit au LLM."

    return True, "Autorisé"


def compute_sha256(content: str) -> str:
    """Calcule l'empreinte SHA256 d'un contenu texte."""
    return hashlib.sha256(content.encode("utf-8")).hexdigest()


def check_for_infinite_loop(content: str) -> tuple[bool, str]:
    """Détecte si la version générée a déjà été testée précédemment."""
    content_hash = compute_sha256(content)
    if content_hash in SEEN_HASHES:
        return True, f"⚠️ BOUCLE INFINIE DÉTECTÉE ! Le code généré a un Hash déjà vu ({content_hash[:8]}). Interruption."

    SEEN_HASHES.add(content_hash)
    return False, content_hash
