from core.llm_engine import query_model
from core.memory import ezzio_memory

class EzzioDispatcher:
    def __init__(self):
        self.organs = {
            "presence": {
                "label": "Présence",
                "model": "qwen3:4b",
                "fallback": "mistral:7b",
                "emotion": "calme",
                "talent": "accueil, réponse rapide, clarification",
                "priority": 1,
                "keywords": [],
            },
            "reflexe": {
                "label": "Réflexe",
                "model": "mistral:7b",
                "fallback": "qwen3:4b",
                "emotion": "efficacité",
                "talent": "réponse simple, fallback léger, rapidité",
                "priority": 3,
                "keywords": ["vite", "rapide", "simple", "court", "résume", "resume", "tl;dr"],
            },
            "mains": {
                "label": "Mains",
                "model": "qwen2.5-coder:7b",
                "fallback": "qwen3:8b",
                "emotion": "maîtrise",
                "talent": "PowerShell, Python, Svelte, FastAPI, debug, architecture code",
                "priority": 10,
                "keywords": [
                    "powershell", ".ps1", "script", "python", "code", "fastapi",
                    "svelte", "sveltekit", "bug", "erreur", "debug", "api",
                    "endpoint", "uvicorn", "backend", "frontend", "json", "fonction",
                    "classe", "patch", "corrige", "corriger", "compile", "syntaxerror",
                    "traceback", "terminal", "log", "stderr"
                ],
            },
            "yeux": {
                "label": "Yeux",
                "model": "qwen2.5vl:3b",
                "fallback": "qwen3:4b",
                "emotion": "attention",
                "talent": "vision, captures, interfaces, analyse visuelle",
                "priority": 7,
                "keywords": [
                    "image", "capture", "screenshot", "écran", "ecran",
                    "photo", "visuel", "interface", "voir", "regarde", "affichage"
                ],
            },
            "logique": {
                "label": "Logique",
                "model": "phi4-mini:latest",
                "fallback": "qwen3:8b",
                "emotion": "précision",
                "talent": "logique, calcul, cohérence, vérification",
                "priority": 8,
                "keywords": [
                    "logique", "calcul", "math", "précis", "precis",
                    "vérifie", "verifie", "cohérence", "coherence",
                    "preuve", "raisonnement", "exact", "comparer"
                ],
            },
            "intuition": {
                "label": "Intuition",
                "model": "llama3.1:8b",
                "fallback": "qwen3:8b",
                "emotion": "recul",
                "talent": "conseil, synthèse, stratégie, choix",
                "priority": 6,
                "keywords": [
                    "conseil", "stratégie", "strategie", "synthèse", "synthese",
                    "plan", "choix", "avis", "orientation", "prochaine étape",
                    "prochaine etape", "quoi faire", "priorité", "priorite"
                ],
            },
            "compagnon": {
                "label": "Compagnon",
                "model": "hermes3:8b",
                "fallback": "llama3.1:8b",
                "emotion": "chaleur",
                "talent": "conversation naturelle, présence humaine, reformulation douce",
                "priority": 4,
                "keywords": [
                    "parle", "discussion", "ami", "compagnon", "ressenti",
                    "humain", "émotion", "emotion", "motivation", "fatigue",
                    "j'en ai marre", "stress"
                ],
            },
            "archiviste": {
                "label": "Archiviste",
                "model": "granite3.3:8b",
                "fallback": "qwen3:8b",
                "emotion": "stabilité",
                "talent": "mémoire, documentation, classement, historique",
                "priority": 7,
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
                "fallback": "llama3.1:8b",
                "emotion": "exigence",
                "talent": "audit, qualité, robustesse, amélioration constructive",
                "priority": 9,
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
                "fallback": "qwen3:8b",
                "emotion": "profondeur",
                "talent": "analyse complexe, architecture, diagnostic long",
                "priority": 8,
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
                "fallback": "llama3.1:8b",
                "emotion": "élégance",
                "talent": "style, reformulation, synthèse premium, écriture",
                "priority": 7,
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
                "fallback": "qwen3:4b",
                "emotion": "prudence",
                "talent": "sécurité, garde-fou, risque, validation",
                "priority": 10,
                "keywords": [
                    "danger", "risque", "sécurité", "securite", "safe",
                    "interdit", "prudence", "garde-fou", "permission",
                    "supprimer", "delete", "effacer", "droits", "admin"
                ],
            },
            "musique": {
                "label": "Oreille musicale",
                "model": "qwen3:8b",
                "fallback": "llama3.1:8b",
                "emotion": "énergie",
                "talent": "MAO, rock, grunge, punk, metal, paroles, structure chanson",
                "priority": 8,
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

        # Commande manuelle utile pour debug : /organ mains ta demande
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

    def route_detailed(self, user_input):
        key, organ, score, hits = self.select_organ(user_input)
        context = ezzio_memory.get_context(last_n=5)

        system_note = (
            f"Organe actif : {organ['label']}.\n"
            f"Émotion : {organ['emotion']}.\n"
            f"Talent : {organ['talent']}.\n"
            "Tu es E-ZZIO, assistant local d'Enrik.\n"
            "Réponds en français.\n"
            "Sois précis, utile, humain, professionnel et concret.\n"
            "Pour le code : donne des blocs complets et testables.\n"
            "Pour le diagnostic : donne la cause, la correction et le test.\n"
            "Pour la création : propose une version exploitable directement.\n"
            "Ne mentionne pas inutilement la mécanique interne.\n"
            "Tu fonctionnes en CPU-only. Ne jamais utiliser le GPU.\n"
        )

        primary = query_model(
            prompt=user_input,
            model=organ["model"],
            context=context,
            system_note=system_note,
            organ_key=key,
        )

        used_fallback = False
        final = primary

        if not primary["ok"] and organ.get("fallback"):
            used_fallback = True
            final = query_model(
                prompt=user_input,
                model=organ["fallback"],
                context=context,
                system_note=system_note + "\nFallback activé.",
                organ_key=key,
            )

        response_text = final["text"]

        metadata = {
            "organ_key": key,
            "organ_label": organ["label"],
            "emotion": organ["emotion"],
            "talent": organ["talent"],
            "model": final["model"],
            "primary_model": organ["model"],
            "fallback_model": organ.get("fallback"),
            "used_fallback": used_fallback,
            "route_score": score,
            "route_hits": hits,
            "elapsed_ms": final["elapsed_ms"],
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
            "primary_model": organ["model"],
            "fallback_model": organ.get("fallback"),
            "used_fallback": used_fallback,
            "route_score": score,
            "route_hits": hits,
            "elapsed_ms": final["elapsed_ms"],
            "gpu_policy": "disabled_for_ezzio",
            "num_gpu": 0,
        }

    def route(self, user_input):
        return self.route_detailed(user_input)["response"]

    def status(self):
        safe_organs = {}
        for key, organ in self.organs.items():
            safe_organs[key] = {
                "label": organ["label"],
                "model": organ["model"],
                "fallback": organ["fallback"],
                "emotion": organ["emotion"],
                "talent": organ["talent"],
                "priority": organ["priority"],
            }

        return {
            "name": "E-ZZIO",
            "version": "v2.2-pro-moe-fast",
            "mode": "organic_moe_light_precise",
            "gpu_policy": "disabled_for_ezzio",
            "num_gpu": 0,
            "default_model": "qwen3:4b",
            "embedding_model": "nomic-embed-text:latest",
            "features": {
                "auto_model_switch": True,
                "memory_context": True,
                "sandboxed_actions": True,
                "fallback": True,
                "route_metadata": True,
                "cpu_only": True,
            },
            "organs": safe_organs,
        }

ezzio_dispatcher = EzzioDispatcher()
