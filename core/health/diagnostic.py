"""Observateur de santé E-ZZIO — LECTURE SEULE, aucune autorité.

Ce module OBSERVE le corps (imports, registre, pool local, bases, fichiers)
et produit des signaux classés. Il ne décide rien, ne patche rien, ne route
rien : le kernel, la policy et le router restent les seules autorités.

Statuts : HEALTHY | WATCH | DEGRADED | SICK | CRITICAL | QUARANTINED |
RECOVERED | UNKNOWN (absence de preuve = UNKNOWN, jamais HEALTHY).
"""
from __future__ import annotations

import importlib
import os
import sqlite3
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

KERNEL_MODULES = [
    "core.ezzio_master",
    "core.agent.coder_federation",
    "core.routing.model_registry",
    "core.providers.gemini_provider",
    "core.providers.ollama_provider",
    "core.memory.unified_gateway",
    "core.bus",
    "core.security.unified_vault",
    "core.identity.canonical_identity",
]

ESCALATION_LEVELS = {
    0: "observation seule",
    1: "correction triviale déterministe",
    2: "correction locale testable",
    3: "modèle spécialisé requis",
    4: "STOP — architecture/sécurité/données (humain)",
    5: "STOP — invérifiable automatiquement (humain)",
}


@dataclass
class HealthSignal:
    signal_id: str
    component: str
    domain: str
    severity: str  # HEALTHY|WATCH|DEGRADED|SICK|CRITICAL|QUARANTINED|RECOVERED|UNKNOWN
    symptom: str
    evidence: str
    confidence: float = 1.0
    recommended_action: str = ""
    escalation_level: int = 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "signal_id": self.signal_id,
            "timestamp_utc": datetime.now(UTC).isoformat(),
            "component": self.component,
            "domain": self.domain,
            "severity": self.severity,
            "symptom": self.symptom,
            "evidence": self.evidence,
            "confidence": self.confidence,
            "recommended_action": self.recommended_action,
            "escalation_level": self.escalation_level,
            "escalation": ESCALATION_LEVELS.get(self.escalation_level, "?"),
        }


def check_kernel_imports(modules: list[str] | None = None) -> list[HealthSignal]:
    """Douleur structurelle : un module noyau non importable."""
    signals = []
    for name in modules or KERNEL_MODULES:
        try:
            importlib.import_module(name)
            signals.append(HealthSignal(f"import:{name}", name, "kernel", "HEALTHY",
                                        "import OK", f"importlib {name}"))
        except Exception as exc:
            signals.append(HealthSignal(f"import:{name}", name, "kernel", "CRITICAL",
                                        f"échec import: {exc!r}", f"importlib {name}",
                                        recommended_action="diagnostiquer la dépendance manquante",
                                        escalation_level=2))
    return signals


def check_model_registry() -> list[HealthSignal]:
    """Douleur décisionnelle : registre vide, défauts non installés, liens morts."""
    from core.routing.model_registry import ModelQualificationStatus, canonical_model_registry

    signals = []
    try:
        qualified = canonical_model_registry.list_models()
    except Exception as exc:
        return [HealthSignal("registry:read", "model_registry", "models", "CRITICAL",
                             f"lecture impossible: {exc!r}", "list_models()",
                             escalation_level=2)]
    if not qualified:
        signals.append(HealthSignal("registry:empty", "model_registry", "models", "CRITICAL",
                                    "aucun modèle qualifié", "list_models()==[]",
                                    escalation_level=4))
    ok = (ModelQualificationStatus.QUALIFIED, ModelQualificationStatus.QUALIFIED_WITH_LIMITATIONS)
    dead = [(m.model_id, f) for m in qualified for f in (m.fallback_chain or [])
            if (r := canonical_model_registry.get(f)) is None or r.qualification_status not in ok]
    if dead:
        signals.append(HealthSignal("registry:deadlinks", "model_registry", "models", "WATCH",
                                    f"{len(dead)} liens de repli non qualifiés",
                                    f"ex: {dead[0]}", escalation_level=1))
    else:
        signals.append(HealthSignal("registry:links", "model_registry", "models", "HEALTHY",
                                    f"{len(qualified)} qualifiés, 0 lien mort", "fallback scan"))
    return signals


def check_databases(paths: list[str] | None = None) -> list[HealthSignal]:
    """Douleur métabolique : taille, WAL, pression."""
    signals = []
    for p in paths or ["runtime/evidence/evidence.db"]:
        if not os.path.exists(p):
            signals.append(HealthSignal(f"db:{p}", p, "database", "UNKNOWN",
                                        "base absente (créée à l'usage)", f"stat {p}"))
            continue
        size = os.path.getsize(p)
        try:
            db = sqlite3.connect(p)
            journal = db.execute("PRAGMA journal_mode;").fetchone()[0]
            freelist = db.execute("PRAGMA freelist_count;").fetchone()[0]
            db.close()
        except Exception as exc:
            signals.append(HealthSignal(f"db:{p}", p, "database", "SICK",
                                        f"lecture impossible: {exc!r}", f"sqlite {p}",
                                        escalation_level=2))
            continue
        sev = "HEALTHY" if size < 100 * 1024 * 1024 else "WATCH"
        signals.append(HealthSignal(f"db:{p}", p, "database", sev,
                                    f"{size // 1024}KB journal={journal} freelist={freelist}",
                                    f"stat+pragma {p}"))
    return signals


def check_ollama_pool() -> list[HealthSignal]:
    """Douleur de capacité : défauts fédération vs artefacts installés."""
    try:
        from core.agent.coder_federation import CoderModelFederationRouter
        from core.providers.ollama_provider import OllamaProvider
    except Exception as exc:
        return [HealthSignal("pool:read", "ollama", "models", "UNKNOWN",
                             f"lecture impossible: {exc!r}", "imports")]
    import asyncio
    try:
        installed = set(asyncio.run(OllamaProvider().health()).get("installed_models", []))
    except Exception as exc:
        return [HealthSignal("pool:daemon", "ollama", "models", "WATCH",
                             f"démon injoignable: {exc!r}", "health()",
                             escalation_level=1)]
    want = {CoderModelFederationRouter.DEFAULT_MODELS.get("ollama", ""),
            OllamaProvider.DEFAULT_MODEL}
    missing = sorted(m for m in want if m and m not in installed)
    if missing:
        return [HealthSignal("pool:missing", "ollama", "models", "DEGRADED",
                             f"défauts absents du pool: {missing}", f"health {sorted(installed)}",
                             recommended_action="réaligner les défauts ou installer",
                             escalation_level=2)]
    return [HealthSignal("pool:ok", "ollama", "models", "HEALTHY",
                         f"défauts installés parmi {len(installed)} artefacts", "health()")]


def full_diagnostic() -> dict[str, Any]:
    """Assemble l'état de santé logique (lecture seule)."""
    signals = check_kernel_imports() + check_model_registry() + check_databases() + check_ollama_pool()
    order = {"CRITICAL": 0, "SICK": 1, "DEGRADED": 2, "WATCH": 3, "UNKNOWN": 4, "HEALTHY": 5}
    worst = min((order.get(s.severity, 4) for s in signals), default=5)
    status = next(k for k, v in order.items() if v == worst)
    return {
        "system": status,
        "signals": [s.to_dict() for s in signals],
        "counts": {k: sum(1 for s in signals if s.severity == k) for k in order},
    }


def record_evolution_event(signal: dict[str, Any], treatment: str, result: str,
                           ledger=None) -> dict[str, Any]:
    """Mémorise un diagnostic/traitement dans le ledger d'audit existant.

    Mémoire d'évolution (XXXVII) : anomalies, diagnostics, traitements,
    résultats. Aucun nouveau store — l'AuditLedger append-only scellé
    est l'autorité. `ledger` injectable pour tests (défaut : singleton).
    """
    from core.security.audit_ledger import audit_ledger

    store = ledger or audit_ledger
    return store.record_event(
        actor="health-engine",
        action="EVOLUTION_RECORD",
        payload={"signal": signal, "treatment": treatment, "result": result},
        status="SUCCESS" if result == "HEALED" else "PARTIAL",
    )
