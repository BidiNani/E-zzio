import os
import time
from pathlib import Path
import ollama

PERSONA_PATH = Path("G:/AI/E-zzio/registry/persona.txt")

BASE_OPTIONS = {
    "num_gpu": 0,
    "num_thread": 10,
    "top_k": 35,
    "top_p": 0.88,
    "repeat_penalty": 1.08,
}

ORGAN_OPTIONS = {
    "presence":  {"num_ctx": 4096, "num_predict": 320,  "temperature": 0.45},
    "reflexe":   {"num_ctx": 4096, "num_predict": 260,  "temperature": 0.35},
    "mains":     {"num_ctx": 8192, "num_predict": 850,  "temperature": 0.25},
    "yeux":      {"num_ctx": 4096, "num_predict": 450,  "temperature": 0.35},
    "logique":   {"num_ctx": 8192, "num_predict": 650,  "temperature": 0.2},
    "intuition": {"num_ctx": 8192, "num_predict": 700,  "temperature": 0.5},
    "compagnon": {"num_ctx": 4096, "num_predict": 500,  "temperature": 0.65},
    "archiviste":{"num_ctx": 8192, "num_predict": 700,  "temperature": 0.25},
    "critique":  {"num_ctx": 8192, "num_predict": 850,  "temperature": 0.25},
    "profonde":  {"num_ctx": 8192, "num_predict": 1100, "temperature": 0.35},
    "voix":      {"num_ctx": 8192, "num_predict": 850,  "temperature": 0.7},
    "conscience":{"num_ctx": 4096, "num_predict": 450,  "temperature": 0.2},
    "musique":   {"num_ctx": 8192, "num_predict": 1000, "temperature": 0.78},
}

os.environ["OLLAMA_NUM_GPU"] = "0"
os.environ["CUDA_VISIBLE_DEVICES"] = ""
os.environ["GGML_CUDA"] = "0"

def get_persona():
    try:
        return PERSONA_PATH.read_text(encoding="utf-8").strip()
    except Exception:
        return (
            "Tu es E-ZZIO, assistant local d'Enrik. "
            "Tu réponds en français. Tu es clair, utile, humain, précis et professionnel. "
            "Tu fonctionnes localement en CPU-only et tu n'utilises jamais le GPU."
        )

def build_options(organ_key="presence"):
    options = dict(BASE_OPTIONS)
    options.update(ORGAN_OPTIONS.get(organ_key, ORGAN_OPTIONS["presence"]))
    options["num_gpu"] = 0
    return options

def format_memory(context):
    if not context:
        return ""

    lines = []
    for item in context[-5:]:
        user = str(item.get("input", ""))[:500]
        answer = str(item.get("response", ""))[:700]
        expert = str(item.get("expert", "mémoire"))
        lines.append(f"- [{expert}] Utilisateur: {user}\n  Réponse: {answer}")

    return "\n\nMémoire récente utile:\n" + "\n".join(lines)

def query_model(prompt, model="qwen3:4b", context=None, system_note=None, organ_key="presence"):
    started = time.perf_counter()

    persona = get_persona()
    context = context or []
    system_note = system_note or ""

    full_prompt = (
        f"{persona}\n\n"
        f"{system_note}\n"
        f"{format_memory(context)}\n\n"
        "Règles de réponse:\n"
        "- Réponds directement à la demande.\n"
        "- Ne fais pas de blabla inutile.\n"
        "- Si c'est technique, donne du concret et du testable.\n"
        "- Si tu manques d'information, dis exactement quoi fournir.\n"
        "- Garde une structure claire.\n\n"
        f"Demande utilisateur:\n{prompt}\n\n"
        "Réponse E-ZZIO:"
    )

    try:
        response = ollama.chat(
            model=model,
            messages=[{"role": "user", "content": full_prompt}],
            options=build_options(organ_key),
        )
        elapsed_ms = int((time.perf_counter() - started) * 1000)
        return {
            "ok": True,
            "model": model,
            "elapsed_ms": elapsed_ms,
            "text": response["message"]["content"],
        }
    except Exception as exc:
        elapsed_ms = int((time.perf_counter() - started) * 1000)
        return {
            "ok": False,
            "model": model,
            "elapsed_ms": elapsed_ms,
            "text": f"Erreur modèle E-ZZIO ({model}) : {exc}",
        }
