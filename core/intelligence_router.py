"""
E-ZZIO V7.25.0 — Fault Tolerant Intelligence Core
Intègre le Circuit Breaker, le chaînage SHA-256 du Ledger et la télémétrie Windows.
"""

import hashlib
import json
import uuid
from datetime import UTC, datetime
from pathlib import Path

from ollama.adaptive_governor import ollama_governor
from ollama.windows_telemetry import windows_memory

from core.routing.circuit_breaker import circuit_breaker
from core.routing.contracts import ExecutionDecision, RouteConstraints, Urgency
from core.routing.scorer import RoutingScorer
from providers.provider_registry import _load_capabilities, _load_performance, get_provider_instance
from providers.provider_response import ProviderResponse

ROOT_DIR = Path(__file__).resolve().parent.parent
LOCAL_REGISTRY_PATH = ROOT_DIR / "runtime" / "models" / "model_registry.json"
LEDGER_PATH = ROOT_DIR / "runtime" / "decisions" / "router_decisions.jsonl"


class IntelligenceRouter:
    def __init__(self):
        self.local_models = self._load_local_registry()

    def _load_local_registry(self) -> dict:
        if LOCAL_REGISTRY_PATH.exists():
            try:
                return json.loads(LOCAL_REGISTRY_PATH.read_text(encoding="utf-8")).get("models", {})
            except Exception:
                pass
        return {}

    def _get_last_ledger_hash(self) -> str:
        """Récupère le hash de la dernière transaction pour assurer l'immutabilité chaînée."""
        if not LEDGER_PATH.exists():
            return "0" * 64
        try:
            lines = LEDGER_PATH.read_text(encoding="utf-8").strip().splitlines()
            if not lines:
                return "0" * 64
            last_entry = json.loads(lines[-1])
            return last_entry.get("hash", "0" * 64)
        except Exception:
            return "0" * 64

    def _log_immutable_transaction(
        self, intent: str, request_id: str, candidates: list, selected: str, state: str, execution_details: dict = None
    ):
        """Journalise l'état transactionnel avec signature SHA-256 (Immutable Ledger)."""
        LEDGER_PATH.parent.mkdir(parents=True, exist_ok=True)
        previous_hash = self._get_last_ledger_hash()

        payload = {
            "timestamp": datetime.now(UTC).isoformat(),
            "request_id": request_id,
            "intent": intent,
            "candidates": candidates,
            "selected": selected,
            "transaction_state": state,  # DECISION_MADE, EXECUTION_STARTED, RECOVERY_SUCCESS, FAILED
            "execution_details": execution_details or {},
            "previous_hash": previous_hash,
        }

        # Calcul du hash immuable chaîné (SHA-256 strict avec previous_hash)
        temp_payload = dict(payload)
        temp_payload.pop("hash", None)
        raw_string = json.dumps(temp_payload, sort_keys=True, ensure_ascii=False)
        current_hash = hashlib.sha256(raw_string.encode("utf-8")).hexdigest()
        payload["hash"] = current_hash
        raw_string = json.dumps(payload, sort_keys=True, ensure_ascii=False)
        current_hash = hashlib.sha256(raw_string.encode("utf-8")).hexdigest()
        payload["hash"] = current_hash

        with open(LEDGER_PATH, "a", encoding="utf-8") as f:
            f.write(json.dumps(payload, ensure_ascii=False) + "\n")

    async def route(self, task_intent: str, prompt: str, constraints: RouteConstraints) -> ExecutionDecision:
        candidates = []
        os_mem = windows_memory.get_system_memory_pressure()

        # 1. Évaluation LOCALE (Vérification Circuit Breaker & Pression Windows)
        cb_ollama_open = circuit_breaker.is_open("ollama")

        if not cb_ollama_open:
            for model_name, meta in self.local_models.items():
                roles = meta.get("roles", [])
                if (
                    task_intent in roles
                    or (constraints.urgency == Urgency.REALTIME and "fast_chat" in roles)
                    or (constraints.require_vision and "vision" in roles)
                ):
                    required_ram = meta.get("ram_gb", 5.0)
                    state = await ollama_governor.check_model_state(model_name, required_ram)

                    # Combinaison Pression Governor + Pression Windows OS
                    high_pressure = state["high_pressure"] or os_mem["os_pressure"]

                    score = RoutingScorer.calculate_final_score(
                        capability_match=0.95 if task_intent in roles else 0.70,
                        health_status=1.0,
                        reliability=0.90,
                        latency_score=0.9 if state["is_loaded"] else 0.5,
                        cost_score=1.0,
                        confidence=1.0,
                        constraints=constraints,
                        is_local=True,
                        is_loaded_in_ram=state["is_loaded"],
                        high_ram_pressure=high_pressure,
                    )
                    candidates.append({"plane": "local", "provider": "ollama", "model": model_name, "score": score, "ram_gb": required_ram})

        # 2. Évaluation CLOUD (Vérification Circuit Breaker par provider)
        if constraints.allow_cloud and not constraints.require_privacy:
            cloud_caps = _load_capabilities()
            cloud_perf = _load_performance()
            for prov_name, meta in cloud_caps.items():
                if not meta.get("enabled", False) or circuit_breaker.is_open(prov_name):
                    continue
                roles = meta.get("roles", [])

                if (
                    task_intent in roles
                    or (constraints.urgency == Urgency.REALTIME and "fast_chat" in roles)
                    or (constraints.require_vision and "vision" in roles)
                ):
                    perf = cloud_perf.get(prov_name, {})
                    score = RoutingScorer.calculate_final_score(
                        capability_match=0.90,
                        health_status=1.0,
                        reliability=perf.get("effective_reliability", 0.5),
                        latency_score=0.8,
                        cost_score=0.9,
                        confidence=perf.get("confidence", 0.0),
                        constraints=constraints,
                        is_local=False,
                    )
                    candidates.append({"plane": "cloud", "provider": prov_name, "model": meta.get("default_model", "auto"), "score": score})

        if not candidates:
            return ExecutionDecision(
                execution_plane="cloud", provider="groq", model="llama-3.3-70b-versatile", confidence_score=0.0, reason="default_fallback"
            )

        candidates.sort(key=lambda x: x["score"], reverse=True)
        winner = candidates[0]
        request_id = str(uuid.uuid4())

        alternatives = [{"provider": c["provider"], "model": c["model"]} for c in candidates[1:3]]

        decision = ExecutionDecision(
            execution_plane=winner["plane"],
            provider=winner["provider"],
            model=winner["model"],
            confidence_score=winner["score"],
            reason=f"Top score for intent '{task_intent}'",
            metadata={
                "request_id": request_id,
                "alternatives": alternatives,
                "candidates_log": candidates[:3],
                "ram_gb": winner.get("ram_gb", 0),
            },
        )

        # Immuable Ledger : État DECISION_MADE
        self._log_immutable_transaction(
            intent=task_intent,
            request_id=request_id,
            candidates=[{"provider": c["provider"], "model": c["model"], "score": c["score"]} for c in candidates[:3]],
            selected=winner["model"],
            state="DECISION_MADE",
            execution_details={"plane": winner["plane"], "provider": winner["provider"]},
        )

        return decision

    async def execute(self, decision: ExecutionDecision, prompt: str, image_bytes: bytes = None) -> ProviderResponse:
        request_id = decision.metadata.get("request_id", "unknown")
        original_provider = decision.provider
        original_model = decision.model

        self._log_immutable_transaction(
            intent=decision.reason,
            request_id=request_id,
            candidates=decision.metadata.get("candidates_log", []),
            selected=decision.model,
            state="EXECUTION_STARTED",
            execution_details={"provider": original_provider, "model": original_model},
        )

        response = None
        fallback_triggered = False

        try:
            if decision.execution_plane == "local":
                required_ram = decision.metadata.get("ram_gb", 5.0)
                await ollama_governor.ensure_model_ready(decision.model, required_ram)

            provider_instance = get_provider_instance(decision.provider)
            if not provider_instance:
                return ProviderResponse(ok=False, provider=decision.provider, model=decision.model, error="Missing provider adapter")

            response = await provider_instance.generate(
                prompt=prompt, model=decision.model, image_bytes=image_bytes, capability=decision.reason
            )

            if response.ok:
                circuit_breaker.record_success(decision.provider)
            else:
                circuit_breaker.record_failure(decision.provider)

        except Exception as e:
            circuit_breaker.record_failure(decision.provider)
            response = ProviderResponse(ok=False, provider=decision.provider, model=decision.model, error=f"Runtime exception: {str(e)}")

        # RECOVERY TRANSCTIONNEL & CIRCUIT BREAKER
        if not response.ok:
            fallback_triggered = True
            alternatives = decision.metadata.get("alternatives", [])
            for alt in alternatives:
                alt_prov = alt["provider"]
                if circuit_breaker.is_open(alt_prov):
                    continue

                print(
                    f"[Fault Tolerant Core] Échec sur {decision.provider} -> Bascule sécurisée vers le circuit de secours {alt_prov} ({alt['model']})"
                )
                alt_instance = get_provider_instance(alt_prov)
                if not alt_instance:
                    continue

                response = await alt_instance.generate(
                    prompt=prompt, model=alt["model"], image_bytes=image_bytes, capability="fallback_recovery"
                )
                if response.ok:
                    circuit_breaker.record_success(alt_prov)
                    decision.provider = alt_prov
                    decision.model = alt["model"]

                    # Immuable Ledger : État RECOVERY_SUCCESS
                    self._log_immutable_transaction(
                        intent=decision.reason,
                        request_id=request_id,
                        candidates=decision.metadata.get("candidates_log", []),
                        selected=decision.model,
                        state="RECOVERY_SUCCESS",
                        execution_details={
                            "original_provider": original_provider,
                            "fallback_provider": alt_prov,
                            "fallback_model": alt["model"],
                        },
                    )
                    return response
                else:
                    circuit_breaker.record_failure(alt_prov)

        # Immuable Ledger : État FAILED ou fin de cycle normal
        final_state = "COMPLETED" if response.ok else "FAILED"
        self._log_immutable_transaction(
            intent=decision.reason,
            request_id=request_id,
            candidates=decision.metadata.get("candidates_log", []),
            selected=decision.model,
            state=final_state,
            execution_details={"success": response.ok, "fallback_triggered": fallback_triggered},
        )

        return response


intelligence_router = IntelligenceRouter()
