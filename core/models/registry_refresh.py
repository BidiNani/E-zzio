"""
E-ZZIO — core/models/registry_refresh.py
=========================================
Synchronisation automatique du registre Gemini depuis l'API Google.

INVARIANTS ABSOLUS :
  - ModelRouter non modifié
  - gemini_pool.py non modifié
  - Aucun modèle n'est jamais activé automatiquement
  - Aucun modèle n'est jamais supprimé physiquement
  - Fail-safe : tout échec API laisse registry.json inchangé
  - Atomicité déléguée à ModelRegistry.save() (tempfile + os.replace)
  - Aucun secret n'est écrit dans les logs ou audits

Utilise exclusivement les composants existants :
  core/models/discovery/gemini.py  → GeminiDiscovery
  core/models/lifecycle.py         → ModelLifecycleManager, ModelLifecycle
  core/models/registry.py          → ModelRegistry, ModelRecord
"""
from __future__ import annotations

import asyncio
import json
import logging
import os
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

logger = logging.getLogger("EzzioRegistryRefresh")

# ── Paths canoniques ────────────────────────────────────────────────────────
# registry_refresh.py lives at: <repo>/core/models/registry_refresh.py
# parents[0] = core/models/  parents[1] = core/  parents[2] = <repo root>
_REPO_ROOT    = Path(__file__).resolve().parents[2]
_REGISTRY_PATH = _REPO_ROOT / "data" / "models" / "registry.json"
_AUDIT_DIR     = _REPO_ROOT / "state" / "audit" / "discovery"



# ── Callback de transition minimal pour ModelLifecycleManager ────────────────
def _make_transition_callback(registry):
    """
    Produit un callback FAIL-CLOSED pour ModelLifecycleManager.ingest_discovery().

    Ce callback est déclenché UNIQUEMENT lorsqu'un modèle ACTIVE ou QUALIFIED
    disparaît de la découverte API. La seule transition légale dans ce cas,
    selon la state machine de fabric.transition(), est :
        ACTIVE    → QUARANTINED  (acteur: lifecycle_manager)
        QUALIFIED → n/a via lifecycle_manager — on laisse intact et on loggue.

    NB : on ne passe pas SUPERSEDED directement car seul `activate_qualified`
    peut déclencher QUALIFIED→SUPERSEDED. On passe QUARANTINED pour ACTIVE
    (seule transition légale depuis lifecycle_manager), et on ignore les
    QUALIFIED disparus avec un WARNING (aucune transition légale disponible
    depuis lifecycle_manager pour QUALIFIED→SUPERSEDED).
    """
    from datetime import datetime

    def callback(
        *,
        provider: str,
        model_id: str,
        new_state: str,
        actor: str,
        reason: str,
        operator: str = "system",
        new_tier: str | None = None,
    ) -> None:
        entry = registry.get(provider, model_id)
        if entry is None:
            logger.warning(
                "[REFRESH] Transition callback : modèle %s/%s introuvable dans le registre.",
                provider, model_id,
            )
            return

        old_state = getattr(entry, "lifecycle", "UNKNOWN")
        now_iso = datetime.now(UTC).isoformat()

        # Seule transition légale disponible depuis registry_refresh :
        # ACTIVE → QUARANTINED (acteur: lifecycle_manager)
        if old_state == "ACTIVE" and new_state == "QUARANTINED":
            entry.lifecycle = "QUARANTINED"
            entry.updated_at = now_iso
            entry.last_quarantine_at = now_iso
            entry.last_quarantine_reason = reason[:300]
            entry.last_quarantine_operator = operator
            logger.warning(
                "[REFRESH] Modèle %s/%s : ACTIVE → QUARANTINED "
                "(disparu de l'API Gemini, actor=%s).",
                provider, model_id, actor,
            )
        else:
            # Pour toute autre combinaison (ex: QUALIFIED disparu),
            # on loggue uniquement sans modifier l'état — pas de transition légale.
            logger.warning(
                "[REFRESH] Modèle %s/%s en état %s a disparu de l'API "
                "mais aucune transition légale disponible depuis registry_refresh "
                "(new_state=%s). État conservé.",
                provider, model_id, old_state, new_state,
            )

    return callback


# ── Fonction principale ──────────────────────────────────────────────────────
async def _run_refresh(*, api_key: str | None = None) -> dict[str, Any]:
    """
    Exécute le pipeline de synchronisation complet (async).

    Retourne un dict de résultats utilisable pour l'audit et le reporting.
    En cas d'erreur critique (API indisponible, parsing échoué…),
    lève une exception SANS avoir modifié registry.json.
    """
    from core.models.discovery.gemini import GeminiDiscovery
    from core.models.lifecycle import ModelLifecycleManager
    from core.models.registry import ModelRegistry

    started = time.perf_counter()
    now_ts  = time.time()

    # ── 1. Charger le registre existant ──────────────────────────────────────
    registry = ModelRegistry(_REGISTRY_PATH)
    gemini_before = [
        r for r in registry.all() if r.provider.lower() == "gemini"
    ]
    count_before = len(gemini_before)
    logger.info("[REFRESH] Registre chargé : %d entrées Gemini existantes.", count_before)

    # ── 2. Découverte API Google ──────────────────────────────────────────────
    # Fail-safe : toute exception ici interrompt le refresh sans écriture.
    # Autorité credentials : core/security/unified_vault.py. Fallback env conservé.
    try:
        from core.security.unified_vault import key_vault
        _vault_gemini = key_vault.get_provider_key("gemini") or None
    except Exception:
        _vault_gemini = None
    effective_key = api_key or _vault_gemini or os.getenv("GEMINI_API_KEY", "")
    discovery = GeminiDiscovery()

    logger.info("[REFRESH] Appel API Google Gemini discovery…")
    discovered_items: list[dict[str, Any]] = await discovery.discover(effective_key)

    if not isinstance(discovered_items, list):
        raise TypeError(
            f"[REFRESH] GeminiDiscovery.discover() a retourné un type inattendu : "
            f"{type(discovered_items)}. Registry non modifié."
        )

    discovered_count = len(discovered_items)
    logger.info("[REFRESH] %d modèles découverts (après filtrage interne GeminiDiscovery).", discovered_count)

    # ── 3. Validation minimale des items découverts ───────────────────────────
    valid_items: list[dict[str, Any]] = []
    invalid_ids: list[str] = []

    for item in discovered_items:
        mid = item.get("model_id", "")
        if not mid:
            invalid_ids.append("<no-id>")
            logger.warning("[REFRESH] Item sans model_id ignoré : %s", item)
            continue
        if item.get("provider", "").lower() != "gemini":
            invalid_ids.append(mid)
            logger.warning("[REFRESH] Item avec provider inattendu ignoré : %s", mid)
            continue
        if item.get("execution_scope") not in {"CLOUD", "LOCAL"}:
            # GeminiDiscovery retourne toujours CLOUD — normalisation défensive
            item["execution_scope"] = "CLOUD"
        if item.get("pricing_status") not in {"FREE", "PAID", "UNKNOWN", "NOT_APPLICABLE"}:
            item["pricing_status"] = "UNKNOWN"
        valid_items.append(item)

    logger.info(
        "[REFRESH] Validation : %d valides, %d invalides.",
        len(valid_items), len(invalid_ids),
    )

    # ── 4. Comparaison avec le registre ───────────────────────────────────────
    discovered_model_ids = {item["model_id"] for item in valid_items}
    existing_gemini_ids  = {r.model_id for r in gemini_before}

    new_ids       = discovered_model_ids - existing_gemini_ids
    existing_ids  = discovered_model_ids & existing_gemini_ids
    missing_ids   = existing_gemini_ids - discovered_model_ids

    logger.info(
        "[REFRESH] Diff : NEW=%d  EXISTING=%d  MISSING_FROM_API=%d",
        len(new_ids), len(existing_ids), len(missing_ids),
    )

    # ── 5. Ingestion via ModelLifecycleManager ────────────────────────────────
    # Le callback est uniquement déclenché pour les modèles ACTIVE qui
    # disparaissent de l'API — cas rare (aucun modèle Gemini ACTIVE actuellement).
    transition_cb = _make_transition_callback(registry)
    lifecycle_mgr = ModelLifecycleManager(registry)

    # ingest_discovery ajoute les nouveaux (CANDIDATE), met à jour les existants,
    # et appelle transition_callback pour les ACTIVE/QUALIFIED disparus.
    # Il appelle aussi registry.save() en fin de pipeline.
    ingested_records = lifecycle_mgr.ingest_discovery("gemini", valid_items)

    # ── 6. Vérification post-ingestion : aucun ACTIVE automatique ─────────────
    for record in ingested_records:
        if getattr(record, "lifecycle", "") == "ACTIVE":
            # Ce cas NE DOIT JAMAIS arriver via ingest_discovery —
            # ingest_discovery assigne CANDIDATE aux nouveaux, et préserve
            # l'état existant pour les connus.
            logger.error(
                "[REFRESH] INVARIANT VIOLÉ : modèle %s/%s est ACTIVE après ingestion. "
                "Ceci ne devrait pas arriver.",
                record.provider, record.model_id,
            )

    # ── 7. Compter les modèles par état post-refresh ──────────────────────────
    gemini_after   = [r for r in registry.all() if r.provider.lower() == "gemini"]
    count_after    = len(gemini_after)
    new_records    = [r for r in gemini_after if r.model_id in new_ids]
    superseded_ids = [
        r.model_id for r in gemini_after
        if r.model_id in missing_ids and r.lifecycle in {"QUARANTINED", "SUPERSEDED"}
    ]

    elapsed = time.perf_counter() - started

    result = {
        "timestamp_iso": datetime.now(UTC).isoformat(),
        "timestamp_unix": now_ts,
        "source": "https://generativelanguage.googleapis.com/v1beta/models",
        "duration_seconds": round(elapsed, 3),
        "discovered_count": discovered_count,
        "valid_count": len(valid_items),
        "registry_count_before": count_before,
        "registry_count_after": count_after,
        "new_models": sorted(new_ids),
        "existing_models": sorted(existing_ids),
        "missing_from_api": sorted(missing_ids),
        "superseded_models": superseded_ids,
        "invalid_models": invalid_ids,
        "errors": [],
        "warnings": [],
    }

    logger.info(
        "[REFRESH] Terminé en %.2fs — registre : %d → %d entrées Gemini.",
        elapsed, count_before, count_after,
    )
    return result


def _write_audit(result: dict[str, Any]) -> Path:
    """
    Écrit le rapport d'audit forensic dans state/audit/discovery/.
    Garantit qu'aucune API key ni secret n'est inclus.
    """
    _AUDIT_DIR.mkdir(parents=True, exist_ok=True)
    date_str = datetime.now(UTC).strftime("%Y-%m-%d")
    audit_path = _AUDIT_DIR / f"gemini_{date_str}.json"

    # Sérialisation défensive — on exclut tout champ contenant "key"/"secret"/"token"
    safe_result = {
        k: v for k, v in result.items()
        if not any(s in k.lower() for s in ("key", "secret", "token", "credential", "password"))
    }

    payload = json.dumps(safe_result, indent=2, ensure_ascii=False, sort_keys=True)
    audit_path.write_text(payload, encoding="utf-8")
    logger.info("[REFRESH] Audit écrit : %s", audit_path)
    return audit_path


# ── API publique ─────────────────────────────────────────────────────────────

def refresh_gemini_registry(*, api_key: str | None = None) -> dict[str, Any]:
    """
    Point d'entrée synchrone unique pour la synchronisation du registre Gemini.

    Utilisable depuis :
      - démarrage applicatif
      - refresh manuel
      - scheduler quotidien

    Garanties :
      - data/models/registry.json inchangé si toute erreur survient
      - Aucun modèle n'est activé automatiquement
      - Aucun secret n'est écrit dans les logs ou audits
      - Idempotent : deux appels sans changement API = même résultat

    Retourne le dict de résultat (également écrit dans state/audit/discovery/).
    Lève une exception en cas d'échec critique avec le registre inchangé.
    """
    try:
        result = asyncio.run(_run_refresh(api_key=api_key))
    except Exception as exc:
        logger.warning(
            "[REFRESH] FAIL-SAFE activé — registry.json NON modifié. "
            "Cause : %s : %s",
            type(exc).__name__, exc,
        )
        raise

    # Audit uniquement si le refresh a réussi
    try:
        audit_path = _write_audit(result)
        result["audit_path"] = str(audit_path)
    except Exception as exc:
        logger.warning("[REFRESH] Échec écriture audit (non bloquant) : %s", exc)
        result["audit_path"] = None

    return result


async def refresh_gemini_registry_async(*, api_key: str | None = None) -> dict[str, Any]:
    """
    Variante async de refresh_gemini_registry().
    Utiliser si appelé depuis un contexte asyncio déjà actif.
    """
    try:
        result = await _run_refresh(api_key=api_key)
    except Exception as exc:
        logger.warning(
            "[REFRESH] FAIL-SAFE activé — registry.json NON modifié. "
            "Cause : %s : %s",
            type(exc).__name__, exc,
        )
        raise

    try:
        audit_path = _write_audit(result)
        result["audit_path"] = str(audit_path)
    except Exception as exc:
        logger.warning("[REFRESH] Échec écriture audit (non bloquant) : %s", exc)
        result["audit_path"] = None

    return result
