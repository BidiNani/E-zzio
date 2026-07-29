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
    "top_k": 30,
    "top_p": 0.86,
    "repeat_penalty": 1.08,
}

ORGAN_OPTIONS = {
    "presence":   {"num_ctx": 3072, "num_predict": 220, "temperature": 0.42},
    "reflexe":    {"num_ctx": 2048, "num_predict": 180, "temperature": 0.30},
    "mains":      {"num_ctx": 6144, "num_predict": 520, "temperature": 0.18},
    "yeux":       {"num_ctx": 4096, "num_predict": 320, "temperature": 0.30},
    "logique":    {"num_ctx": 6144, "num_predict": 420, "temperature": 0.18},
    "intuition":  {"num_ctx": 4096, "num_predict": 420, "temperature": 0.45},
    "compagnon":  {"num_ctx": 3072, "num_predict": 360, "temperature": 0.62},
    "archiviste": {"num_ctx": 6144, "num_predict": 460, "temperature": 0.22},
    "critique":   {"num_ctx": 6144, "num_predict": 520, "temperature": 0.22},
    "profonde":   {"num_ctx": 8192, "num_predict": 780, "temperature": 0.30},
    "voix":       {"num_ctx": 6144, "num_predict": 650, "temperature": 0.62},
    "conscience": {"num_ctx": 3072, "num_predict": 280, "temperature": 0.18},
    "musique":    {"num_ctx": 6144, "num_predict": 760, "temperature": 0.76},
}

FAST_OVERRIDES = {
    "num_ctx": 2048,
    "num_predict": 180,
    "temperature": 0.25,
}

_ollama_lock = asyncio.Semaphore(1)

def get_persona():
    try:
        return PERSONA_PATH.read_text(encoding="utf-8").strip()
    except Exception:
        return (
            "Tu es E-ZZIO, assistant local d'Enrik. "
            "Tu réponds en français, clairement, concrètement et sans blabla. "
            "Tu fonctionnes en CPU-only et tu n'utilises jamais le GPU."
        )

def build_options(organ_key="presence", speed="normal"):
    options = dict(BASE_OPTIONS)
    options.update(ORGAN_OPTIONS.get(organ_key, ORGAN_OPTIONS["presence"]))

    if speed == "fast":
        options.update(FAST_OVERRIDES)
    elif speed == "deep":
        options["num_ctx"] = max(options.get("num_ctx", 4096), 8192)
        options["num_predict"] = max(options.get("num_predict", 500), 900)

    options["num_gpu"] = 0
    return options

def format_memory(context, max_items=3):
    if not context:
        return ""

    lines = []
    for item in context[-max_items:]:
        user = str(item.get("input", ""))[:260]
        answer = str(item.get("response", ""))[:360]
        expert = str(item.get("expert", "mémoire"))
        lines.append(f"- [{expert}] U: {user}\n  R: {answer}")

    return "\n\nMémoire courte utile:\n" + "\n".join(lines)

def build_prompt(prompt, context=None, system_note=None, speed="normal"):
    persona = get_persona()
    context = context or []
    system_note = system_note or ""

    if speed == "fast":
        response_rules = (
            "- Réponds en 3 à 8 lignes maximum.\n"
            "- Donne directement la cause et la correction.\n"
            "- Pas d'introduction longue.\n"
        )
    else:
        response_rules = (
            "- Réponds directement à la demande.\n"
            "- Sois précis, concret et testable.\n"
            "- Pour le code : donne du complet, pas des bouts abstraits.\n"
            "- Pour le diagnostic : cause, correction, test.\n"
            "- Évite les exemples génériques hors projet.\n"
        )

    return (
        f"{persona}\n\n"
        f"{system_note}\n"
        f"{format_memory(context)}\n\n"
        f"Règles:\n{response_rules}\n"
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
    model="qwen3:4b",
    context=None,
    system_note=None,
    organ_key="presence",
    speed="normal",
    timeout_sec=75,
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

def query_model(*args, **kwargs):
    return asyncio.run(query_model_async(*args, **kwargs))
