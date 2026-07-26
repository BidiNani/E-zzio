import json
from pathlib import Path

LATENCY_PATH = Path("G:/AI/E-zzio/registry/model_latency.json")

FAST_MODEL_POOL = [
    "llama3.2:3b",
    "qwen2.5-coder:1.5b",
    "phi4-mini:latest",
]

ORGANS = {
    "presence": {
        "label": "Présence",
        "model": "llama3.2:3b",
        "fast_candidates": ["llama3.2:3b", "qwen2.5-coder:1.5b"],
        "deep_model": "hermes3:8b",
        "fallback": "llama3.2:3b",
        "emotion": "calme",
        "talent": "accueil, réponse rapide, clarification",
        "priority": 1,
        "timeout_sec": 30,
        "keywords": [],
    },
    "reflexe": {
        "label": "Réflexe",
        "model": "llama3.2:3b",
        "fast_candidates": ["llama3.2:3b", "qwen2.5-coder:1.5b"],
        "deep_model": "llama3.2:3b",
        "fallback": "qwen2.5-coder:1.5b",
        "emotion": "efficacité",
        "talent": "réponse courte, vitesse, fallback nerveux",
        "priority": 3,
        "timeout_sec": 20,
        "keywords": ["vite", "rapide", "simple", "court", "résume", "resume", "tl;dr", "bref"],
    },
    "mains": {
        "label": "Mains",
        "model": "qwen2.5-coder:7b",
        "fast_candidates": ["qwen2.5-coder:1.5b", "llama3.2:3b"],
        "deep_model": "qwen2.5-coder:7b",
        "fallback": "llama3.2:3b",
        "emotion": "maîtrise",
        "talent": "PowerShell, Python, Svelte, FastAPI, debug, architecture code",
        "priority": 10,
        "timeout_sec": 60,
        "keywords": [
            "powershell", ".ps1", "script", "python", "code", "fastapi",
            "svelte", "sveltekit", "bug", "erreur", "debug", "api",
            "endpoint", "uvicorn", "backend", "frontend", "json", "fonction",
            "classe", "patch", "corrige", "corriger", "compile", "syntaxerror",
            "traceback", "terminal", "log", "stderr", "async", "router",
            "routers", "asynchrone", "optimise", "refactor"
        ],
    },
    "compagnon": {
        "label": "Compagnon",
        "model": "hermes3:8b",
        "fast_candidates": ["llama3.2:3b", "qwen2.5-coder:1.5b"],
        "deep_model": "hermes3:8b",
        "fallback": "llama3.2:3b",
        "emotion": "chaleur",
        "talent": "conversation naturelle, présence humaine, reformulation douce",
        "priority": 4,
        "timeout_sec": 45,
        "keywords": ["parle", "discussion", "ami", "compagnon", "ressenti", "humain", "émotion", "emotion", "motivation", "fatigue", "j'en ai marre", "stress"],
    },
    "logique": {
        "label": "Logique",
        "model": "phi4-mini:latest",
        "fast_candidates": ["llama3.2:3b", "phi4-mini:latest"],
        "deep_model": "hermes3:8b",
        "fallback": "llama3.2:3b",
        "emotion": "précision",
        "talent": "logique, calcul, cohérence, vérification",
        "priority": 8,
        "timeout_sec": 45,
        "keywords": ["logique", "calcul", "math", "précis", "precis", "vérifie", "verifie", "cohérence", "coherence", "preuve", "raisonnement", "exact", "comparer"],
    }
}

def load_latency():
    if not LATENCY_PATH.exists(): return {}
    try: return json.loads(LATENCY_PATH.read_text(encoding="utf-8"))
    except: return {}

def save_latency(data):
    LATENCY_PATH.parent.mkdir(parents=True, exist_ok=True)
    LATENCY_PATH.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

def best_fast_model(candidates):
    latency = load_latency()
    valid = []
    for model in candidates:
        item = latency.get(model)
        if item and item.get("ok"): valid.append((int(item.get("elapsed_ms", 999999)), model))
        else: valid.append((999999, model))
    if not valid: return candidates[0] if candidates else "llama3.2:3b"
    valid.sort(key=lambda x: x[0])
    return valid[0][1]

def all_known_models():
    models = set(FAST_MODEL_POOL)
    for organ in ORGANS.values():
        models.add(organ["model"])
        if organ.get("deep_model"): models.add(organ.get("deep_model"))
        if organ.get("fallback"): models.add(organ.get("fallback"))
        for candidate in organ.get("fast_candidates", []): models.add(candidate)
    return sorted([m for m in models if m])