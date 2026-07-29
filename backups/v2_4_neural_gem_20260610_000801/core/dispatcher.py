from core.llm_engine import query_model_async
from core.memory import ezzio_memory


class EzzioDispatcher:
    def __init__(self):
        self.organs = {
            "presence": {
                "label": "Présence",
                "model": "qwen3:4b",
                "fast_model": "qwen3:4b",
                "deep_model": "llama3.1:8b",
                "fallback": "mistral:7b",
                "fallback_fast": "mistral:7b",
                "emotion": "calme",
                "talent": "accueil, réponse rapide, clarification",
                "priority": 1,
                "timeout_sec": 45,
                "keywords": [],
            },
            "reflexe": {
                "label": "Réflexe",
                "model": "mistral:7b",
                "fast_model": "mistral:7b",
                "deep_model": "qwen3:4b",
                "fallback": "qwen3:4b",
                "fallback_fast": "qwen3:4b",
                "emotion": "efficacité",
                "talent": "réponse simple, fallback léger, rapidité",
                "priority": 3,
                "timeout_sec": 35,
                "keywords": ["vite", "rapide", "simple", "court", "résume", "resume", "tl;dr"],
            },
            "mains": {
                "label": "Mains",
                "model": "qwen2.5-coder:7b",
                "fast_model": "qwen3:4b",
                "deep_model": "qwen3:8b",
                "fallback": "qwen3:8b",
                "fallback_fast": "mistral:7b",
                "emotion": "maîtrise",
                "talent": "PowerShell, Python, Svelte, FastAPI, debug, architecture code",
                "priority": 10,
                "timeout_sec": 75,
                "keywords": [
                    "powershell", ".ps1", "script", "python", "code", "fastapi",
                    "svelte", "sveltekit", "bug", "erreur", "debug", "api",
                    "endpoint", "uvicorn", "backend", "frontend", "json", "fonction",
                    "classe", "patch", "corrige", "corriger", "compile", "syntaxerror",
                    "traceback", "terminal", "log", "stderr", "async", "router",
                    "routers", "asynchrone"
                ],
            },
            "yeux": {
                "label": "Yeux",
                "model": "qwen2.5vl:3b",
                "fast_model": "qwen3:4b",
                "deep_model": "qwen2.5vl:3b",
                "fallback": "qwen3:4b",
                "fallback_fast": "qwen3:4b",
                "emotion": "attention",
                "talent": "vision, captures, interfaces, analyse visuelle",
                "priority": 7,
                "timeout_sec": 55,
                "keywords": [
                    "image", "capture", "screenshot", "écran", "ecran",
                    "photo", "visuel", "interface", "voir", "regarde", "affichage"
                ],
            },
            "logique": {
                "label": "Logique",
                "model": "phi4-mini:latest",
                "fast_model": "phi4-mini:latest",
                "deep_model": "qwen3:8b",
                "fallback": "qwen3:8b",
                "fallback_fast": "qwen3:4b",
                "emotion": "précision",
                "talent": "logique, calcul, cohérence, vérification",
                "priority": 8,
                "timeout_sec": 60,
                "keywords": [
                    "logique", "calcul", "math", "précis", "precis",
                    "vérifie", "verifie", "cohérence", "coherence",
                    "preuve", "raisonnement", "exact", "comparer"
                ],
            },
            "intuition": {
                "label": "Intuition",
                "model": "llama3.1:8b",
                "fast_model": "qwen3:4b",
                "deep_model": "qwen3:8b",
                "fallback": "qwen3:8b",
                "fallback_fast": "mistral:7b",
                "emotion": "recul",
                "talent": "conseil, synthèse, stratégie, choix",
                "priority": 6,
                "timeout_sec": 65,
                "keywords": [
                    "conseil", "stratégie", "strategie", "synthèse", "synthese",
                    "plan", "choix", "avis", "orientation", "prochaine étape",
                    "prochaine etape", "quoi faire", "priorité", "priorite"
                ],
            },
            "compagnon": {
                "label": "Compagnon",
                "model": "hermes3:8b",
                "fast_model": "qwen3:4b",
                "deep_model": "llama3.1:8b",
                "fallback": "llama3.1:8b",
                "fallback_fast": "mistral:7b",
                "emotion": "chaleur",
                "talent": "conversation naturelle, présence humaine, reformulation douce",
                "priority": 4,
                "timeout_sec": 60,
                "keywords": [
                    "parle", "discussion", "ami", "compagnon", "ressenti",
                    "humain", "émotion", "emotion", "motivation", "fatigue",
                    "j'en ai marre", "stress"
                ],
            },
            "archiviste": {
                "label": "Archiviste",
                "model": "granite3.3:8b",
                "fast_model": "qwen3:4b",
                "deep_model": "granite3.3:8b",
                "fallback": "qwen3:8b",
                "fallback_fast": "mistral:7b",
                "emotion": "stabilité",
                "talent": "mémoire, documentation, classement, historique",
                "priority": 7,
                "timeout_sec": 70,
                "keywords": [
                    "mémoire", "memoire", "souvenir", "historique", "archive",
                    "document", "classe", "résume le projet", "resume le projet",
                    "handover", "passation", "sauvegarde", "backup", "tree",
                    "structure", "architecture actuelle"
                ],
            },
            "critique": {
                "label": "Regard critique",
                "model": "qwen3:8b",
                "fast_model": "qwen3:4b",
                "deep_model": "qwen3:8b",
                "fallback": "llama3.1:8b",
                "fallback_fast": "mistral:7b",
                "emotion": "exigence",
                "talent": "audit, qualité, robustesse, amélioration constructive",
                "priority": 9,
                "timeout_sec": 75,
                "keywords": [
                    "audit", "critique", "qualité", "qualite", "review",
                    "robuste", "propre", "professionnel", "améliore",
                    "ameliore", "optimise", "sécurise", "securise",
                    "ménage", "menage", "refactor", "fiabilise"
                ],
            },
            "profonde": {
                "label": "Pensée profonde",
                "model": "deepseek-r1:8b",
                "fast_model": "qwen3:4b",
                "deep_model": "deepseek-r1:8b",
                "fallback": "qwen3:8b",
                "fallback_fast": "mistral:7b",
                "emotion": "profondeur",
                "talent": "analyse complexe, architecture, diagnostic long",
                "priority": 8,
                "timeout_sec": 110,
                "keywords": [
                    "analyse profonde", "profond", "complexe", "architecture",
                    "diagnostic", "raisonne", "problème difficile",
                    "probleme difficile", "décortique", "decortique",
                    "long terme", "système", "systeme"
                ],
            },
            "voix": {
                "label": "Voix premium",
                "model": "gemma4:e4b",
                "fast_model": "qwen3:4b",
                "deep_model": "gemma4:e4b",
                "fallback": "llama3.1:8b",
                "fallback_fast": "mistral:7b",
                "emotion": "élégance",
                "talent": "style, reformulation, synthèse premium, écriture",
                "priority": 7,
                "timeout_sec": 90,
                "keywords": [
                    "réécris", "reecris", "style", "élégant", "elegant",
                    "formule", "rédige", "redige", "texte", "message",
                    "document", "premium", "mail", "lettre", "présentation",
                    "presentation"
                ],
            },
            "conscience": {
                "label": "Conscience",
                "model": "shieldgemma:2b",
                "fast_model": "shieldgemma:2b",
                "deep_model": "shieldgemma:2b",
                "fallback": "qwen3:4b",
                "fallback_fast": "qwen3:4b",
                "emotion": "prudence",
                "talent": "sécurité, garde-fou, risque, validation",
                "priority": 10,
                "timeout_sec": 45,
                "keywords": [
                    "danger", "risque", "sécurité", "securite", "safe",
                    "interdit", "prudence", "garde-fou", "permission",
                    "supprimer", "delete", "effacer", "droits", "admin"
                ],
            },
            "musique": {
                "label": "Oreille musicale",
                "model": "qwen3:8b",
                "fast_model": "qwen3:4b",
                "deep_model": "qwen3:8b",
                "fallback": "llama3.1:8b",
                "fallback_fast": "mistral:7b",
                "emotion": "énergie",
                "talent": "MAO, rock, grunge, punk, metal, paroles, structure chanson",
                "priority": 8,
                "timeout_sec": 90,
                "keywords": [
                    "musique", "mao", "riff", "midi", "wav", "rock",
                    "grunge", "punk", "metal", "paroles", "chanson",
                    "guitare", "batterie", "basse", "accords", "couplet",
                    "refrain", "solo"
                ],
            },
        }

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

    def select_model_for_speed(self, organ, speed):
        if speed == "fast":
            return organ.get("fast_model", organ["model"])
        if speed == "deep":
            return organ.get("deep_model", organ["model"])
        return organ["model"]

    def select_fallback_for_speed(self, organ, speed):
        if speed == "fast":
            return organ.get("fallback_fast", organ.get("fallback"))
        return organ.get("fallback")

    async def route_detailed_async(self, user_input, speed="normal"):
        key, organ, score, hits = self.select_organ(user_input)
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
        fallback_model = self.select_fallback_for_speed(organ, speed)

        timeout_sec = organ.get("timeout_sec", 75)
        if speed == "fast":
            timeout_sec = min(timeout_sec, 18)
        elif speed == "deep":
            timeout_sec = max(timeout_sec, 110)

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

        if not primary["ok"] and fallback_model:
            used_fallback = True
            final = await query_model_async(
                prompt=user_input,
                model=fallback_model,
                context=context,
                system_note=system_note + "\nFallback activé.",
                organ_key=key,
                speed="fast",
                timeout_sec=min(timeout_sec, 18),
            )

        response_text = final["text"]

        metadata = {
            "organ_key": key,
            "organ_label": organ["label"],
            "emotion": organ["emotion"],
            "talent": organ["talent"],
            "model": final["model"],
            "selected_model": selected_model,
            "primary_model": organ["model"],
            "fast_model": organ.get("fast_model"),
            "deep_model": organ.get("deep_model"),
            "fallback_model": fallback_model,
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
            "primary_model": organ["model"],
            "fast_model": organ.get("fast_model"),
            "deep_model": organ.get("deep_model"),
            "fallback_model": fallback_model,
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
                "fast_model": organ.get("fast_model"),
                "deep_model": organ.get("deep_model"),
                "fallback": organ.get("fallback"),
                "fallback_fast": organ.get("fallback_fast"),
                "emotion": organ["emotion"],
                "talent": organ["talent"],
                "priority": organ["priority"],
                "timeout_sec": organ["timeout_sec"],
            }

        return {
            "name": "E-ZZIO",
            "version": "v2.3.1-fast-model-routing",
            "mode": "organic_moe_async_fast_models",
            "gpu_policy": "disabled_for_ezzio",
            "num_gpu": 0,
            "default_model": "qwen3:4b",
            "embedding_model": "nomic-embed-text:latest",
            "features": {
                "fastapi_routers": True,
                "async_chat": True,
                "auto_model_switch": True,
                "fast_model_switch": True,
                "deep_model_switch": True,
                "memory_context": True,
                "sandboxed_actions": True,
                "fallback": True,
                "route_metadata": True,
                "timeouts": True,
                "cpu_only": True,
            },
            "organs": safe_organs,
        }


ezzio_dispatcher = EzzioDispatcher()
