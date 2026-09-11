"""E-ZZIO Wave 5 — Politique mémoire 3-tiers sur le store unique.

TIER 01 working   : minutes/heures, volatil, scope session/task.
TIER 02 semantic  : jours/semaines, inter-tâches, scope project.
TIER 03 persistent: explicite/durable, versionné, invalidable.

MEMORY IS CONTEXT, NOT AUTHORITY : truth_state transporté, jamais
promu automatiquement. PERSISTENT ≠ TRUE. OLD ≠ CURRENT.
"""
from __future__ import annotations

import hashlib
import json
import logging
import re
import time
import uuid
from dataclasses import dataclass, field, asdict
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger("ezzio.memory.tiers")

TIERS = ("working", "semantic", "persistent")
SCOPES = ("session", "task", "project", "workspace", "global")
MEMORY_TYPES = ("fact", "preference", "summary", "decision", "context",
                "reference", "task_context", "project_context")
TRUTH_STATES = ("unknown", "supported", "verified", "conflicted", "stale",
                "invalidated")
PRIVACY_CLASSES = ("normal", "restricted", "secret")

TIER_TTL = {
    "working": timedelta(hours=6),
    "semantic": timedelta(days=14),
    "persistent": None,
}

VOLATILE_HINTS = ("version", "prix", "price", "disponib", "api ",
                  "actuel", "en cours", "breaking", " CVE", "cve-")

_SECRET_PATTERNS = (
    "api_key", "apikey", "sk-", "sk_", "bearer ", "password", "passwd",
    "pwd=", "token=", "secret=", "client_secret", "private_key",
    "-----begin", "xoxb-", "ghp_", "gho_",
)


class MemoryViolationError(ValueError):
    pass


def _utcnow() -> str:
    return datetime.now(timezone.utc).isoformat()


def detect_secret(content: str) -> bool:
    low = (content or "").lower()
    return any(p in low for p in _SECRET_PATTERNS)


def content_hash(content: str) -> str:
    return hashlib.sha256((content or "").encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class MemoryObject:
    """Contrat mémoire : versionné, scopé, typé, avec état de vérité."""
    memory_id: str
    tier: str
    scope: str
    scope_id: str = ""
    memory_type: str = "context"
    content: str = ""
    provenance: Dict[str, Any] = field(default_factory=dict)
    truth_state: str = "unknown"
    importance: float = 0.5
    created_at: str = ""
    updated_at: str = ""
    expires_at: Optional[str] = None
    version: int = 1
    parent_version: Optional[int] = None
    privacy_class: str = "normal"
    source_refs: Tuple[str, ...] = ()
    evidence_refs: Tuple[str, ...] = ()
    task_refs: Tuple[str, ...] = ()
    project_refs: Tuple[str, ...] = ()

    def validate(self) -> List[str]:
        errors = []
        if not self.memory_id:
            errors.append("memory_id requis")
        if self.tier not in TIERS:
            errors.append(f"tier doit être dans {TIERS}")
        if self.scope not in SCOPES:
            errors.append(f"scope doit être dans {SCOPES}")
        if self.memory_type not in MEMORY_TYPES:
            errors.append(f"memory_type doit être dans {MEMORY_TYPES}")
        if self.truth_state not in TRUTH_STATES:
            errors.append(f"truth_state doit être dans {TRUTH_STATES}")
        if self.privacy_class not in PRIVACY_CLASSES:
            errors.append("privacy_class invalide")
        if not (self.content or "").strip():
            errors.append("content vide")
        if len(self.content or "") > 8000:
            errors.append("content > 8000 chars (contexte minimal)")
        if not (0.0 <= float(self.importance) <= 1.0):
            errors.append("importance doit être dans [0, 1]")
        if self.version < 1:
            errors.append("version >= 1 requise")
        if self.tier == "persistent" and self.truth_state == "unknown" \
                and self.memory_type == "fact":
            errors.append("fact persistant exige truth_state != unknown "
                          "(supported|verified + provenance)")
        return errors

    def ensure_valid(self) -> "MemoryObject":
        errors = self.validate()
        if errors:
            raise MemoryViolationError("; ".join(errors))
        return self

    def to_cell(self) -> Dict[str, Any]:
        now = _utcnow()
        prov = dict(self.provenance or {})
        prov.setdefault("source_refs", list(self.source_refs))
        prov.setdefault("evidence_refs", list(self.evidence_refs))
        prov.setdefault("task_refs", list(self.task_refs))
        prov.setdefault("project_refs", list(self.project_refs))
        return {
            "memory_id": self.memory_id, "tier": self.tier,
            "scope": self.scope, "scope_id": self.scope_id,
            "memory_type": self.memory_type, "content": self.content,
            "provenance": json.dumps(prov, ensure_ascii=False),
            "truth_state": self.truth_state,
            "importance": float(self.importance),
            "created_at": self.created_at or now,
            "updated_at": self.updated_at or now,
            "expires_at": self.expires_at, "version": self.version,
            "parent_version": self.parent_version,
            "privacy_class": self.privacy_class,
            "integrity": content_hash(self.content),
        }


def classify_eligibility(content: str, memory_type: str = "context",
                         privacy_hint: str = "normal") -> str:
    """Décision déterministe : IGNORE | WORKING | SEMANTIC | PERSISTENT |
    DEFER | QUARANTINE."""
    text = (content or "").strip()
    if len(text) < 8:
        return "IGNORE"
    if detect_secret(text) or privacy_hint == "secret":
        return "QUARANTINE"
    low = text.lower()
    if any(k in low for k in ("ignore policy", "ignore les instructions",
                              "reveal credentials", "system:")):
        return "QUARANTINE"
    if memory_type in ("task_context",):
        return "WORKING"
    if memory_type in ("preference", "decision", "project_context",
                       "summary"):
        return "SEMANTIC"
    return "WORKING"


def build_object(content: str, memory_type: str = "context",
                 scope: str = "task", scope_id: str = "",
                 tier: Optional[str] = None,
                 truth_state: str = "unknown",
                 importance: float = 0.5,
                 provenance: Optional[Dict[str, Any]] = None,
                 privacy_class: str = "normal") -> MemoryObject:
    """Construit un objet gouverné (TTL appliqué selon tier)."""
    tier = tier or {"task_context": "working", "project_context": "semantic",
                    "preference": "semantic", "decision": "semantic",
                    "summary": "semantic"}.get(memory_type, "working")
    if tier not in TIERS:
        raise MemoryViolationError(f"tier invalide : {tier}")
    if detect_secret(content):
        privacy_class = "secret"
    ttl = TIER_TTL[tier]
    now = datetime.now(timezone.utc)
    expires = (now + ttl).isoformat() if ttl else None
    obj = MemoryObject(
        memory_id=f"mem_{uuid.uuid4().hex[:12]}", tier=tier, scope=scope,
        scope_id=scope_id, memory_type=memory_type, content=content,
        provenance=provenance or {}, truth_state=truth_state,
        importance=importance, created_at=now.isoformat(),
        updated_at=now.isoformat(), expires_at=expires,
        privacy_class=privacy_class)
    return obj.ensure_valid()


def _audit(action: str, payload: Dict[str, Any],
           status: str = "SUCCESS") -> Optional[str]:
    try:
        from core.security.audit_ledger import AuditLedger
        res = AuditLedger().record_event(
            actor="memory-tiers", action=action,
            payload=payload, status=status)
        return str(res.get("id"))
    except Exception as exc:
        logger.warning("[MEMORY-TIERS] Audit non enregistré : %s", exc)
        return None


def is_expired(cell: Dict[str, Any], now: Optional[str] = None) -> bool:
    exp = cell.get("expires_at")
    if not exp:
        return False
    return exp < (now or _utcnow())


async def store(gateway, obj: MemoryObject) -> str:
    """Persiste après validation + dédup exacte (idempotent)."""
    obj.ensure_valid()
    existing = await gateway.list_cells(
        tier=obj.tier, scope=obj.scope, scope_id=obj.scope_id, limit=200)
    for cell in existing:
        if cell.get("integrity") == content_hash(obj.content) \
                and cell.get("memory_type") == obj.memory_type:
            return cell["memory_id"]
    await gateway.store_cell(obj.to_cell())
    _audit("MEMORY_CREATED", {"memory_id": obj.memory_id, "tier": obj.tier,
                              "scope": obj.scope,
                              "truth_state": obj.truth_state})
    return obj.memory_id


async def promote(gateway, memory_id: str, to_tier: str,
                  actor: str = "policy") -> str:
    """Promotion gouvernée : jamais de secret, jamais de fait non étayé."""
    if to_tier not in TIERS:
        raise MemoryViolationError(f"tier cible invalide : {to_tier}")
    cell = await gateway.get_cell(memory_id)
    if not cell:
        raise MemoryViolationError(f"mémoire inconnue : {memory_id}")
    order = {t: i for i, t in enumerate(TIERS)}
    if order[to_tier] <= order[cell["tier"]]:
        raise MemoryViolationError("promotion exige un tier supérieur")
    if cell.get("privacy_class") == "secret":
        raise MemoryViolationError("SECRET → jamais promu (fail-closed)")
    if to_tier == "persistent" and cell.get("truth_state") == "unknown" \
            and cell.get("memory_type") == "fact":
        raise MemoryViolationError("fact non étayé → jamais persistant")
    if cell.get("truth_state") in ("invalidated",):
        raise MemoryViolationError("mémoire invalidée non promouvable")
    ttl = TIER_TTL[to_tier]
    now = _utcnow()
    await gateway.update_cell_fields(memory_id, {
        "tier": to_tier, "updated_at": now,
        "expires_at": (datetime.now(timezone.utc) + ttl).isoformat()
        if ttl else None})
    _audit("MEMORY_PROMOTED", {"memory_id": memory_id,
                               "from": cell["tier"], "to": to_tier,
                               "actor": actor})
    return to_tier


async def demote(gateway, memory_id: str, to_tier: str,
                 actor: str = "policy") -> str:
    cell = await gateway.get_cell(memory_id)
    if not cell:
        raise MemoryViolationError(f"mémoire inconnue : {memory_id}")
    order = {t: i for i, t in enumerate(TIERS)}
    if order[to_tier] >= order[cell["tier"]]:
        raise MemoryViolationError("demotion exige un tier inférieur")
    ttl = TIER_TTL[to_tier]
    now = _utcnow()
    await gateway.update_cell_fields(memory_id, {
        "tier": to_tier, "updated_at": now,
        "expires_at": (datetime.now(timezone.utc) + ttl).isoformat()
        if ttl else None})
    _audit("MEMORY_DEMOTED", {"memory_id": memory_id,
                              "from": cell["tier"], "to": to_tier,
                              "actor": actor})
    return to_tier


async def invalidate(gateway, memory_id: str,
                     actor: str = "policy") -> bool:
    ok = await gateway.update_cell_fields(memory_id, {
        "truth_state": "invalidated", "updated_at": _utcnow()})
    if ok:
        _audit("MEMORY_INVALIDATED", {"memory_id": memory_id,
                                      "actor": actor})
    return ok


async def mark_stale(gateway, memory_id: str) -> bool:
    ok = await gateway.update_cell_fields(memory_id, {
        "truth_state": "stale", "updated_at": _utcnow()})
    if ok:
        _audit("MEMORY_STALE", {"memory_id": memory_id})
    return ok


async def expire_sweep(gateway) -> int:
    """Marque STALE les cellules volatiles périmées (jamais de suppression
    silencieuse du sémantique/persistant)."""
    now = _utcnow()
    count = 0
    for tier in TIERS:
        for cell in await gateway.list_cells(tier=tier, limit=500):
            if cell.get("expires_at") and cell["expires_at"] < now \
                    and cell.get("truth_state") not in ("stale",
                                                        "invalidated"):
                await gateway.update_cell_fields(cell["memory_id"], {
                    "truth_state": "stale", "updated_at": now})
                count += 1
    if count:
        _audit("MEMORY_EXPIRED", {"count": count})
    return count


async def purge_working_expired(gateway) -> int:
    """Supprime uniquement le working périmé (politique de rétention)."""
    now = _utcnow()
    count = 0
    for cell in await gateway.list_cells(tier="working", limit=1000):
        if cell.get("expires_at") and cell["expires_at"] < now:
            if await gateway.delete_cell(cell["memory_id"]):
                count += 1
    if count:
        _audit("MEMORY_PURGED", {"tier": "working", "count": count})
    return count


async def correct(gateway, memory_id: str, new_content: str,
                  actor: str = "user") -> str:
    """Correction : v1 INVALIDATED + v2 CURRENT, provenance conservée."""
    cell = await gateway.get_cell(memory_id)
    if not cell:
        raise MemoryViolationError(f"mémoire inconnue : {memory_id}")
    now = _utcnow()
    await gateway.update_cell_fields(memory_id, {
        "truth_state": "invalidated", "updated_at": now})
    new_id = f"mem_{uuid.uuid4().hex[:12]}"
    new_cell = dict(cell)
    new_cell.update({"memory_id": new_id, "content": new_content,
                     "integrity": content_hash(new_content),
                     "version": int(cell.get("version", 1)) + 1,
                     "parent_version": int(cell.get("version", 1)),
                     "truth_state": "unknown",
                     "created_at": now, "updated_at": now})
    await gateway.store_cell(new_cell)
    _audit("MEMORY_CORRECTED", {"old_id": memory_id, "new_id": new_id,
                                "actor": actor})
    return new_id


async def mark_conflict(gateway, id_a: str, id_b: str) -> bool:
    """Conflit : les deux passent CONFLICTED, aucune résolution silencieuse."""
    now = _utcnow()
    ok_a = await gateway.update_cell_fields(id_a, {
        "truth_state": "conflicted", "updated_at": now})
    ok_b = await gateway.update_cell_fields(id_b, {
        "truth_state": "conflicted", "updated_at": now})
    if ok_a and ok_b:
        _audit("MEMORY_CONFLICTED", {"ids": [id_a, id_b]})
        return True
    return False


def rank_score(cell: Dict[str, Any], now: Optional[str] = None) -> Tuple[float, Dict[str, float]]:
    """Score explicable : importance + fraîcheur + scope + vérité."""
    parts: Dict[str, float] = {}
    parts["importance"] = float(cell.get("importance", 0.5)) * 0.4
    try:
        age_h = (datetime.now(timezone.utc) - datetime.fromisoformat(
            cell.get("updated_at", now or _utcnow()))).total_seconds() / 3600.0
    except Exception:
        age_h = 24.0
    parts["freshness"] = max(0.0, 1.0 - age_h / 168.0) * 0.3
    scope_w = {"task": 1.0, "project": 0.8, "session": 0.7,
               "workspace": 0.5, "global": 0.3}
    parts["scope"] = scope_w.get(cell.get("scope"), 0.3) * 0.2
    truth_w = {"verified": 1.0, "supported": 0.7, "unknown": 0.4,
               "stale": 0.2, "conflicted": 0.1, "invalidated": 0.0}
    parts["truth"] = truth_w.get(cell.get("truth_state"), 0.0) * 0.1
    return round(sum(parts.values()), 4), parts


async def retrieve(gateway, query: str = "", task_id: str = "",
                   project_id: str = "", tiers: Optional[List[str]] = None,
                   max_memories: int = 5,
                   max_chars: int = 4000) -> Dict[str, Any]:
    """RIGHT MEMORY/RIGHT TIME : FTS + isolation scope + budget + états."""
    tiers = tiers or ["working", "semantic"]
    if "persistent" in tiers and not (task_id or project_id or query):
        tiers = [t for t in tiers if t != "persistent"]
    raw = await gateway.search_cells(query or " ", tiers=tiers,
                                     limit=max_memories * 4)
    now = _utcnow()
    kept = []
    for cell in raw:
        if cell.get("truth_state") == "invalidated":
            continue
        scope, sid = cell.get("scope"), cell.get("scope_id", "")
        if scope == "task" and task_id and sid and sid != task_id:
            continue
        if scope == "project" and project_id and sid and sid != project_id:
            continue
        if scope == "project" and not project_id and sid:
            continue
        if cell.get("expires_at") and cell["expires_at"] < now \
                and cell.get("truth_state") not in ("stale",):
            cell = dict(cell)
            cell["truth_state"] = "stale"
        score, parts = rank_score(cell, now)
        kept.append((score, parts, cell))
    kept.sort(key=lambda k: k[0], reverse=True)
    out, used = [], 0
    for score, parts, cell in kept:
        size = len(cell.get("content", ""))
        if len(out) >= max_memories or used + size > max_chars:
            break
        used += size
        out.append({"memory_id": cell["memory_id"], "tier": cell["tier"],
                    "scope": cell["scope"], "content": cell["content"],
                    "truth_state": cell["truth_state"],
                    "importance": cell.get("importance"),
                    "score": score, "score_parts": parts,
                    "why": f"tier={cell['tier']} scope={cell['scope']} "
                           f"truth={cell['truth_state']}"})
    try:
        await gateway.bump_access([m["memory_id"] for m in out])
    except Exception:
        pass
    return {"memories": out, "chars": used, "tiers_searched": tiers}


# --- Wave 5.5 : décision de besoin + vue workspace (pur, déterministe) ---

_HISTORY_MARKERS = (
    "hier", "avant-hier", "précédent", "précédente", "décidé", "décision",
    "rappelle", "souviens", "continue", "repren", "notre ", "nos ",
    "projet", "dernière fois", "comme convenu", "historique",
    "il y a", "autrefois",
)
_LONG_AGO_MARKERS = ("plusieurs mois", "il y a longtemps", "l'an dernier",
                     "ancienne décision")


def memory_need(prompt: str, has_active_tasks: bool = False
                ) -> Tuple[str, List[str]]:
    """Décision L0 du besoin mémoire (§5) : (besoin, tiers).
    NO_MEMORY | WORKING | SEMANTIC | PERSISTENT | MULTI_TIER."""
    t = (prompt or "").lower()
    if any(m in t for m in _LONG_AGO_MARKERS):
        return "PERSISTENT", ["persistent"]
    if "hier" in t or "continue" in t or "repren" in t:
        return "MULTI_TIER", ["working", "semantic"]
    if any(m in t for m in _HISTORY_MARKERS):
        return "SEMANTIC", ["semantic"]
    if has_active_tasks and any(
            m in t for m in ("tâche", "taches", "mission", "travail",
                             "où en", "statut", "avance", "état")):
        return "WORKING", ["working"]
    return "NO_MEMORY", []


def workspace_view(project_id: str, tasks: List[Dict[str, Any]],
                   cells: List[Dict[str, Any]],
                   artifacts: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Graphe minimal (§48) : project → tasks → memories → artifacts.
    Assembleur pur, sans nouvelle base (lectures existantes en entrée)."""
    task_ids = {t.get("mission_id", t.get("task_id", "")) for t in tasks}
    mem_by_task: Dict[str, List[str]] = {}
    proj_mems = []
    for c in cells:
        refs = set((c.get("provenance") or {}).get("task_refs", [])
                   if isinstance(c.get("provenance"), dict) else [])
        hits = sorted(task_ids & refs)
        if hits:
            for h in hits:
                mem_by_task.setdefault(h, []).append(c["memory_id"])
        elif c.get("scope") == "project":
            proj_mems.append(c["memory_id"])
    art_by_task: Dict[str, List[str]] = {}
    for a in artifacts:
        tid = a.get("task_id", "")
        if tid in task_ids:
            art_by_task.setdefault(tid, []).append(
                a.get("artifact_id", ""))
    return {"project_id": project_id,
            "tasks": sorted(task_ids),
            "memories_by_task": mem_by_task,
            "project_memories": sorted(proj_mems),
            "artifacts_by_task": art_by_task}
