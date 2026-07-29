import os
import time
import asyncio
from pathlib import Path
import ollama

PERSONA_PATH = Path("G:/AI/E-zzio/registry/persona.txt")

os.environ["OLLAMA_NUM_GPU"] = "0"
os.environ["CUDA_VISIBLE_DEVICES"] = ""
os.environ["GGML_CUDA"] = "0"

BASE_OPTIONS = {
    "num_gpu": 0,
    "num_thread": 10,
    "top_k": 28,
    "top_p": 0.86,
    "repeat_penalty": 1.08,
}

ORGAN_OPTIONS = {
    "presence":   {"num_ctx": 2048, "num_predict": 180, "temperature": 0.42},
    "reflexe":    {"num_ctx": 1536, "num_predict": 140, "temperature": 0.28},
    "mains":      {"num_ctx": 4096, "num_predict": 420, "temperature": 0.16},
    "yeux":       {"num_ctx": 4096, "num_predict": 260, "temperature": 0.30},
    "logique":    {"num_ctx": 4096, "num_predict": 320, "temperature": 0.16},
    "intuition":  {"num_ctx": 4096, "num_predict": 360, "temperature": 0.42},
    "compagnon":  {"num_ctx": 3072, "num_predict": 320, "temperature": 0.62},
    "archiviste": {"num_ctx": 4096, "num_predict": 380, "temperature": 0.20},
    "critique":   {"num_ctx": 4096, "num_predict": 420, "temperature": 0.20},
    "profonde":   {"num_ctx": 8192, "num_predict": 900, "temperature": 0.30},
    "voix":       {"num_ctx": 4096, "num_predict": 520, "temperature": 0.62},
    "conscience": {"num_ctx": 2048, "num_predict": 220, "temperature": 0.16},
    "musique":    {"num_ctx": 4096, "num_predict": 620, "temperature": 0.76},
}

FAST_OPTIONS = {
    "num_ctx": 1536,
    "num_predict": 120,
    "temperature": 0.22,
    "top_k": 20,
    "top_p": 0.82,
}

DEEP_OPTIONS = {
    "num_ctx": 8192,
    "num_predict": 900,
    "temperature": 0.30,
}

_ollama_lock = asyncio.Semaphore(1)

def get_persona():
    try:
        return PERSONA_PATH.read_text(encoding="utf-8").strip()
    except Exception:
        return (
            "Tu es E-ZZIO, assistant local d'Enrik. "
            "Tu réponds en français, concrètement, sans blabla. "
            "Tu fonctionnes en CPU-only et tu n'utilises jamais le GPU."
        )

def build_options(organ_key="presence", speed="normal"):
    options = dict(BASE_OPTIONS)
    options.update(ORGAN_OPTIONS.get(organ_key, ORGAN_OPTIONS["presence"]))

    if speed == "fast":
        options.update(FAST_OPTIONS)
    elif speed == "deep":
        options.update(DEEP_OPTIONS)

    options["num_gpu"] = 0
    return options

def format_memory(context, speed="normal"):
    if not context:
        return ""

    max_items = 1 if speed == "fast" else 3
    max_user = 180 if speed == "fast" else 320
    max_answer = 220 if speed == "fast" else 420

    lines = []
    for item in context[-max_items:]:
        user = str(item.get("input", ""))[:max_user]
        answer = str(item.get("response", ""))[:max_answer]
        expert = str(item.get("expert", "mémoire"))
        lines.append(f"- [{expert}] U: {user}\n  R: {answer}")

    return "\n\nMémoire courte utile:\n" + "\n".join(lines)

def build_prompt(prompt, context=None, system_note=None, speed="normal"):
    persona = get_persona()
    context = context or []
    system_note = system_note or ""

    if speed == "fast":
        rules = (
            "- Réponds en 3 à 6 lignes maximum.\n"
            "- Donne directement la correction ou l'action.\n"
            "- Pas d'introduction.\n"
            "- Si la demande est du code, donne le bloc minimal fiable.\n"
        )
    elif speed == "deep":
        rules = (
            "- Analyse profondément.\n"
            "- Donne une réponse structurée, complète et exploitable.\n"
            "- Signale les risques, les limites et les tests.\n"
        )
    else:
        rules = (
            "- Réponds directement à la demande.\n"
            "- Sois précis, concret, testable.\n"
            "- Pour le code : donne du complet, adapté à Windows/PowerShell si pertinent.\n"
            "- Pour E-ZZIO : reste dans l'architecture réelle du projet.\n"
            "- Évite les architectures génériques hors sujet.\n"
        )

    return (
        f"{persona}\n\n"
        f"{system_note}\n"
        f"{format_memory(context, speed=speed)}\n\n"
        f"Règles:\n{rules}\n"
        f"Demande utilisateur:\n{prompt}\n\n"
        "Réponse E-ZZIO:"
    )

def _sync_ollama_chat(model, full_prompt, options):
    return ollama.chat(
        model=model,
        messages=[{"role": "user", "content": full_prompt}],
        options=options,
    )

async def query_model_async(
    prompt,
    model="qwen3:1.7b",
    context=None,
    system_note=None,
    organ_key="presence",
    speed="normal",
    timeout_sec=60,
):
    started = time.perf_counter()
    full_prompt = build_prompt(prompt, context=context, system_note=system_note, speed=speed)
    options = build_options(organ_key=organ_key, speed=speed)

    try:
        async with _ollama_lock:
            response = await asyncio.wait_for(
                asyncio.to_thread(_sync_ollama_chat, model, full_prompt, options),
                timeout=timeout_sec,
            )

        elapsed_ms = int((time.perf_counter() - started) * 1000)
        return {
            "ok": True,
            "model": model,
            "elapsed_ms": elapsed_ms,
            "text": response["message"]["content"],
            "timeout_sec": timeout_sec,
            "speed": speed,
        }

    except asyncio.TimeoutError:
        elapsed_ms = int((time.perf_counter() - started) * 1000)
        return {
            "ok": False,
            "model": model,
            "elapsed_ms": elapsed_ms,
            "text": f"Timeout modèle E-ZZIO ({model}) après {timeout_sec}s.",
            "timeout_sec": timeout_sec,
            "speed": speed,
        }

    except Exception as exc:
        elapsed_ms = int((time.perf_counter() - started) * 1000)
        return {
            "ok": False,
            "model": model,
            "elapsed_ms": elapsed_ms,
            "text": f"Erreur modèle E-ZZIO ({model}) : {exc}",
            "timeout_sec": timeout_sec,
            "speed": speed,
        }
