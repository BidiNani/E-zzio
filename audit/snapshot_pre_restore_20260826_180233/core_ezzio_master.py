"""E-ZZIO Master Orchestrator — Architecture Hybride Gouvernée v4.1.0."""
from __future__ import annotations
from typing import Any, Dict
from core.memory_vault import check_memory_intent
from core.dispatcher import ezzio_dispatcher
from core.memory import ezzio_memory
from core import safe_actions
from core.cloud_brain_broker import cloud_chat


class EzzioMasterOrchestrator:
    def __init__(self) -> None:
        self.dispatcher = ezzio_dispatcher
        self.memory = ezzio_memory
        self.ledger = safe_actions.ledger

    async def execute_intent(
        self,
        user_prompt: str,
        speed: str = "auto",
        force_cloud: bool = False,
        session_id: str = "",
        system_prompt: str = ""
    ) -> Dict[str, Any]:
        # 1. Mémoire déterministe SQLite prioritaire
        vault_res = check_memory_intent(user_prompt)
        if vault_res:
            return {
                "organ": "memory_vault",
                "source": "Deterministic SQLite",
                "response": {"response": vault_res, "text": vault_res, "model": "sqlite_vault", "elapsed_ms": 1},
                "ok": True,
                "used_fallback": False,
            }

        # 2. Analyse d'organe et sélection de modèle
        organ_key, organ_info, score, hits = self.dispatcher.select_organ(user_prompt)
        selected_model = self.dispatcher.select_model_for_speed(organ_info, speed)

        # 3. Arbitrage Hybride : Cloud si forcé ou tâche complexe de code / raisonnement lourd
        use_cloud = force_cloud or (organ_info.get("priority", 1) >= 8 and "code" in user_prompt.lower())

        if use_cloud:
            cloud_result = await self.dispatcher.route_detailed_async(
                text=user_prompt,
                speed=speed,
                session_id=session_id,
                system_prompt=system_prompt,
                force_cloud=True,
            )

            if not isinstance(cloud_result, dict) or cloud_result.get("ok") is False:
                # Repli local CPU maîtrisé si indisponibilité cloud
                local_res = await self.dispatcher.route_detailed_async(
                    text=user_prompt,
                    speed=speed,
                    session_id=session_id,
                    system_prompt=system_prompt,
                    force_cloud=False
                )
                return {
                    "organ": organ_key,
                    "source": f"Ollama Local (Fallback CPU - {selected_model})",
                    "response": local_res.get("response") if isinstance(local_res, dict) else str(local_res),
                    "model": selected_model,
                    "selected_model": selected_model,
                    "route_score": score,
                    "route_hits": ["cloud_failover_to_local"],
                    "ok": True,
                    "used_fallback": True,
                }

            response_text = (
                cloud_result.get("response")
                or cloud_result.get("answer")
                or cloud_result.get("message")
                or str(cloud_result)
            )
            return {
                "organ": organ_key,
                "source": "Gemini Cloud — Super Cerveau",
                "response": response_text,
                "model": cloud_result.get("model", selected_model),
                "selected_model": selected_model,
                "route_score": score,
                "route_hits": hits,
                "ok": True,
                "used_fallback": False,
                "cloud_result": cloud_result,
            }
        else:
            # Traitement local rapide sur CPU Ryzen 9
            local_res = await self.dispatcher.route_detailed_async(
                text=user_prompt,
                speed=speed,
                session_id=session_id,
                system_prompt=system_prompt,
                force_cloud=False
            )
            response_text = local_res.get("response") if isinstance(local_res, dict) else str(local_res)
            return {
                "organ": organ_key,
                "source": f"Ollama Local (Ryzen 9 CPU - {selected_model})",
                "response": response_text,
                "model": selected_model,
                "selected_model": selected_model,
                "route_score": score,
                "route_hits": ["local_ryzen9_fastpath"],
                "ok": True,
                "used_fallback": False,
            }


ezzio_master = EzzioMasterOrchestrator()
