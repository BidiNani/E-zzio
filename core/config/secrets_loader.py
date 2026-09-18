"""E-ZZIO — source de vérité unique des secrets (racine absolue, override, typage)."""
from __future__ import annotations

import logging
import os
from pathlib import Path

logger = logging.getLogger("ezzio.secrets")

ROOT_DIR = Path(__file__).resolve().parent.parent.parent
ENV_PATH = ROOT_DIR / "secrets" / ".env"


def _clean(value: object) -> str:
    return str(value or "").strip().strip().strip("\"'").strip()


DISCORD_OWNER_ID: int | None = None


def _refresh_owner(env: dict) -> None:
    global DISCORD_OWNER_ID
    raw = _clean(env.get("DISCORD_OWNER_ID", ""))
    try:
        DISCORD_OWNER_ID = int(raw) if raw.isdigit() else None
    except (TypeError, ValueError):
        DISCORD_OWNER_ID = None
    if DISCORD_OWNER_ID is not None:
        os.environ["DISCORD_OWNER_ID"] = str(DISCORD_OWNER_ID)


def is_owner_id(user_id: object, owner_id: object = None) -> bool:
    """Comparaison stricte d'entiers (espaces/guillemets tolérés en entrée)."""
    oid = DISCORD_OWNER_ID if owner_id is None else owner_id
    try:
        return oid is not None and int(str(user_id).strip()) == int(str(oid).strip())
    except (TypeError, ValueError):
        return False


def load(override: bool = True) -> dict[str, str]:
    """Charge secrets/.env (chemin absolu), écrase le résiduel système."""
    loaded: dict[str, str] = {}
    if not ENV_PATH.exists():
        logger.error("[SECRETS] Fichier absent : %s", ENV_PATH)
        return loaded
    try:
        from dotenv import load_dotenv
        load_dotenv(dotenv_path=str(ENV_PATH), override=override)
    except Exception as exc:
        logger.error("[SECRETS] load_dotenv impossible : %s", exc)
    try:
        raw_text = ENV_PATH.read_text(encoding="utf-8-sig", errors="ignore")
        for line in raw_text.splitlines():
            s = line.strip()
            if not s or s.startswith("#") or "=" not in s:
                continue
            k, _, v = line.partition("=")
            key = k.strip().lstrip("\ufeff")
            if key:
                loaded[key] = _clean(v)
    except Exception as exc:
        logger.error("[SECRETS] Lecture secrets/.env impossible : %s", exc)

    # Synchronisation canonique des alias
    disc_val = loaded.get("DISCORD_BOT_TOKEN") or loaded.get("DISCORD_TOKEN") or os.environ.get("DISCORD_BOT_TOKEN") or os.environ.get("DISCORD_TOKEN", "")
    disc_val = _clean(disc_val)
    if disc_val:
        loaded["DISCORD_BOT_TOKEN"] = disc_val
        loaded["DISCORD_TOKEN"] = disc_val

    gem_val = loaded.get("GEMINI_API_KEY") or loaded.get("GEMINI_API_KEY_1") or os.environ.get("GEMINI_API_KEY") or os.environ.get("GEMINI_API_KEY_1", "")
    gem_val = _clean(gem_val)
    if gem_val:
        loaded["GEMINI_API_KEY"] = gem_val

    merged = dict(os.environ)
    if override:
        for k, v in loaded.items():
            if v:
                os.environ[k] = v
                merged[k] = v
    else:
        for k, v in loaded.items():
            merged.setdefault(k, v)
            if k not in os.environ:
                os.environ[k] = v
    _refresh_owner(merged)
    return loaded


def discord_token(env: dict[str, str] | None = None) -> str:
    src = dict(os.environ) if env is None else env
    for key in ("DISCORD_TOKEN", "DISCORD_BOT_TOKEN"):
        val = _clean(src.get(key, ""))
        if val and val.count(".") >= 2:
            return val
    return ""


def discord_owner_id(env: dict[str, str] | None = None) -> int | None:
    src = dict(os.environ) if env is None else env
    raw = _clean(src.get("DISCORD_OWNER_ID", ""))
    if not raw:
        logger.warning("[SECRETS] DISCORD_OWNER_ID absent — DM restreints.")
        return None
    try:
        return int(raw)
    except ValueError:
        logger.error("[SECRETS] DISCORD_OWNER_ID non convertible : %r", raw[:12])
        return None


def groq_key(env: dict[str, str] | None = None) -> str:
    src = dict(os.environ) if env is None else env
    for key in ("DISCORD_GROQ_API_KEY", "GROQ_API_KEY", "GROQ_API_KEY_2"):
        val = _clean(src.get(key, ""))
        if val:
            return val
    return ""


def gemini_keys(env: dict[str, str] | None = None) -> list[str]:
    src = dict(os.environ) if env is None else env
    out = []
    for k in sorted(src.keys()):
        if k.startswith("GEMINI_API_KEY"):
            val = _clean(src[k])
            if val:
                out.append(val)
    return out


def log_secrets_diagnostics(env: dict[str, str] | None = None) -> dict[str, str]:
    """Bilan masqué : jamais de clé en clair."""
    src = dict(os.environ) if env is None else env
    tok = discord_token(src)
    owner = discord_owner_id(src)
    gk = groq_key(src)
    gmk = gemini_keys(src)
    report = {
        "DISCORD_TOKEN": f"[PRESENT] (longueur: {len(tok)}, separateurs: 2)"
        if tok else "[INVALIDE / ABSENT]",
        "DISCORD_OWNER_ID": f"[PRESENT] (ID: {str(owner)[:5]}...XXXX)"
        if owner else "[ABSENT]",
        "GROQ_API_KEY": "[PRESENT]" if gk else "[ABSENT]",
        "GEMINI_KEYS": f"{len(gmk)} cles detectees",
    }
    for k, v in report.items():
        logger.info("[SECRETS] %s : %s", k, v)
    return report
