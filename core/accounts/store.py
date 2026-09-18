"""
core/accounts/store.py — Stockage chiffré des tokens OAuth.

Utilise Fernet (AES-128 CBC + HMAC) avec une clé dérivée de
EZZIO_GATEWAY_SECRET (présent dans secrets/.env).

Format disque : JSON chiffré dans runtime/accounts/accounts.enc
"""
from __future__ import annotations

import base64
import hashlib
import json
import logging
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

try:
    from cryptography.fernet import Fernet
except ImportError:
    Fernet = None  # type: ignore

logger = logging.getLogger("AccountsStore")

_ROOT = Path(__file__).resolve().parents[2]
_STORE_DIR = _ROOT / "runtime" / "accounts"
_STORE_FILE = _STORE_DIR / "accounts.enc"


def _load_master_secret() -> Optional[str]:
    """Lit EZZIO_GATEWAY_SECRET depuis secrets/.env ou l'environnement."""
    env_path = _ROOT / "secrets" / ".env"
    if env_path.exists():
        try:
            for line in env_path.read_text(encoding="utf-8").splitlines():
                line = line.strip()
                if line.startswith("#") or "=" not in line:
                    continue
                key, _, val = line.partition("=")
                if key.strip() == "EZZIO_GATEWAY_SECRET":
                    return val.strip().strip("\"'")
        except Exception as exc:
            logger.warning("[STORE] Lecture secrets/.env échouée : %s", exc)
    return os.environ.get("EZZIO_GATEWAY_SECRET")


def _derive_fernet() -> "Fernet":
    """Dérive une clé Fernet 32-bytes URL-safe à partir du secret maître."""
    if Fernet is None:
        raise RuntimeError(
            "cryptography n'est pas installé. "
            "pip install cryptography"
        )
    secret = _load_master_secret()
    if not secret:
        raise RuntimeError(
            "EZZIO_GATEWAY_SECRET introuvable dans secrets/.env ou l'environnement."
        )
    digest = hashlib.sha256(secret.encode("utf-8")).digest()
    key = base64.urlsafe_b64encode(digest)
    return Fernet(key)


def _ensure_dir() -> None:
    _STORE_DIR.mkdir(parents=True, exist_ok=True)


def _read_all() -> Dict[str, Any]:
    """Lit l'intégralité du store. Retourne {} si vide."""
    if not _STORE_FILE.exists():
        return {}
    try:
        cipher = _derive_fernet()
        raw = _STORE_FILE.read_bytes()
        decrypted = cipher.decrypt(raw)
        data = json.loads(decrypted.decode("utf-8"))
        if isinstance(data, dict):
            return data
        return {}
    except Exception as exc:
        logger.error("[STORE] Décryptage échoué : %s", exc)
        return {}


def _write_all(data: Dict[str, Any]) -> None:
    """Écrit le store complet, chiffré."""
    _ensure_dir()
    cipher = _derive_fernet()
    payload = json.dumps(data, ensure_ascii=False, indent=2).encode("utf-8")
    encrypted = cipher.encrypt(payload)
    _STORE_FILE.write_bytes(encrypted)


# ---------------------------------------------------------------------------
# API publique
# ---------------------------------------------------------------------------

def list_accounts() -> List[Dict[str, Any]]:
    """Retourne la liste des comptes connectés (sans exposer les tokens)."""
    data = _read_all()
    out: List[Dict[str, Any]] = []
    for provider, entry in data.items():
        if not isinstance(entry, dict):
            continue
        out.append({
            "provider": provider,
            "account_id": entry.get("account_id"),
            "display_name": entry.get("display_name"),
            "email": entry.get("email"),
            "scopes": entry.get("scopes", []),
            "connected_at": entry.get("connected_at"),
            "expires_at": entry.get("expires_at"),
        })
    return out


def get_account(provider: str) -> Optional[Dict[str, Any]]:
    """Retourne l'entrée brute (avec tokens) pour un provider."""
    data = _read_all()
    entry = data.get(provider)
    return entry if isinstance(entry, dict) else None


def save_account(
    provider: str,
    *,
    access_token: str,
    refresh_token: Optional[str] = None,
    expires_in: Optional[int] = None,
    scopes: Optional[List[str]] = None,
    account_id: Optional[str] = None,
    display_name: Optional[str] = None,
    email: Optional[str] = None,
    extra: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Enregistre (ou met à jour) un compte connecté."""
    data = _read_all()
    now = datetime.now(timezone.utc).isoformat()
    expires_at = None
    if expires_in:
        from datetime import timedelta
        expires_at = (datetime.now(timezone.utc) + timedelta(seconds=int(expires_in))).isoformat()

    entry: Dict[str, Any] = {
        "provider": provider,
        "access_token": access_token,
        "refresh_token": refresh_token,
        "expires_at": expires_at,
        "scopes": scopes or [],
        "account_id": account_id,
        "display_name": display_name,
        "email": email,
        "connected_at": now,
    }
    if extra:
        entry.update(extra)

    data[provider] = entry
    _write_all(data)
    logger.info("[STORE] Compte enregistré : %s", provider)
    return {k: v for k, v in entry.items() if k not in ("access_token", "refresh_token")}


def delete_account(provider: str) -> bool:
    """Supprime un compte. Retourne True si quelque chose a été supprimé."""
    data = _read_all()
    if provider not in data:
        return False
    del data[provider]
    _write_all(data)
    logger.info("[STORE] Compte supprimé : %s", provider)
    return True


def has_account(provider: str) -> bool:
    return get_account(provider) is not None