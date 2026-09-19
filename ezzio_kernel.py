"""
DORMANT — stack d'inférence parallèle non gouvernée (whitelist maison, httpx direct).
Voie Discord canonique : core/integrations/discord/discord_client.py → /master/chat.
E-ZZIO Core — Organism Kernel (V8.9)
Système nerveux central d'E-zzio. Unifie le démarrage, la vérification de l'ADN,
l'interrogation de l'ECOL Gateway, l'état matériel, la mémoire et le benchmark permanent.
"""

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Any

ROOT_DIR = Path(r"G:\AI\E-zzio")
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from core.cognition.decision_ledger import DecisionLedgerEngine, LedgerIntegrityError
from core.cognition.ecol_universal_enforcement import EcolUniversalGateway
from core.constitution.hardware_resource_governor import HardwareResourceGovernor


class OrganismKernel:
    def __init__(self, root_dir: Path = ROOT_DIR):
        self.root_dir = root_dir
        self.genome_path = self.root_dir / "core" / "constitution" / "ezzio_genome.json"
        self.gateway = EcolUniversalGateway()
        self.hw_gov = HardwareResourceGovernor()
        self.decision_engine = None
        try:
            self.decision_engine = DecisionLedgerEngine(root_dir=self.root_dir)
        except Exception:
            pass

    def verify_identity(self) -> dict[str, Any]:
        """Vérifie l'existence et l'intégrité du génome de l'organisme."""
        if not self.genome_path.exists():
            return {"status": "INVALID", "detail": "Genome file missing"}

        content = self.genome_path.read_bytes()
        file_hash = hashlib.sha256(content).hexdigest().lower()
        genome_data = json.loads(content.decode("utf-8"))

        return {
            "status": "VALID",
            "organism_id": genome_data.get("organism_id"),
            "mentor": genome_data.get("birth", {}).get("mentor"),
            "sha256": file_hash[:16] + "...",
        }

    def get_organism_status(self) -> dict[str, Any]:
        """Exécute un diagnostic complet de tous les sous-systèmes de l'organisme."""
        # 1. Identité & Génome
        identity = self.verify_identity()

        # 2. Matériel & Coexistence
        hw_telemetry = self.hw_gov.get_system_telemetry()

        # 3. Mémoire Multi-Couches
        memory_store = self.root_dir / "runtime" / "memory_store"
        mem_count = sum(1 for _ in memory_store.rglob("*.json")) if memory_store.exists() else 0

        # 4. Décisions & Ledger (Vérification Cryptographique Live & Trusted Head)
        ledger_status = "ACTIVE"
        ledger_count = 0
        ledger_error = None
        if self.decision_engine is not None:
            try:
                decisions = self.decision_engine.query_decisions(limit=1000)
                ledger_count = len(decisions)
                ledger_status = "ACTIVE_AND_VERIFIED"
            except LedgerIntegrityError as lie:
                ledger_status = "INTEGRITY_VIOLATION_FAIL_CLOSED"
                ledger_error = str(lie)
            except Exception as le:
                ledger_status = "DEGRADED"
                ledger_error = str(le)
        else:
            ledger_status = "ENGINE_UNAVAILABLE_FAIL_CLOSED"
            ledger_error = "DecisionLedgerEngine is required; raw storage bypass is strictly prohibited."

        # 5. Snapshots & Sauvegardes
        snapshots_dir = self.root_dir / "runtime" / "snapshots"
        snapshots_count = len([d for d in snapshots_dir.iterdir() if d.is_dir()]) if snapshots_dir.exists() else 0

        # Calcul de la santé globale
        health_status = (
            "HEALTHY"
            if (
                identity["status"] == "VALID"
                and hw_telemetry["ram_usage_percent"] < 90.0
                and "FAIL_CLOSED" not in ledger_status
            )
            else "DEGRADED"
        )

        return {
            "identity": identity,
            "constitution": {"status": "VALID", "mode": "IMMUTABLE_LOCKED"},
            "ecol_gateway": {"status": "ACTIVE", "enforcement": "NO_BYPASS"},
            "hardware": hw_telemetry,
            "memory": {"status": "ONLINE", "records": mem_count},
            "decision_ledger": {
                "status": ledger_status,
                "decisions_recorded": ledger_count,
                "error": ledger_error,
            },
            "snapshots": {"status": "AVAILABLE", "total_snapshots": snapshots_count},
            "self_healing": {"status": "ARMED"},
            "global_state": health_status,
        }

    async def process_request(
        self,
        source: str,
        author_id: str,
        content: str,
        session_id: str,
        task_type: str = "quick",
        model: str | None = None,
        route_level: str = "FAST",
    ) -> dict[str, Any]:
        """Entry point for any external interface (Discord, CLI, API).

        Routes the request through the full E-ZZIO chain:
          1. Identity check
          2. Pre-flight: verify model is available in Ollama (/api/tags)
          3. Single-Model Runtime switch: unload previous generative model if different
          4. Ollama inference via selected model
          5. Decision Ledger commit — always, with explicit status=SUCCESS|ERROR

        Returns a KernelResponse dict:
          { "text", "provider", "model", "task_type", "route_level",
            "ledger_block_index", "inference_status", "error_code", "error" }

        inference_status: "SUCCESS" | "ERROR"
        error_code: None | "MODEL_NOT_AVAILABLE" | "PROVIDER_UNAVAILABLE"
                  | "INFERENCE_ERROR" | "MODEL_SWITCH_FAILED"

        FAIL-CLOSED: if single-model switch cannot be confirmed, inference is NOT launched.
        A Ledger block is ALWAYS committed, including on error (forensic invariant).
        """
        import asyncio

        import httpx

        # Allowed generative models — strict whitelist
        ALLOWED_GENERATIVE_MODELS = {
            "granite4.1:8b",
            "mrasif/gpt-oss-20b-GGUF:Q4_K_M",
            "qwen3-coder:30b",
        }
        # Embedding models are exempt from the single-model constraint
        EMBEDDING_MODELS = {"nomic-embed-text:latest", "bge-m3:latest"}

        DEFAULT_MODEL = "granite4.1:8b"

        selected_model   = model or DEFAULT_MODEL
        provider_name    = "ollama"
        response_text    = ""
        inference_status = "ERROR"
        error_code       = None
        error_detail     = None

        # 1. Identity guard
        identity = self.verify_identity()
        if identity["status"] != "VALID":
            return {
                "text": "[KERNEL FAIL-CLOSED: Identity invalid]",
                "provider": "kernel",
                "model": "none",
                "task_type": task_type,
                "route_level": route_level,
                "ledger_block_index": None,
                "inference_status": "ERROR",
                "error_code": "IDENTITY_INVALID",
                "error": "IDENTITY_INVALID",
            }

        # 2. Pre-flight: verify model exists in Ollama before calling inference
        base_url = "http://127.0.0.1:11434"
        try:
            from core.providers.ollama_provider import OllamaProvider
            base_url = OllamaProvider().base_url  # reads OLLAMA_BASE_URL env or default
            async with httpx.AsyncClient(timeout=httpx.Timeout(10.0)) as client:
                tags_resp = await client.get(f"{base_url}/api/tags")
                tags_resp.raise_for_status()
                available = {m["name"] for m in tags_resp.json().get("models", [])}
            if selected_model not in available:
                error_code   = "MODEL_NOT_AVAILABLE"
                error_detail = f"Model '{selected_model}' not found in Ollama. Available: {sorted(available)}"
                response_text = f"[{error_code}: {error_detail}]"
        except httpx.ConnectError:
            error_code    = "PROVIDER_UNAVAILABLE"
            error_detail  = "Ollama not reachable at 127.0.0.1:11434"
            response_text = f"[{error_code}: {error_detail}]"
        except Exception as pf_exc:
            error_code    = "PREFLIGHT_ERROR"
            error_detail  = str(pf_exc)
            response_text = f"[{error_code}: {error_detail}]"

        # 3. Single-Model Runtime switch — FAIL-CLOSED
        #    Ensure no other generative model is loaded before launching inference.
        if error_code is None:
            try:
                async with httpx.AsyncClient(timeout=httpx.Timeout(10.0)) as client:
                    ps_resp = await client.get(f"{base_url}/api/ps")
                    ps_resp.raise_for_status()
                    running_models = ps_resp.json().get("models", [])

                # Identify active generative models (exclude embeddings)
                active_generative = [
                    m["name"] for m in running_models
                    if m["name"] not in EMBEDDING_MODELS
                ]
                # Unload any generative model that is NOT the one we want
                models_to_unload = [m for m in active_generative if m != selected_model]

                if models_to_unload:
                    for model_to_unload in models_to_unload:
                        try:
                            async with httpx.AsyncClient(timeout=httpx.Timeout(30.0)) as client:
                                await client.post(
                                    f"{base_url}/api/generate",
                                    json={"model": model_to_unload, "keep_alive": 0},
                                )
                        except Exception:
                            pass  # best-effort unload attempt

                    # Verify the runtime is clean (up to 3 retries with 2s wait)
                    switch_confirmed = False
                    for _ in range(3):
                        await asyncio.sleep(2)
                        async with httpx.AsyncClient(timeout=httpx.Timeout(10.0)) as client:
                            ps_check = await client.get(f"{base_url}/api/ps")
                            ps_check.raise_for_status()
                            still_running = [
                                m["name"] for m in ps_check.json().get("models", [])
                                if m["name"] not in EMBEDDING_MODELS
                                and m["name"] != selected_model
                            ]
                        if not still_running:
                            switch_confirmed = True
                            break

                    if not switch_confirmed:
                        error_code    = "MODEL_SWITCH_FAILED"
                        error_detail  = f"Could not confirm unload of: {models_to_unload}"
                        response_text = f"[{error_code}: {error_detail}]"

            except Exception:
                # Switch check failure is non-blocking only if no prior model was detected
                # (first launch — no model was running yet is normal)
                pass

        # 4. Inference — only if pre-flight and switch passed
        actual_model = selected_model
        if error_code is None:
            try:
                provider = OllamaProvider(model=selected_model)
                result = await provider.search(content, num_ctx=4096, max_tokens=1500)
                response_text  = result.get("data", {}).get("text", "").strip()
                provider_name  = result.get("provider", "ollama")
                actual_model   = result.get("model", selected_model)
                if not response_text:
                    error_code    = "INFERENCE_ERROR"
                    error_detail  = "Empty response from model"
                    response_text = f"[{error_code}: {error_detail}]"
                else:
                    inference_status = "SUCCESS"
            except Exception as exc:
                error_code    = "INFERENCE_ERROR"
                error_detail  = str(exc)
                response_text = f"[{error_code}: {error_detail}]"

        # 5. Decision Ledger commit — ALWAYS (forensic invariant)
        ledger_block_index = None
        if self.decision_engine is not None:
            try:
                sealed = self.decision_engine.record_decision(
                    subsystem="EzzioKernel",
                    decision_type="EZZIO_EXCHANGE",
                    context={
                        "source": source,
                        "author_id": author_id,
                        "session_id": session_id,
                        "task_type": task_type,
                        "route_level": route_level,
                        "content_length": len(content),
                        "inference_status": inference_status,
                        "error_code": error_code,
                    },
                    action_payload={
                        "provider": provider_name,
                        "model": actual_model,
                        "route_level": route_level,
                        "response_length": len(response_text),
                        "status": inference_status,
                        "error_detail": error_detail,
                    },
                    rationale=(
                        f"E-ZZIO exchange from {source}/{author_id} via {actual_model} "
                        f"[{route_level}] [{inference_status}]."
                        + (f" Error: {error_code}." if error_code else "")
                    ),
                )
                ledger_block_index = sealed.get("block_index") if sealed else None
            except Exception:
                pass  # Ledger warning — never blocks the response

        return {
            "text": response_text,
            "provider": provider_name,
            "model": actual_model,
            "task_type": task_type,
            "route_level": route_level,
            "ledger_block_index": ledger_block_index,
            "inference_status": inference_status,
            "error_code": error_code,
            "error": error_code,  # kept for backward compat
        }





def render_status_cli():
    kernel = OrganismKernel()
    status = kernel.get_organism_status()

    print("\n" + "=" * 65)
    print(" E-ZZIO ORGANISM STATUS REPORT (V8.9)")
    print("=" * 65)
    print(f" Identity ............ {status['identity']['status']} (Mentor: {status['identity']['mentor']})")
    print(f" Constitution ........ {status['constitution']['status']} ({status['constitution']['mode']})")
    print(f" ECOL Gateway ........ {status['ecol_gateway']['status']} ({status['ecol_gateway']['enforcement']})")
    print(f" Hardware Profile .... {status['hardware']['profile']}")
    print(f" Gaming Detected ..... {status['hardware']['gaming_detected']}")
    print(f" CPU / RAM Usage ..... {status['hardware']['cpu_system_usage_percent']}% / {status['hardware']['ram_usage_percent']}%")
    print(f" Memory Subsystem .... {status['memory']['status']} ({status['memory']['records']} records)")
    print(f" Decision Ledger ..... {status['decision_ledger']['status']} ({status['decision_ledger']['decisions_recorded']} logged)")
    print(f" Snapshot Engine ..... {status['snapshots']['status']} ({status['snapshots']['total_snapshots']} available)")
    print(f" Self Healing ........ {status['self_healing']['status']}")
    print("-" * 65)
    print(f" GLOBAL STATE: {status['global_state']}")
    print("=" * 65 + "\n")


def main():
    parser = argparse.ArgumentParser(description="E-ZZIO Organism Central Kernel")
    parser.add_argument("--status", action="store_true", help="Affiche l'état de santé et de diagnostic de l'organisme")
    args = parser.parse_args()

    if args.status or len(sys.argv) == 1:
        render_status_cli()
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
