import json
from pathlib import Path

LATENCY_PATH = Path("G:/AI/E-zzio/registry/model_latency.json")

FAST_MODEL_POOL = [
    "qwen2.5-coder:1.5b",
    "qwen3:1.7b",
    "llama3.2:3b",
    "shieldgemma:2b",
    "phi4-mini:latest",
]

ORGANS = {
    "presence": {
        "label": "Présence",
        "model": "qwen3:4b",
        "fast_candidates": ["llama3.2:3b", "qwen3:1.7b"],
        "deep_model": "llama3.1:8b",
        "fallback": "qwen3:1.7b",
        "emotion": "calme",
        "talent": "accueil, réponse rapide, clarification",
        "priority": 1,
        "timeout_sec": 45,
        "keywords": [],
    },
    "reflexe": {
        "label": "Réflexe",
        "model": "qwen3:1.7b",
        "fast_candidates": ["qwen3:1.7b", "llama3.2:3b"],
        "deep_model": "qwen3:4b",
        "fallback": "llama3.2:3b",
        "emotion": "efficacité",
        "talent": "réponse courte, vitesse, fallback nerveux",
        "priority": 3,
        "timeout_sec": 25,
        "keywords": ["vite", "rapide", "simple", "court", "résume", "resume", "tl;dr", "bref"],
    },
    "mains": {
        "label": "Mains",
        "model": "qwen2.5-coder:7b",
        "fast_candidates": ["qwen2.5-coder:1.5b", "qwen3:1.7b", "llama3.2:3b"],
        "deep_model": "qwen3:8b",
        "fallback": "qwen3:8b",
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
        "fast_candidates": ["qwen3:1.7b", "llama3.2:3b"],
        "deep_model": "qwen2.5vl:3b",
        "fallback": "qwen3:4b",
        "emotion": "attention",
        "talent": "vision, captures, interfaces, analyse visuelle",
        "priority": 7,
        "timeout_sec": 55,
        "keywords": ["image", "capture", "screenshot", "écran", "ecran", "photo", "visuel", "interface", "voir", "regarde", "affichage"],
    },
    "logique": {
        "label": "Logique",
        "model": "phi4-mini:latest",
        "fast_candidates": ["qwen3:1.7b", "phi4-mini:latest"],
        "deep_model": "qwen3:8b",
        "fallback": "qwen3:8b",
        "emotion": "précision",
        "talent": "logique, calcul, cohérence, vérification",
        "priority": 8,
        "timeout_sec": 60,
        "keywords": ["logique", "calcul", "math", "précis", "precis", "vérifie", "verifie", "cohérence", "coherence", "preuve", "raisonnement", "exact", "comparer"],
    },
    "intuition": {
        "label": "Intuition",
        "model": "llama3.1:8b",
        "fast_candidates": ["llama3.2:3b", "qwen3:1.7b"],
        "deep_model": "qwen3:8b",
        "fallback": "qwen3:8b",
        "emotion": "recul",
        "talent": "conseil, synthèse, stratégie, choix",
        "priority": 6,
        "timeout_sec": 65,
        "keywords": ["conseil", "stratégie", "strategie", "synthèse", "synthese", "plan", "choix", "avis", "orientation", "prochaine étape", "prochaine etape", "quoi faire", "priorité", "priorite"],
    },
    "compagnon": {
        "label": "Compagnon",
        "model": "hermes3:8b",
        "fast_candidates": ["llama3.2:3b", "qwen3:1.7b"],
        "deep_model": "hermes3:8b",
        "fallback": "llama3.1:8b",
        "emotion": "chaleur",
        "talent": "conversation naturelle, présence humaine, reformulation douce",
        "priority": 4,
        "timeout_sec": 60,
        "keywords": ["parle", "discussion", "ami", "compagnon", "ressenti", "humain", "émotion", "emotion", "motivation", "fatigue", "j'en ai marre", "stress"],
    },
    "archiviste": {
        "label": "Archiviste",
        "model": "granite3.3:8b",
        "fast_candidates": ["llama3.2:3b", "qwen3:1.7b"],
        "deep_model": "granite3.3:8b",
        "fallback": "qwen3:8b",
        "emotion": "stabilité",
        "talent": "mémoire, documentation, classement, historique",
        "priority": 7,
        "timeout_sec": 70,
        "keywords": ["mémoire", "memoire", "souvenir", "historique", "archive", "document", "classe", "résume le projet", "resume le projet", "handover", "passation", "sauvegarde", "backup", "tree", "structure", "architecture actuelle"],
    },
    "critique": {
        "label": "Regard critique",
        "model": "qwen3:8b",
        "fast_candidates": ["qwen3:1.7b", "llama3.2:3b"],
        "deep_model": "qwen3:8b",
        "fallback": "llama3.1:8b",
        "emotion": "exigence",
        "talent": "audit, qualité, robustesse, amélioration constructive",
        "priority": 9,
        "timeout_sec": 75,
        "keywords": ["audit", "critique", "qualité", "qualite", "review", "robuste", "propre", "professionnel", "améliore", "ameliore", "optimise", "sécurise", "securise", "ménage", "menage", "refactor", "fiabilise"],
    },
    "profonde": {
        "label": "Pensée profonde",
        "model": "deepseek-r1:8b",
        "fast_candidates": ["qwen3:1.7b", "llama3.2:3b"],
        "deep_model": "deepseek-r1:8b",
        "fallback": "qwen3:8b",
        "emotion": "profondeur",
        "talent": "analyse complexe, architecture, diagnostic long",
        "priority": 8,
        "timeout_sec": 110,
        "keywords": ["analyse profonde", "profond", "complexe", "architecture", "diagnostic", "raisonne", "problème difficile", "probleme difficile", "décortique", "decortique", "long terme", "système", "systeme"],
    },
    "voix": {
        "label": "Voix premium",
        "model": "gemma4:e4b",
        "fast_candidates": ["llama3.2:3b", "qwen3:1.7b"],
        "deep_model": "gemma4:e4b",
        "fallback": "llama3.1:8b",
        "emotion": "élégance",
        "talent": "style, reformulation, synthèse premium, écriture",
        "priority": 7,
        "timeout_sec": 90,
        "keywords": ["réécris", "reecris", "style", "élégant", "elegant", "formule", "rédige", "redige", "texte", "message", "document", "premium", "mail", "lettre", "présentation", "presentation"],
    },
    "conscience": {
        "label": "Conscience",
        "model": "shieldgemma:2b",
        "fast_candidates": ["shieldgemma:2b", "qwen3:1.7b"],
        "deep_model": "shieldgemma:2b",
        "fallback": "qwen3:4b",
        "emotion": "prudence",
        "talent": "sécurité, garde-fou, risque, validation",
        "priority": 10,
        "timeout_sec": 45,
        "keywords": ["danger", "risque", "sécurité", "securite", "safe", "interdit", "prudence", "garde-fou", "permission", "supprimer", "delete", "effacer", "droits", "admin"],
    },
    "musique": {
        "label": "Oreille musicale",
        "model": "qwen3:8b",
        "fast_candidates": ["llama3.2:3b", "qwen3:1.7b"],
        "deep_model": "qwen3:8b",
        "fallback": "llama3.1:8b",
        "emotion": "énergie",
        "talent": "MAO, rock, grunge, punk, metal, paroles, structure chanson",
        "priority": 8,
        "timeout_sec": 90,
        "keywords": ["musique", "mao", "riff", "midi", "wav", "rock", "grunge", "punk", "metal", "paroles", "chanson", "guitare", "batterie", "basse", "accords", "couplet", "refrain", "solo"],
    },
}

def load_latency():
    if not LATENCY_PATH.exists():
        return {}
    try:
        return json.loads(LATENCY_PATH.read_text(encoding="utf-8"))
    except Exception:
        return {}

def save_latency(data):
    LATENCY_PATH.parent.mkdir(parents=True, exist_ok=True)
    LATENCY_PATH.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

def best_fast_model(candidates):
    latency = load_latency()
    valid = []

    for model in candidates:
        item = latency.get(model)
        if not item:
            valid.append((999999, model))
            continue
        if item.get("ok"):
            valid.append((int(item.get("elapsed_ms", 999999)), model))

    if not valid:
        return candidates[0] if candidates else "qwen3:1.7b"

    valid.sort(key=lambda x: x[0])
    return valid[0][1]

def all_known_models():
    models = set(FAST_MODEL_POOL)
    for organ in ORGANS.values():
        models.add(organ["model"])
        models.add(organ.get("deep_model"))
        models.add(organ.get("fallback"))
        for candidate in organ.get("fast_candidates", []):
            models.add(candidate)
    return sorted([m for m in models if m])
