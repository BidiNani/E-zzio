"""
E-ZZIO — Resolution unique de la cle d'API (X-API-Key).

Probleme corrige : `routers/stats.py`, `routers/system.py` et `routers/webhook.py`
utilisaient chacun `os.getenv("EZZIO_API_KEY", "ezzio_secret_key_local_dev")`.
Cette cle par defaut etait **publique dans le code source** : toute personne
ayant lu le depot pouvait s'authentifier sur `/api/v1/stats/*`,
`/api/v1/system/*` (nettoyage destructif) et `/api/v1/webhook/*`.

Ce module etablit une source de verite unique et applique la doctrine du projet
(identique a `core/identity/canonical_identity.py`) : **fail-closed**.
Si aucune cle n'est configuree, l'authentification n'est PAS desactivee
silencieusement : `is_key_valid()` renvoie `False` et l'appelant doit lever une
erreur explicite.

Usage :
    from core.security.api_key import is_key_valid
    if not is_key_valid(provided):
        raise HTTPException(status_code=403, detail="Cle API invalide")
"""

from __future__ import annotations

import hmac
import logging
import os
import warnings

logger = logging.getLogger("ezzio.security.api_key")

ENV_KEY = "EZZIO_API_KEY"

#: anciennes cles par defaut, conservees uniquement pour detecter et REFUSER
#: les configurations legacy qui les utilisent encore.
LEGACY_INSECURE_DEFAULTS = frozenset(
    {
        "ezzio_secret_key_local_dev",
        "ezzio_super_secret_session_key_2026",
    }
)


def resolve_expected_key() -> str:
    """Retourne la cle attendue, ou "" si aucune n'est configuree.

    Ne retourne JAMAIS de valeur par defaut : une cle absente doit etre
    traitee comme une configuration absente, pas comme une cle connue.
    """
    return (os.getenv(ENV_KEY) or "").strip()


def is_key_configured() -> bool:
    """Vrai seulement si une cle non triviale est configuree."""
    return bool(resolve_expected_key())


def is_using_insecure_default() -> bool:
    """Vrai si la cle configuree est une des anciennes valeurs par defaut."""
    return resolve_expected_key() in LEGACY_INSECURE_DEFAULTS


def is_key_valid(provided: str | None) -> bool:
    """Compare en temps constant. Fail-closed si aucune cle n'est configuree.

    `hmac.compare_digest` evite les timing attacks sur la comparaison de cles
    (le middleware web_server comparait avec `!=`).

    Les valeurs None / vides sont traitees comme des cles invalides.
    Les anciennes valeurs par defaut, publiees dans l'ancien code source, sont
    explicitement refusees tant qu'elles restent configurees.
    """
    expected = resolve_expected_key()
    if not expected:
        # Fail-closed : pas de cle configuree => personne ne peut s'authentifier.
        return False
    if expected in LEGACY_INSECURE_DEFAULTS:
        # Cle publique connue => refusee, meme si elle correspond a l'entree.
        return False
    if provided is None:
        return False
    return hmac.compare_digest(provided.encode("utf-8"), expected.encode("utf-8"))


def warn_if_auth_unenforced(context: str = "") -> None:
    """Emet un avertissement explicite si l'auth ne peut pas etre appliquee.

    A appeler au demarrage. Le silence est ici un defaut de securite : un
    systeme dit "souverain" qui laisse passer toutes les requetes sans le
    dire est pire qu'un systeme qui refuse de demarrer.
    """
    suffix = f" ({context})" if context else ""
    if is_using_insecure_default():
        msg = (
            f"[SECURITE] {ENV_KEY} est configuree sur une valeur par defaut "
            f"PUBLIQUE, qui sera refusee. Changez-la{suffix}."
        )
        logger.error(msg)
        warnings.warn(msg, RuntimeWarning, stacklevel=2)
        return
    if not is_key_configured():
        msg = (
            f"[SECURITE] {ENV_KEY} n'est pas definie{suffix}. Les endpoints "
            f"proteges qui utilisent core.security.api_key seront refuses "
            f"(fail-closed). Definissez {ENV_KEY} pour les activer."
        )
        logger.warning(msg)
        warnings.warn(msg, RuntimeWarning, stacklevel=2)
