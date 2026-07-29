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
                "keywords": [],
            },
            "reflexe": {
                "label": "Réflexe",
                "model": "mistral:7b",
                "fallback": "qwen3:4b",
                "emotion": "efficacité",
                "talent": "réponse simple, fallback léger, rapidité",
                "keywords": ["vite", "rapide", "simple", "court", "résume", "resume"],
            },
            "mains": {
                "label": "Mains",
                "model": "qwen2.5-coder:7b",
                "fallback": "qwen3:8b",
                "emotion": "maîtrise",
                "talent": "PowerShell, Python, Svelte, FastAPI, debug, architecture code",
                "keywords": [
                    "powershell", ".ps1", "script", "python", "code", "fastapi",
                    "svelte", "sveltekit", "bug", "erreur", "debug", "api",
                    "endpoint", "uvicorn", "backend", "frontend", "json", "fonction",
                    "classe", "patch", "corrige", "corriger"
                ],
            },
            "yeux": {
                "label": "Yeux",
                "model": "qwen2.5vl:3b",
                "fallback": "qwen3:4b",
                "emotion": "attention",
                "talent": "vision, captures, interfaces, analyse visuelle",
                "keywords": [
                    "image", "capture", "screenshot", "écran", "ecran",
                    "photo", "visuel", "interface", "voir", "regarde"
                ],
            },
            "logique": {
                "label": "Logique",
                "model": "phi4-mini:latest",
                "fallback": "qwen3:8b",
                "emotion": "précision",
                "talent": "logique, calcul, cohérence, vérification",
                "keywords": [
                    "logique", "calcul", "math", "précis", "precis",
                    "vérifie", "verifie", "cohérence", "coherence",
                    "preuve", "raisonnement"
                ],
            },
            "intuition": {
                "label": "Intuition",
                "model": "llama3.1:8b",
                "fallback": "qwen3:8b",
                "emotion": "recul",
                "talent": "conseil, synthèse, stratégie, choix",
                "keywords": [
                    "conseil", "stratégie", "strategie", "synthèse", "synthese",
                    "plan", "choix", "avis", "orientation", "prochaine étape",
                    "prochaine etape"
                ],
            },
            "compagnon": {
                "label": "Compagnon",
                "model": "hermes3:8b",
                "fallback": "llama3.1:8b",
                "emotion": "chaleur",
                "talent": "conversation naturelle, présence humaine, reformulation douce",
                "keywords": [
                    "parle", "discussion", "ami", "compagnon", "ressenti",
                    "humain", "émotion", "emotion", "motivation"
                ],
            },
            "archiviste": {
                "label": "Archiviste",
                "model": "granite3.3:8b",
                "fallback": "qwen3:8b",
                "emotion": "stabilité",
                "talent": "mémoire, documentation, classement, historique",
                "keywords": [
                    "mémoire", "memoire", "souvenir", "historique", "archive",
                    "document", "classe", "résume le projet", "resume le projet",
                    "handover", "passation"
                ],
            },
            "critique": {
                "label": "Regard critique",
                "model": "qwen3:8b",
                "fallback": "llama3.1:8b",
                "emotion": "exigence",
                "talent": "audit, qualité, robustesse, amélioration constructive",
                "keywords": [
                    "audit", "critique", "qualité", "qualite", "review",
                    "robuste", "propre", "professionnel", "améliore",
                    "ameliore", "optimise", "sécurise", "securise"
                ],
            },
            "profonde": {
                "label": "Pensée profonde",
                "model": "deepseek-r1:8b",
                "fallback": "qwen3:8b",
                "emotion": "profondeur",
                "talent": "analyse complexe, architecture, diagnostic long",
                "keywords": [
                    "analyse profonde", "profond", "complexe", "architecture",
                    "diagnostic", "raisonne", "problème difficile",
                    "probleme difficile", "décortique", "decortique"
                ],
            },
            "voix": {
                "label": "Voix premium",
                "model": "gemma4:e4b",
                "fallback": "llama3.1:8b",
                "emotion": "élégance",
                "talent": "style, reformulation, synthèse premium, écriture",
                "keywords": [
                    "réécris", "reecris", "style", "élégant", "elegant",
                    "formule", "rédige", "redige", "texte", "message",
                    "document", "premium"
                ],
            },
            "conscience": {
                "label": "Conscience",
                "model": "shieldgemma:2b",
                "fallback": "qwen3:4b",
                "emotion": "prudence",
                "talent": "sécurité, garde-fou, risque, validation",
                "keywords": [
                    "danger", "risque", "sécurité", "securite", "safe",
                    "interdit", "prudence", "garde-fou", "permission"
                ],
            },
            "musique": {
                "label": "Oreille musicale",
                "model": "qwen3:8b",
                "fallback": "llama3.1:8b",
                "emotion": "énergie",
                "talent": "MAO, rock, grunge, punk, metal, paroles, structure chanson",
                "keywords": [
                    "musique", "mao", "riff", "midi", "wav", "rock",
                    "grunge", "punk", "metal", "paroles", "chanson",
                    "guitare", "batterie", "basse"
                ],
            },
        }

    def select_organ(self, user_input):
        text = str(user_input).lower()

        for key, organ in self.organs.items():
            if key == "presence":
                continue
            if any(keyword in text for keyword in organ["keywords"]):
                return key, organ

        return "presence", self.organs["presence"]

    def route(self, user_input):
        key, organ = self.select_organ(user_input)
        context = ezzio_memory.get_context(last_n=5)

        system_note = (
            f"Organe actif : {organ['label']}.\n"
            f"Émotion : {organ['emotion']}.\n"
            f"Talent : {organ['talent']}.\n"
            "Tu es E-ZZIO, assistant local d'Enrik.\n"
            "Réponds en français.\n"
            "Sois clair, utile, humain, professionnel et concret.\n"
            "Ne mentionne pas inutilement la mécanique interne.\n"
            "Tu fonctionnes en CPU-only. Ne jamais utiliser le GPU.\n"
        )

        response = query_model(
            prompt=user_input,
            model=organ["model"],
            context=context,
            system_note=system_note,
        )

        if response.startswith("Erreur modèle E-ZZIO") and organ.get("fallback"):
            response = query_model(
                prompt=user_input,
                model=organ["fallback"],
                context=context,
                system_note=system_note + "\nFallback activé.",
            )

        ezzio_memory.save_interaction(user_input, response, organ["label"])
        return response

    def status(self):
        safe_organs = {}
        for key, organ in self.organs.items():
            safe_organs[key] = {
                "label": organ["label"],
                "model": organ["model"],
                "fallback": organ["fallback"],
                "emotion": organ["emotion"],
                "talent": organ["talent"],
            }

        return {
            "name": "E-ZZIO",
            "version": "v2-moe-light-installed-models",
            "mode": "organic_moe_light",
            "gpu_policy": "disabled_for_ezzio",
            "num_gpu": 0,
            "default_model": "qwen3:4b",
            "embedding_model": "nomic-embed-text:latest",
            "organs": safe_organs,
        }

ezzio_dispatcher = EzzioDispatcher()
