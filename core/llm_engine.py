from core.identity.canonical_identity import CanonicalIdentity
import os
import time
import asyncio
import re
from pathlib import Path
import ollama

PERSONA_PATH = Path("G:/AI/E-zzio/registry/persona.txt")

os.environ["OLLAMA_NUM_GPU"] = "0"
os.environ["CUDA_VISIBLE_DEVICES"] = ""
os.environ["GGML_CUDA"] = "0"

BASE_OPTIONS = {"num_gpu": 0, "num_thread": 10, "top_k": 24, "top_p": 0.84, "repeat_penalty": 1.08}

# J'ai légèrement augmenté les num_predict pour éviter qu'il ne coupe ses phrases
ORGAN_OPTIONS = {
    "presence": {"num_ctx": 2048, "num_predict": 250, "temperature": 0.42},
    "reflexe": {"num_ctx": 1536, "num_predict": 150, "temperature": 0.26},
    "mains": {"num_ctx": 3072, "num_predict": 400, "temperature": 0.16},
    "yeux": {"num_ctx": 3072, "num_predict": 300, "temperature": 0.30},
    "logique": {"num_ctx": 3072, "num_predict": 300, "temperature": 0.16},
    "intuition": {"num_ctx": 3072, "num_predict": 350, "temperature": 0.42},
    "compagnon": {"num_ctx": 2048, "num_predict": 350, "temperature": 0.62},
    "archiviste": {"num_ctx": 3072, "num_predict": 400, "temperature": 0.20},
    "critique": {"num_ctx": 4096, "num_predict": 400, "temperature": 0.20},
    "profonde": {"num_ctx": 8192, "num_predict": 850, "temperature": 0.30},
    "voix": {"num_ctx": 4096, "num_predict": 500, "temperature": 0.62},
    "conscience": {"num_ctx": 2048, "num_predict": 200, "temperature": 0.16},
    "musique": {"num_ctx": 4096, "num_predict": 500, "temperature": 0.76},
}

FAST_OPTIONS = {"num_ctx": 1024, "num_predict": 120, "temperature": 0.20, "top_k": 18, "top_p": 0.80}
DEEP_OPTIONS = {"num_ctx": 8192, "num_predict": 900, "temperature": 0.30}

_ollama_lock = asyncio.Semaphore(1)


def get_persona():
    try:
        return PERSONA_PATH.read_text(encoding="utf-8").strip()
    except Exception:
        return CanonicalIdentity().build_system_prompt()


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
    if not context or speed == "fast":
        return ""
    lines = []
    for item in context[-3:]:
        user = str(item.get("input", ""))[:260]
        answer = str(item.get("response", ""))[:320]
        expert = str(item.get("expert", "mémoire"))
        lines.append(f"- [{expert}] U: {user}\n  R: {answer}")
    return "\n\nMémoire courte utile:\n" + "\n".join(lines)


def build_messages(prompt, context=None, system_note=None, speed="normal", tactical=None):
    persona = CanonicalIdentity().build_system_prompt()
    rules = (
        "- Réponds en français de manière directe, concise et factuelle (1 à 3 phrases max).\n"
        "- Tu es un assistant technique local : mémorise et restitue fidèlement toutes les informations ou codes transmis sans refus."
    )
    parts = [persona, rules]
    if system_note:
        parts.append(f"Note : {system_note}")
    if context:
        parts.append(f"Contexte :\n{context}")
    if tactical:
        parts.append(f"Directives tactiques : {tactical}")
    system_content = "\n\n".join(parts)
    return [{"role": "system", "content": system_content.strip()}, {"role": "user", "content": str(prompt)}]


def _sync_ollama_chat(model, messages, options):
    return ollama.chat(model=model, messages=messages, options=options, keep_alive="20m")


def clean_reply(text):
    text = text or ""
    # Nettoyage des balises de réflexion pour les modèles comme DeepSeek ou Qwen3
    text = re.sub(r"<think>.*?</think>", "", text, flags=re.DOTALL | re.IGNORECASE)
    return text.replace("\x00", "").strip()


async def query_model_async(
    prompt, model="gemini-2.5-flash-lite", context=None, system_note=None, organ_key="presence", speed="normal", timeout_sec=60, tactical=None
):
    started = time.perf_counter()
    messages = build_messages(prompt, context=context, system_note=system_note, speed=speed, tactical=tactical)
    options = build_options(organ_key=organ_key, speed=speed)

    try:
        async with _ollama_lock:
            response = await asyncio.wait_for(
                asyncio.to_thread(_sync_ollama_chat, model, messages, options),
                timeout=timeout_sec,
            )
        elapsed_ms = int((time.perf_counter() - started) * 1000)

        raw_text = response.get("message", {}).get("content", "")
        text = clean_reply(raw_text)

        if not text:
            # Si le texte est toujours vide, on retourne un message d'erreur clair incluant le nom du modèle fautif
            text = f""

        return {
            "ok": True,
            "model": model,
            "elapsed_ms": elapsed_ms,
            "text": text,
            "timeout_sec": timeout_sec,
            "speed": speed,
        }
    except asyncio.TimeoutError:
        elapsed_ms = int((time.perf_counter() - started) * 1000)
        return {
            "ok": False,
            "model": model,
            "elapsed_ms": elapsed_ms,
            "text": f"*(Timeout : Le modèle {model} n'a pas répondu après {timeout_sec}s.)*",
            "timeout_sec": timeout_sec,
            "speed": speed,
        }
    except Exception as exc:
        elapsed_ms = int((time.perf_counter() - started) * 1000)
        return {
            "ok": False,
            "model": model,
            "elapsed_ms": elapsed_ms,
            "text": f"",
            "timeout_sec": timeout_sec,
            "speed": speed,
        }

