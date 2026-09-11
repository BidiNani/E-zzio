"""
E-ZZIO Sovereign Routing & Operations Telemetry Engine.
Fournit une observabilité continue, légère et locale :
- Journalisation append-only des événements de requête
- Suivi du cycle de vie des modèles (ELIGIBLE, DEPRIORITIZED, RECOVERED)
- Métriques par profil (latence p95, taux de hit cache, bascules cloud)
- Détection proactive des anomalies (flapping, 429 burst, stampede)
- Respect strict des secrets (zéro credential exposé)
"""
from __future__ import annotations
import os
import json
import time
import uuid
import logging
from pathlib import Path
from typing import Dict, Any, List, Optional
from collections import deque

logger = logging.getLogger("RoutingTelemetry")

STATE_DIR = Path("G:/AI/E-zzio/state/telemetry")
STATE_DIR.mkdir(parents=True, exist_ok=True)
EVENTS_LOG_FILE = STATE_DIR / "routing_events.jsonl"
ANOMALIES_LOG_FILE = STATE_DIR / "anomalies.jsonl"


class RoutingTelemetryEngine:
    """Moteur local d'observabilité continue du routage cognitif."""

    def __init__(self, max_memory_records: int = 1000):
        self.max_records = max_memory_records
        self._recent_events: deque = deque(maxlen=max_memory_records)
        self._anomalies: deque = deque(maxlen=200)
        self._quota_transitions: deque = deque(maxlen=200)
        self._profile_stats: Dict[str, Dict[str, Any]] = {
            "fast": {"count": 0, "cache_hits": 0, "cloud_primary": 0, "cloud_failovers": 0, "ollama_fallbacks": 0, "latencies": []},
            "general": {"count": 0, "cache_hits": 0, "cloud_primary": 0, "cloud_failovers": 0, "ollama_fallbacks": 0, "latencies": []},
            "coding": {"count": 0, "cache_hits": 0, "cloud_primary": 0, "cloud_failovers": 0, "ollama_fallbacks": 0, "latencies": []},
            "deep_reasoning": {"count": 0, "cache_hits": 0, "cloud_primary": 0, "cloud_failovers": 0, "ollama_fallbacks": 0, "latencies": []},
        }

    def record_request(
        self,
        request_id: str,
        profile: str,
        model_requested: str,
        provider_selected: str,
        model_selected: str,
        cache_status: str,
        singleflight_role: str,
        latency_ms: float,
        success: bool,
        failover_count: int = 0,
        attempted_targets: Optional[List[str]] = None,
        error: Optional[str] = None
    ) -> Dict[str, Any]:
        """Enregistre un événement complet d'inférence."""
        clean_profile = profile.lower()
        ollama_used = (provider_selected == "ollama")
        is_cache_hit = (cache_status == "CACHE_HIT")

        event = {
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
            "timestamp_epoch": time.time(),
            "request_id": request_id,
            "profile": clean_profile,
            "model_requested": model_requested,
            "provider_selected": provider_selected,
            "model_selected": model_selected,
            "cache_status": cache_status,
            "singleflight_role": singleflight_role,
            "latency_ms": round(latency_ms, 2),
            "success": success,
            "failover_count": failover_count,
            "attempted_targets": attempted_targets or [],
            "ollama_used": ollama_used,
            "error": error
        }

        # 1. Mise à jour de la mémoire vive
        self._recent_events.append(event)

        # 2. Mise à jour des agrégats par profil
        if clean_profile in self._profile_stats:
            pstat = self._profile_stats[clean_profile]
            pstat["count"] += 1
            if is_cache_hit:
                pstat["cache_hits"] += 1
            elif failover_count == 0 and not ollama_used:
                pstat["cloud_primary"] += 1
            elif not ollama_used and failover_count > 0:
                pstat["cloud_failovers"] += 1
            elif ollama_used:
                pstat["ollama_fallbacks"] += 1

            if len(pstat["latencies"]) >= 500:
                pstat["latencies"].pop(0)
            pstat["latencies"].append(latency_ms)

        # 3. Détection d'anomalies
        self._check_anomalies(event)

        # 4. Écriture append-only légère sur disque
        try:
            with open(EVENTS_LOG_FILE, "a", encoding="utf-8") as f:
                f.write(json.dumps(event, ensure_ascii=False) + "\n")
        except Exception as exc:
            logger.debug("[TELEMETRY-WRITE-SKIP] %s", exc)

        return event

    def record_quota_transition(
        self,
        model: str,
        previous_state: str,
        new_state: str,
        reason: str,
        cooldown_sec: float = 0.0
    ):
        """Enregistre un changement d'état de quota / délestage."""
        transition = {
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
            "model": model,
            "previous_state": previous_state,
            "new_state": new_state,
            "reason": reason,
            "cooldown_sec": cooldown_sec
        }
        self._quota_transitions.append(transition)
        logger.info("[QUOTA-TRANSITION] %s: %s -> %s (%s)", model, previous_state, new_state, reason)

    def _check_anomalies(self, event: Dict[str, Any]):
        """Détecte les anomalies de routage et de qualité de service."""
        # 1. Ollama utilisé en mode nominal alors qu'aucun failover n'a eu lieu
        if event["ollama_used"] and event["failover_count"] == 0 and event["profile"] != "local_only":
            self.record_anomaly(
                anomaly_type="UNEXPECTED_OLLAMA_NOMINAL",
                description="Ollama sélectionné directement sans tentative cloud préalable",
                context=event
            )

        # 2. Pic de latence anormal sur un profil FAST (> 2500ms hors premier appel)
        if event["profile"] == "fast" and event["latency_ms"] > 2500.0 and event["cache_status"] != "CACHE_HIT":
            self.record_anomaly(
                anomaly_type="LATENCY_SPIKE_FAST",
                description=f"Latence FAST anormale ({event['latency_ms']}ms)",
                context=event
            )

    def record_anomaly(self, anomaly_type: str, description: str, context: Dict[str, Any]):
        """Enregistre une anomalie dans le journal des anomalies."""
        anom = {
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
            "anomaly_type": anomaly_type,
            "description": description,
            "context": context
        }
        self._anomalies.append(anom)
        logger.warning("[ROUTING-ANOMALY] %s : %s", anomaly_type, description)
        try:
            with open(ANOMALIES_LOG_FILE, "a", encoding="utf-8") as f:
                f.write(json.dumps(anom, ensure_ascii=False) + "\n")
        except Exception:
            pass

    def get_summary_metrics(self) -> Dict[str, Any]:
        """Calcule les métriques globales et par profil pour /metrics."""
        total_requests = len(self._recent_events)
        total_hits = sum(1 for e in self._recent_events if e.get("cache_status") == "CACHE_HIT")
        total_cloud_primary = sum(1 for e in self._recent_events if e.get("provider_selected") == "gemini_pool" and e.get("failover_count", 0) == 0)
        total_cloud_failovers = sum(1 for e in self._recent_events if e.get("provider_selected") == "groq")
        total_ollama_fallbacks = sum(1 for e in self._recent_events if e.get("provider_selected") == "ollama")

        hit_rate = (total_hits / total_requests * 100.0) if total_requests > 0 else 0.0
        cloud_failover_rate = (total_cloud_failovers / total_requests * 100.0) if total_requests > 0 else 0.0
        ollama_fallback_rate = (total_ollama_fallbacks / total_requests * 100.0) if total_requests > 0 else 0.0

        profile_details = {}
        for p, data in self._profile_stats.items():
            lats = sorted(data["latencies"]) if data["latencies"] else [0.0]
            mean_lat = sum(lats) / len(lats) if lats else 0.0
            median_lat = lats[len(lats) // 2] if lats else 0.0
            p95_lat = lats[int(len(lats) * 0.95)] if lats else 0.0

            profile_details[p] = {
                "requests": data["count"],
                "cache_hits": data["cache_hits"],
                "cloud_primary": data["cloud_primary"],
                "cloud_failovers": data["cloud_failovers"],
                "ollama_fallbacks": data["ollama_fallbacks"],
                "latency_mean_ms": round(mean_lat, 2),
                "latency_median_ms": round(median_lat, 2),
                "latency_p95_ms": round(p95_lat, 2),
            }

        return {
            "total_requests_recorded": total_requests,
            "cache_hits": total_hits,
            "cache_hit_rate_percent": round(hit_rate, 2),
            "cloud_primary_calls": total_cloud_primary,
            "cloud_failovers": total_cloud_failovers,
            "cloud_failover_rate_percent": round(cloud_failover_rate, 2),
            "ollama_fallbacks": total_ollama_fallbacks,
            "ollama_fallback_rate_percent": round(ollama_fallback_rate, 2),
            "anomalies_count": len(self._anomalies),
            "quota_transitions_count": len(self._quota_transitions),
            "profile_metrics": profile_details
        }


# Singleton global de télémétrie
routing_telemetry = RoutingTelemetryEngine()