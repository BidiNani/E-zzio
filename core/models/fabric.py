"""E-ZZIO Autonomous Model Fabric with upstream FREE_ONLY filtering."""

from __future__ import annotations

import asyncio
import os
import time
from datetime import UTC
from pathlib import Path
from typing import Any

from .discovery.gemini import GeminiDiscovery
from .discovery.groq import GroqDiscovery
from .discovery.litellm import LiteLLMDiscovery
from .discovery.openrouter import OpenRouterDiscovery
from .ezzio_router import EzzioRouter
from .key_pool import KeyPoolManager
from .lifecycle import ModelLifecycleManager
from .qualification.free_only import filter_free_only
from .qualification.gate import QualificationGate
from .registry import ModelLifecycle, ModelRegistry
from .telemetry import SafeTelemetry


class AutonomousModelFabric:

    def __init__(
        self,
        project_root: str | Path,
    ) -> None:

        self.project_root = Path(project_root)

        data_root = self.project_root / "data" / "models"
        forensic_root = self.project_root / "_forensic" / "reports"

        self.registry = ModelRegistry(data_root / "registry.json")
        self.lifecycle = ModelLifecycleManager(self.registry)
        self.key_pool = KeyPoolManager()
        self.telemetry = SafeTelemetry(forensic_root)

        self.router = EzzioRouter(
            registry=self.registry,
            key_pool=self.key_pool,
            telemetry=self.telemetry,
        )

        self.gate = QualificationGate()

        self.providers = {
            "gemini": GeminiDiscovery(),
            "groq": GroqDiscovery(),
            "openrouter": OpenRouterDiscovery(),
            "litellm": LiteLLMDiscovery(),
        }
        self.discoveries = {}

    def key_for_provider(self, provider: str) -> str | None:
        name = f"{provider.upper()}_API_KEY"
        return os.environ.get(name, "").strip() or None

    async def discover(
        self,
    ) -> dict[str, list[dict[str, Any]]]:

        discovered: dict[str, list[dict[str, Any]]] = {}

        for provider, adapter in self.providers.items():
            key = self.key_for_provider(provider) or ""

            try:
                raw_models = await adapter.discover(key)

                accepted, rejected, stats = filter_free_only(raw_models)
                print(
                    f"[FREE_ONLY] {provider.upper():<12} : "
                    f"FREE={stats['FREE']}  "
                    f"PAID={stats['PAID']}  "
                    f"UNKNOWN={stats['UNKNOWN']}"
                )
                print(
                    f"[DEBUG] {provider.upper()} : "
                    f"raw={len(raw_models)} "
                    f"accepted={len(accepted)} "
                    f"rejected={len(rejected)}"
                )

                # La découverte FREE validée ne dépend pas du lifecycle.
                discovered[provider] = accepted

                # L'ingestion lifecycle est optionnelle : elle ne doit jamais
                # effacer ni invalider un catalogue déjà filtré FREE_ONLY.
                try:
                    ingest = getattr(self.lifecycle, "ingest", None)

                    if callable(ingest):
                        result = ingest(provider, accepted)

                        if hasattr(result, "__await__"):
                            await result
                    else:
                        print(
                            f"[WARN] {provider.upper():<12} : "
                            "ModelLifecycleManager.ingest absent ; "
                            "catalogue FREE conservé."
                        )

                except Exception as exc:
                    print(
                        f"[WARN] {provider.upper():<12} : "
                        f"ingestion lifecycle ignorée : {exc}"
                    )

                self.telemetry.emit(
                    "free_only_filter_summary",
                    {
                        "provider": provider,
                        "stats": stats,
                        "accepted_count": len(accepted),
                        "rejected_count": len(rejected),
                    },
                )

                self.telemetry.emit(
                    "discovery_success",
                    {
                        "provider": provider,
                        "raw_count": len(raw_models),
                        "free_accepted_count": len(accepted),
                    },
                )

            except Exception as exc:
                print(
                    f"[FREE_ONLY] {provider.upper():<12} : "
                    f"échec découverte : {exc}"
                )
                discovered[provider] = []
                self.telemetry.emit(
                    "discovery_failure",
                    {
                        "provider": provider,
                        "error_type": type(exc).__name__,
                    },
                )

        for provider, models in discovered.items():
            print(
                f"[DEBUG] RETURN {provider.upper()} = {len(models)}"
            )

        self.discoveries = discovered
        return discovered

    async def discover_all(self) -> dict[str, list[dict[str, Any]]]:
        return await self.discover()

    def activate_qualified(
        self,
        qualification_results: list[dict[str, Any]],
        exclusive_per_tier: bool = True,
    ) -> list[dict[str, Any]]:
        provider_rank = {
            "groq": 0,
            "gemini": 1,
            "openrouter": 2,
            "litellm": 99,
        }
        valid_tiers = {"FAST", "MID", "HEAVY"}
        transitions: list[dict[str, Any]] = []
        qualified_by_tier: dict[str, list[dict[str, Any]]] = {}

        for result in qualification_results:
            provider = str(result.get("provider", "")).lower()
            model_id = str(result.get("model_id", ""))
            qualified = bool(result.get("qualified", False))
            tier = str(result.get("tier", "UNQUALIFIED")).upper()

            entry = self.registry.get(provider, model_id)
            if entry is None:
                print(
                    f"[WARN] Activation ignorée : "
                    f"{provider}/{model_id} absent du registre."
                )
                continue

            if not qualified or tier not in valid_tiers:
                old_state = entry.lifecycle
                entry.lifecycle = ModelLifecycle.QUARANTINED.value
                entry.tier = "UNQUALIFIED"
                transitions.append(
                    {
                        "model": f"{provider}/{model_id}",
                        "old_state": old_state,
                        "new_state": ModelLifecycle.QUARANTINED.value,
                        "tier": "UNQUALIFIED",
                    }
                )
                continue

            qualified_by_tier.setdefault(tier, []).append(result)

        winners: dict[str, dict[str, Any]] = {}
        for tier, candidates in qualified_by_tier.items():
            winners[tier] = min(
                candidates,
                key=lambda candidate: (
                    -float(candidate.get("score", 0.0)),
                    float(candidate.get("latency_ms", float("inf"))),
                    provider_rank.get(
                        str(candidate.get("provider", "")).lower(),
                        999,
                    ),
                    str(candidate.get("model_id", "")).lower(),
                ),
            )

        for tier, candidates in qualified_by_tier.items():
            winner = winners[tier]
            for candidate in candidates:
                if candidate is winner:
                    continue
                c_provider = str(candidate["provider"]).lower()
                c_model_id = str(candidate["model_id"])
                c_entry = self.registry.get(c_provider, c_model_id)
                if c_entry is None:
                    continue
                old_state = c_entry.lifecycle
                c_entry.lifecycle = ModelLifecycle.SUPERSEDED.value
                transitions.append(
                    {
                        "model": f"{c_provider}/{c_model_id}",
                        "old_state": old_state,
                        "new_state": ModelLifecycle.SUPERSEDED.value,
                        "tier": tier,
                    }
                )

        for tier, winner in winners.items():
            provider = str(winner["provider"]).lower()
            model_id = str(winner["model_id"])
            entry = self.registry.get(provider, model_id)
            if entry is None:
                continue

            if exclusive_per_tier:
                for existing in self.registry.all():
                    if (
                        existing.lifecycle == ModelLifecycle.ACTIVE.value
                        and existing.tier == tier
                        and existing is not entry
                    ):
                        old_state = existing.lifecycle
                        existing.lifecycle = ModelLifecycle.SUPERSEDED.value
                        transitions.append(
                            {
                                "model": (
                                    f"{existing.provider}/"
                                    f"{existing.model_id}"
                                ),
                                "old_state": old_state,
                                "new_state": (
                                    ModelLifecycle.SUPERSEDED.value
                                ),
                                "tier": tier,
                            }
                        )

            old_state = entry.lifecycle
            entry.lifecycle = ModelLifecycle.ACTIVE.value
            entry.tier = tier
            entry.qualification_score = float(
                winner.get("score", 0.0)
            )
            entry.latency_ms = float(
                winner.get("latency_ms", 0.0)
            )
            entry.last_verified = time.time()
            transitions.append(
                {
                    "model": f"{provider}/{model_id}",
                    "old_state": old_state,
                    "new_state": ModelLifecycle.ACTIVE.value,
                    "tier": tier,
                }
            )

        self.registry.save()
        return transitions

    async def qualify_candidates(
        self,
    ) -> list[dict[str, Any]]:

        results = []

        for model in self.registry.all():
            if model.lifecycle not in {
                ModelLifecycle.CANDIDATE.value,
                ModelLifecycle.SUPERSEDED.value,
            }:
                continue

            provider = model.provider.lower()
            endpoint = getattr(self.router, 'endpoint', lambda p: getattr(self.router, 'endpoints', {}).get(p))(provider) if hasattr(self.router, 'endpoint') or hasattr(self.router, 'endpoints') else None

            if not endpoint:
                continue

            key = self.key_for_provider(provider)
            if not key:
                continue

            model.lifecycle = ModelLifecycle.QUALIFYING.value
            metadata = model.metadata or {}

            result = await self.gate.qualify_openai_compatible(
                provider=provider,
                model=metadata,
                api_key=key,
                endpoint=endpoint,
            )

            results.append(result)

            if result["qualified"]:
                model.lifecycle = ModelLifecycle.ACTIVE.value
                model.tier = result["tier"]
                model.latency_ms = result["latency_ms"]
                model.qualification_score = result["score"]
                model.last_verified = time.time()
            else:
                model.lifecycle = ModelLifecycle.QUARANTINED.value

        self.registry.save()
        return results

    async def refresh(self) -> dict[str, Any]:
        started = time.perf_counter()

        discovered = await self.discover()
        qualified = await self.qualify_candidates()

        elapsed = time.perf_counter() - started

        summary = {
            "timestamp": time.time(),
            "duration_seconds": round(elapsed, 3),
            "providers": {
                provider: len(models)
                for provider, models in discovered.items()
            },
            "qualified": sum(1 for item in qualified if item["qualified"]),
            "rejected": sum(1 for item in qualified if not item["qualified"]),
            "active_models": len(self.registry.active()),
        }

        self.telemetry.emit("fabric_refresh", summary)
        return summary

    async def run_forever(self, interval_seconds: int = 21600) -> None:
        while True:
            try:
                await self.refresh()
            except Exception as exc:
                self.telemetry.emit(
                    "refresh_failure",
                    {"error_type": type(exc).__name__},
                )
            await asyncio.sleep(interval_seconds)









    def _quarantine_runtime_violation_v1(
        self,
        *,
        provider: str,
        model_id: str,
        tier: str,
        reason: str,
    ) -> bool:
        return self.transition(
            provider=provider,
            model_id=model_id,
            new_state="QUARANTINED",
            actor="runtime_violation",
            reason=reason,
            operator="runtime_guard",
            new_tier="UNQUALIFIED",
        )

    def _rehabilitate_model_v1(
        self,
        *,
        provider: str,
        model_id: str,
        reason: str,
        operator: str,
    ) -> bool:
        if not operator or len(operator.strip()) < 2:
            raise ValueError("Opérateur invalide")
        if not reason or len(reason.strip()) < 5:
            raise ValueError("Motif invalide")
        return self.transition(
            provider=provider,
            model_id=model_id,
            new_state="CANDIDATE",
            actor="admin_rehabilitation",
            reason=reason.strip(),
            operator=operator.strip(),
            new_tier="UNQUALIFIED",
        )


    def transition(
        self,
        *,
        provider: str,
        model_id: str,
        new_state: str,
        actor: str,
        reason: str,
        operator: str = "system",
        new_tier: str | None = None,
    ) -> bool:
        from datetime import datetime
        entry = self.registry.get(provider, model_id)
        if entry is None:
            return False

        old_state = getattr(entry, "lifecycle", "DISCOVERED")
        now_iso = datetime.now(UTC).isoformat()

        allowed = {
            ("DISCOVERED", "CANDIDATE"): ["discovery"],
            ("CANDIDATE", "QUALIFIED"): ["qualification_gate"],
            ("CANDIDATE", "QUARANTINED"): ["qualification_gate"],
            ("QUALIFIED", "ACTIVE"): ["activate_qualified"],
            ("QUALIFIED", "UNQUALIFIED"): ["qualification_gate"],
            ("ACTIVE", "QUARANTINED"): ["runtime_violation"],
            ("ACTIVE", "SUPERSEDED"): ["lifecycle_manager"],
            ("ACTIVE", "RETIRED"): ["lifecycle_manager"],
            ("QUARANTINED", "CANDIDATE"): ["admin_rehabilitation"],
            ("QUARANTINED", "UNQUALIFIED"): ["qualification_gate"],
        }

        if (old_state, new_state) not in allowed or actor not in allowed[(old_state, new_state)]:
            raise RuntimeError(f"Transition illégale : {old_state} -> {new_state} par {actor}")

        if new_state == "QUARANTINED":
            entry.tier = "UNQUALIFIED"
            entry.failure_count = int(getattr(entry, "failure_count", 0)) + 1
            entry.last_quarantine_at = now_iso
            entry.last_quarantine_reason = reason[:300]
            entry.last_quarantine_operator = operator
            if hasattr(self, "router") and hasattr(self.router, "invalidate_cache"):
                self.router.invalidate_cache(provider, model_id)

        elif new_state == "CANDIDATE" and old_state == "QUARANTINED":
            failures = int(getattr(entry, "failure_count", 0))
            entry.historical_failures = int(getattr(entry, "historical_failures", 0)) + failures
            entry.failure_count = 0
            entry.rehabilitation_count = int(getattr(entry, "rehabilitation_count", 0)) + 1
            entry.rehabilitated_at = now_iso
            entry.rehabilitated_by = operator
            entry.rehabilitation_reason = reason[:300]
            entry.tier = "UNQUALIFIED"

        elif new_state == "ACTIVE" and new_tier:
            entry.tier = new_tier

        entry.lifecycle = new_state
        entry.updated_at = now_iso
        if hasattr(self, "_sync_router_with_registry"):
            self._sync_router_with_registry()
        self.registry.save()
        return True

    def quarantine_runtime_violation(
        self,
        *,
        provider: str,
        model_id: str,
        tier: str,
        reason: str,
    ) -> bool:
        return self.transition(
            provider=provider,
            model_id=model_id,
            new_state="QUARANTINED",
            actor="runtime_violation",
            reason=reason,
            operator="runtime_guard",
            new_tier="UNQUALIFIED",
        )

    def rehabilitate_model(
        self,
        *,
        provider: str,
        model_id: str,
        reason: str,
        operator: str,
    ) -> bool:
        if not operator or len(operator.strip()) < 2:
            raise ValueError("Opérateur invalide")
        if not reason or len(reason.strip()) < 5:
            raise ValueError("Motif invalide")
        return self.transition(
            provider=provider,
            model_id=model_id,
            new_state="CANDIDATE",
            actor="admin_rehabilitation",
            reason=reason.strip(),
            operator=operator.strip(),
            new_tier="UNQUALIFIED",
        )




    def _sync_router_with_registry(self) -> None:
        """
        FAIL-CLOSED Synchronization (Canonique):
        Extrait strictement les modèles du ModelRegistry dont l'état de cycle de vie est ACTIVE.
        Exclut immédiatement tout modèle DISCOVERED, CANDIDATE, QUALIFIED, QUARANTINED, SUPERSEDED ou RETIRED.
        """
        active_models = []
        try:
            records = []
            if hasattr(self.registry, "_models") and isinstance(self.registry._models, dict):
                records = self.registry._models.values()
            elif hasattr(self.registry, "all") and callable(self.registry.all):
                records = self.registry.all()

            for entry in records:
                lifecycle = str(getattr(entry, "lifecycle", "DISCOVERED")).upper()
                if lifecycle == "ACTIVE":
                    provider = str(getattr(entry, "provider", "openai")).lower()
                    model_id = str(getattr(entry, "model_id", "gpt-4"))
                    tier = str(getattr(entry, "tier", "FAST") or "FAST").upper()

                    deployment_dict = {
                        "model_name": tier,
                        "litellm_params": {
                            "model": f"{provider}/{model_id}",
                            "custom_llm_provider": provider,
                        },
                        "model_info": {
                            "id": f"{provider}_{model_id}",
                            "base_model": model_id,
                            "lifecycle": "ACTIVE"
                        }
                    }
                    active_models.append(deployment_dict)
        except Exception as e:
            print(f"[FAIL-CLOSED CRITICAL ERROR] Synchronisation active échouée : {e}")
            active_models = []

        if hasattr(self, "router") and self.router is not None:
            if hasattr(self.router, "set_model_list"):
                try:
                    self.router.set_model_list(active_models)
                except Exception:
                    self.router.model_list = active_models
            else:
                self.router.model_list = active_models

def build_fabric(project_root: str | Path = "G:/AI/E-zzio") -> AutonomousModelFabric:
    """
    Factory canonique pour instancier et synchroniser AutonomousModelFabric.
    """
    fabric = AutonomousModelFabric(project_root=project_root)
    if hasattr(fabric, "_sync_router_with_registry"):
        fabric._sync_router_with_registry()
    return fabric
