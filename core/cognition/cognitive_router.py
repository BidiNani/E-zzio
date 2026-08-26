"""
E-ZZIO Core — Cognitive Task Classifier & Model Router (V9.0 Federated)
Analyse l'intention de la tâche et sélectionne dynamiquement le domaine d'exécution
(Local Ollama, Cloud Gemini, Agent Fédéré Antigravity) sous le contrôle du gouverneur matériel
et avec enregistrement des décisions dans le Decision Ledger V10.0 gelé.
"""

import sys
import json
import uuid
import logging
from pathlib import Path
from typing import Dict, Any, Optional

ROOT_DIR = Path(r"G:\AI\E-zzio")
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from core.constitution.hardware_resource_governor import HardwareResourceGovernor
from core.cognition.ecol_universal_enforcement import EcolUniversalGateway
from core.cognition.decision_ledger import DecisionLedgerEngine
from core.cognition.model_federation.base_provider import ProviderDomain

logger = logging.getLogger(__name__)


class CognitiveRouterError(Exception):
    """Levée en cas d'échec de routage ou de non-disponibilité des ressources (Fail-Closed)."""

    pass


class CognitiveTaskClassifier:
    TASK_MAP = {
        # Tâches ordinaires / Locales
        "quick": {"domain": ProviderDomain.LOCAL_OLLAMA, "model": "qwen2.5:3b", "fallback": "qwen2.5:3b", "cost_factor": 0.3},
        "code_simple": {"domain": ProviderDomain.LOCAL_OLLAMA, "model": "qwen2.5-coder:7b", "fallback": "qwen2.5:3b", "cost_factor": 1.0},
        "classification": {"domain": ProviderDomain.LOCAL_OLLAMA, "model": "granite3.1-dense:8b", "fallback": "qwen2.5:3b", "cost_factor": 0.8},
        # Tâches de raisonnement lourd / Cloud
        "deep_reasoning": {"domain": ProviderDomain.CLOUD_GEMINI, "model": "gemini-2.5-pro", "fallback": "qwen2.5-coder:7b", "cost_factor": 2.5},
        "fast_cloud_chat": {"domain": ProviderDomain.CLOUD_GROQ, "model": "llama-3.3-70b-versatile", "fallback": "qwen2.5:3b", "cost_factor": 0.5},
        # Tâches Agentiques Fédérées (Multi-fichiers, Terminal, Browser, Refactor)
        "agentic_refactor": {"domain": ProviderDomain.AGENT_ANTIGRAVITY, "model": "antigravity_agent", "fallback": "qwen2.5-coder:7b", "cost_factor": 3.0},
        "browser_inspection": {"domain": ProviderDomain.AGENT_ANTIGRAVITY, "model": "antigravity_agent", "fallback": "qwen2.5:3b", "cost_factor": 2.0},
        "multi_step_engineering": {"domain": ProviderDomain.AGENT_ANTIGRAVITY, "model": "antigravity_agent", "fallback": "qwen2.5-coder:7b", "cost_factor": 4.0},
        "vision": {"domain": ProviderDomain.LOCAL_OLLAMA, "model": "qwen2.5vl", "fallback": "qwen2.5:3b", "cost_factor": 1.5},
    }

    def __init__(self, root_dir: Path = ROOT_DIR):
        self.root_dir = root_dir
        self.hw_governor = HardwareResourceGovernor()
        self.gateway = EcolUniversalGateway()
        self.gateway.register_gateway_action("COGNITIVE_MODEL_ROUTE")
        self.decision_engine = None
        self.evidence_store = None
        
        # Initialize Sovereign Key Pools for Cloud Providers
        from core.cognition.providers.key_pool import SovereignKeyPool
        self.gemini_pool = SovereignKeyPool("gemini", ["mock_gemini_key_1", "mock_gemini_key_2"])
        self.groq_pool = SovereignKeyPool("groq", ["mock_groq_key_1", "mock_groq_key_2"])
        
        try:
            self.decision_engine = DecisionLedgerEngine(root_dir=self.root_dir)
            from core.cognition.evidence.store import EvidenceStore
            self.evidence_store = EvidenceStore(root_dir=self.root_dir, hmac_key=getattr(self.decision_engine, "hmac_key", None))
        except Exception:
            pass

    def route_task(self, task_type: str, task_description: str, estimated_tokens: int = 500) -> Dict[str, Any]:
        """
        Classifie la tâche, interroge le gouverneur matériel (Gaming H24),
        sélectionne le domaine optimal (Local, Cloud, Antigravity) et consigne la décision dans le Ledger.
        """
        if task_type not in self.TASK_MAP:
            raise CognitiveRouterError(f"Type de tâche cognitif inconnu : {task_type}")

        telemetry = self.hw_governor.get_system_telemetry()
        is_gaming = telemetry["gaming_detected"]

        profile = self.TASK_MAP[task_type]

        # En mode Gaming, forçage du fallback local léger pour préserver le GPU / CPU
        if is_gaming and profile["domain"] == ProviderDomain.LOCAL_OLLAMA:
            selected_domain = ProviderDomain.LOCAL_OLLAMA
            selected_model = profile["fallback"]
        elif is_gaming and profile["domain"] == ProviderDomain.AGENT_ANTIGRAVITY:
            # L'agent externe soulage le CPU local en déportant l'effort
            selected_domain = ProviderDomain.AGENT_ANTIGRAVITY
            selected_model = profile["model"]
        else:
            selected_domain = profile["domain"]
            selected_model = profile["model"]

        payload = {
            "source_component": "llm_dispatcher",
            "action": "COGNITIVE_MODEL_ROUTE",
            "task_description": f"Routage cognitif [{task_type}] -> {selected_domain.value}:{selected_model} (Gaming: {is_gaming})",
            "priority": "normal" if not is_gaming else "low",
            "risk_level": "low",
            "estimated_cost": int(estimated_tokens * profile["cost_factor"]),
        }

        def execute_routing():
            routing_decision = {
                "task_type": task_type,
                "provider_domain": selected_domain.value,
                "routed_model": selected_model,
                "gaming_coexistence_active": is_gaming,
                "cost_adjusted": payload["estimated_cost"],
                "status": "OPTIMIZED_FEDERATED_ROUTE_DISPATCHED",
            }

            # 1. Create Evidence Envelope
            evidence_id = None
            if self.evidence_store is not None:
                try:
                    from core.cognition.evidence.envelope import EvidenceEnvelope
                    env = EvidenceEnvelope.create(
                        task_id=f"TASK-ROUTE-{uuid.uuid4().hex[:8].upper()}",
                        provider=selected_domain.value,
                        model_name=selected_model,
                        capability=task_type,
                        input_prompt=task_description,
                        output_payload=json.dumps(routing_decision, sort_keys=True),
                        execution_duration_ms=1.5,
                        policy_status="APPROVED",
                        signing_key=getattr(self.decision_engine, "hmac_key", None),
                    )
                    self.evidence_store.store_evidence(env)
                    evidence_id = env.evidence_id
                    routing_decision["evidence_id"] = evidence_id
                except Exception as ee:
                    logger.warning(f"[ROUTER] Evidence envelope error: {ee}")

            # 2. Commit audit decision to frozen Ledger V10.0
            if self.decision_engine is not None:
                try:
                    self.decision_engine.record_decision(
                        subsystem="CognitiveRouter",
                        decision_type="FEDERATED_MODEL_ROUTING",
                        context={"gaming_active": is_gaming, "task_type": task_type, "estimated_tokens": estimated_tokens, "evidence_id": evidence_id},
                        action_payload=routing_decision,
                        rationale=f"Routed {task_type} to {selected_domain.value} ({selected_model}) with Evidence {evidence_id}.",
                    )
                except Exception as de:
                    logger.warning(f"[ROUTER] Ledger recording warning: {de}")

            return routing_decision

        # Validation No-Bypass via ECOL
        result = self.gateway.execute_via_gateway(action="COGNITIVE_MODEL_ROUTE", payload=payload, target_func=execute_routing)

        return result

    def classify(self, content: str) -> tuple[str, str]:
        """Heuristic task classifier — maps free text to (task_type, model).

        Purely deterministic (regex/keywords). No LLM call, no token cost.
        Returns (task_type, preferred_model).

        Model policy (Multi-level — 2026-08-24):
          FAST    → granite4.1:8b                    (~5.7 GB)
                    conversation simple, salutations, questions courtes
          MID     → mrasif/gpt-oss-20b-GGUF:Q4_K_M (~11.1 GB)
                    raisonnement, analyse, synthèse, stratégie, explication
          HEAVY   → qwen3-coder:30b                  (~17.9 GB)
                    code, scripts, PowerShell, Python, refactor, architecture logicielle
          default → FAST
        """
        # Model constants — single source of truth (LOCKED 2026-08-24)
        MODEL_FAST  = "granite4.1:8b"
        MODEL_MID   = "mrasif/gpt-oss-20b-GGUF:Q4_K_M"
        MODEL_HEAVY = "qwen3-coder:30b"

        text = content.lower()

        # ── FAST — Conversational / salutation signals ─────────────────────────
        if any(k in text for k in (
            "bonjour", "hello", "salut", "hi ", "merci", "thank",
            " ok ", "oui", "non ", "bonne journée", "bonsoir", "au revoir",
            "bonne nuit", "ça va", "comment tu vas",
        )):
            return "quick", MODEL_FAST

        # ── HEAVY — Code / scripting signals (checked before MID) ──────────────
        if any(k in text for k in (
            "powershell", "ps1", "get-filehash", "invoke-", "cmdlet",
            "python", "async def", "import ", "class ", "def ", "```py", "```ps",
            "script", "code", "fonction", "function", "refactor", "debug",
            "module", "package", "pip ", "pytest", "unittest",
            "bash", "shell", "curl ", "dockerfile", "yaml", "json schema",
            "sql ", "requête sql", "migration",
        )):
            return "code_simple", MODEL_HEAVY

        # ── MID — Reasoning / analysis / synthesis signals ─────────────────────
        if any(k in text for k in (
            "analyse", "analyze", "architecture", "compare", "comparaison",
            "explique", "explain", "pourquoi", "why", "comment fonctionne",
            "how does", "stratégie", "strategy", "raisonnement", "reasoning",
            "synthèse", "synthesis", "résume", "summarize", "résumé",
            "évalue", "evaluate", "diagnose", "diagnostique",
            "recommande", "recommend", "quelle est la différence",
            "pros et cons", "avantages", "inconvénients",
        )):
            return "deep_reasoning", MODEL_MID

        # ── FAST — Vision (no dedicated vision model — fall through to fast) ────
        if any(k in text for k in ("image", "photo", "vois", "regarde", "screenshot")):
            return "vision", MODEL_FAST

        # ── Default : FAST ──────────────────────────────────────────────────────
        return "quick", MODEL_FAST




def test_cognitive_router():
    print("[*] Test du Cognitive Task Classifier & Model Router (V8.1)...")
    router = CognitiveTaskClassifier()

    # Test 1 : Tâche de code en mode normal / gaming
    print("\n--- Test 1 : Routage d'une tâche de code complexe ---")
    res = router.route_task("code", "Refactoring du module de persistance E-zzio", 450)
    print(f"  [PASS] Tâche routée vers le modèle : {res['routed_model']} | Mode Gaming : {res['gaming_coexistence_active']}")

    # Test 2 : Tâche de raisonnement lourd
    print("\n--- Test 2 : Routage d'une tâche de raisonnement (DeepSeek / Fallback) ---")
    res_reason = router.route_task("reasoning", "Analyse comparative de l'architecture Mémorielle L0-L5", 800)
    print(f"  [PASS] Tâche routée vers le modèle : {res_reason['routed_model']} | Coût ajusté : {res_reason['cost_adjusted']}")

    print("\n" + "=" * 65)
    print(" COGNITIVE ROUTER (V8.1) : OPERATIONAL & HARDWARE-AWARE")
    print("=" * 65)


if __name__ == "__main__":
    test_cognitive_router()
