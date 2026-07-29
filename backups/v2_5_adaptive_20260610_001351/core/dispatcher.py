from core.llm_engine import query_model_async
from core.memory import ezzio_memory
from core.model_registry import ORGANS, best_fast_model, all_known_models, load_latency


class EzzioDispatcher:
    def __init__(self):
        self.organs = ORGANS

    def _keyword_score(self, text, organ):
        score = 0
        hits = []

        for keyword in organ.get("keywords", []):
            if keyword in text:
                weight = 3 if " " in keyword else 1
                score += weight
                hits.append(keyword)

        if score > 0:
            score += organ.get("priority", 1)

        return score, hits

    def select_organ(self, user_input):
        text = str(user_input).lower()

        if text.startswith("/organ "):
            parts = text.split(maxsplit=2)
            if len(parts) >= 2 and parts[1] in self.organs:
                return parts[1], self.organs[parts[1]], 999, ["forced"]

        best_key = "presence"
        best_organ = self.organs["presence"]
        best_score = 0
        best_hits = []

        for key, organ in self.organs.items():
            if key == "presence":
                continue

            score, hits = self._keyword_score(text, organ)
            if score > best_score:
                best_key = key
                best_organ = organ
                best_score = score
                best_hits = hits

        return best_key, best_organ, best_score, best_hits

    def confidence(self, score):
        if score >= 15:
            return "très haute"
        if score >= 10:
            return "haute"
        if score >= 5:
            return "moyenne"
        return "par défaut"

    def auto_speed(self, text):
        lowered = str(text).lower()

        if any(word in lowered for word in ["profond", "analyse profonde", "architecture", "diagnostic long", "raisonne", "complexe"]):
            return "deep"

        if len(lowered) <= 180:
            return "fast"

        if any(word in lowered for word in ["vite", "rapide", "bref", "court", "en 5 lignes"]):
            return "fast"

        return "normal"

    def select_model_for_speed(self, organ, speed):
        if speed == "fast":
            return best_fast_model(organ.get("fast_candidates", ["qwen3:1.7b"]))
        if speed == "deep":
            return organ.get("deep_model", organ["model"])
        return organ["model"]

    def select_fallbacks_for_speed(self, organ, speed, selected_model):
        if speed == "fast":
            candidates = list(organ.get("fast_candidates", []))
            ordered = []
            for candidate in candidates:
                if candidate != selected_model and candidate not in ordered:
                    ordered.append(candidate)
            if "qwen3:1.7b" not in ordered and selected_model != "qwen3:1.7b":
                ordered.append("qwen3:1.7b")
            return ordered

        fallback = organ.get("fallback")
        return [fallback] if fallback else []

    async def route_detailed_async(self, user_input, speed="normal"):
        if speed == "auto":
            speed = self.auto_speed(user_input)

        key, organ, score, hits = self.select_organ(user_input)

        context = []
        if speed != "fast":
            context = ezzio_memory.get_context(last_n=3)

        system_note = (
            f"Organe actif : {organ['label']}.\n"
            f"Émotion : {organ['emotion']}.\n"
            f"Talent : {organ['talent']}.\n"
            "Tu es E-ZZIO, assistant local d'Enrik.\n"
            "Réponds en français.\n"
            "Sois précis, utile, humain, professionnel et concret.\n"
            "Tu dois éviter les réponses génériques hors projet.\n"
            "Tu dois répondre à la demande réelle.\n"
            "Pour le code : donne du complet, robuste, Windows/PowerShell si demandé.\n"
            "Pour FastAPI : parle de l'architecture actuelle E-ZZIO, pas d'un projet SQLAlchemy fictif.\n"
            "Tu fonctionnes en CPU-only. Ne jamais utiliser le GPU.\n"
        )

        selected_model = self.select_model_for_speed(organ, speed)
        fallback_models = self.select_fallbacks_for_speed(organ, speed, selected_model)

        if speed == "fast":
            timeout_sec = 18
        elif speed == "deep":
            timeout_sec = max(organ.get("timeout_sec", 75), 120)
        else:
            timeout_sec = organ.get("timeout_sec", 75)

        primary = await query_model_async(
            prompt=user_input,
            model=selected_model,
            context=context,
            system_note=system_note,
            organ_key=key,
            speed=speed,
            timeout_sec=timeout_sec,
        )

        used_fallback = False
        final = primary
        attempted_models = [selected_model]

        if not primary["ok"]:
            for fallback_model in fallback_models:
                used_fallback = True
                attempted_models.append(fallback_model)

                final = await query_model_async(
                    prompt=user_input,
                    model=fallback_model,
                    context=context,
                    system_note=system_note + "\nFallback activé.",
                    organ_key=key,
                    speed="fast" if speed == "fast" else speed,
                    timeout_sec=18 if speed == "fast" else min(timeout_sec, 45),
                )

                if final["ok"]:
                    break

        response_text = final["text"]

        metadata = {
            "organ_key": key,
            "organ_label": organ["label"],
            "emotion": organ["emotion"],
            "talent": organ["talent"],
            "model": final["model"],
            "selected_model": selected_model,
            "attempted_models": attempted_models,
            "primary_model": organ["model"],
            "deep_model": organ.get("deep_model"),
            "fallback_models": fallback_models,
            "used_fallback": used_fallback,
            "route_score": score,
            "route_hits": hits,
            "confidence": self.confidence(score),
            "elapsed_ms": final["elapsed_ms"],
            "speed": speed,
            "gpu_policy": "disabled_for_ezzio",
            "num_gpu": 0,
        }

        ezzio_memory.save_interaction(user_input, response_text, organ["label"], metadata=metadata)

        return {
            "response": response_text,
            "answer": response_text,
            "message": response_text,
            "content": response_text,
            "selected_organ": key,
            "organ_label": organ["label"],
            "emotion": organ["emotion"],
            "talent": organ["talent"],
            "model": final["model"],
            "selected_model": selected_model,
            "attempted_models": attempted_models,
            "primary_model": organ["model"],
            "deep_model": organ.get("deep_model"),
            "fallback_models": fallback_models,
            "used_fallback": used_fallback,
            "route_score": score,
            "route_hits": hits,
            "confidence": self.confidence(score),
            "elapsed_ms": final["elapsed_ms"],
            "speed": speed,
            "gpu_policy": "disabled_for_ezzio",
            "num_gpu": 0,
        }

    async def route_text_async(self, user_input, speed="normal"):
        detailed = await self.route_detailed_async(user_input, speed=speed)
        return detailed["response"]

    def status(self):
        safe_organs = {}
        for key, organ in self.organs.items():
            safe_organs[key] = {
                "label": organ["label"],
                "model": organ["model"],
                "fast_candidates": organ.get("fast_candidates", []),
                "best_fast_model": best_fast_model(organ.get("fast_candidates", [])),
                "deep_model": organ.get("deep_model"),
                "fallback": organ.get("fallback"),
                "emotion": organ["emotion"],
                "talent": organ["talent"],
                "priority": organ["priority"],
                "timeout_sec": organ["timeout_sec"],
            }

        return {
            "name": "E-ZZIO",
            "version": "v2.5-adaptive-nervous-system",
            "mode": "organic_moe_adaptive_fast_normal_deep",
            "gpu_policy": "disabled_for_ezzio",
            "num_gpu": 0,
            "default_speed": "auto",
            "default_model": "adaptive",
            "embedding_model": "nomic-embed-text:latest",
            "known_models": all_known_models(),
            "latency": load_latency(),
            "features": {
                "fastapi_routers": True,
                "async_chat": True,
                "auto_speed": True,
                "adaptive_fast_model": True,
                "model_latency_registry": True,
                "auto_model_switch": True,
                "fast_model_switch": True,
                "normal_model_switch": True,
                "deep_model_switch": True,
                "memory_context": True,
                "sandboxed_actions": True,
                "fallback_cascade": True,
                "route_metadata": True,
                "timeouts": True,
                "keep_alive": True,
                "cpu_only": True,
            },
            "organs": safe_organs,
        }


ezzio_dispatcher = EzzioDispatcher()
