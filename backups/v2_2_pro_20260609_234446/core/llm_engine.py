import os
from pathlib import Path
import ollama

PERSONA_PATH = Path("G:/AI/E-zzio/registry/persona.txt")

CPU_OPTIONS = {
    "num_gpu": 0,
    "num_thread": 10,
    "num_ctx": 8192,
    "num_predict": 700,
    "top_k": 40,
    "top_p": 0.9,
    "temperature": 0.55,
}

os.environ["OLLAMA_NUM_GPU"] = "0"
os.environ["CUDA_VISIBLE_DEVICES"] = ""
os.environ["GGML_CUDA"] = "0"

def get_persona():
    try:
        return PERSONA_PATH.read_text(encoding="utf-8").strip()
    except Exception:
        return "Tu es E-ZZIO, assistant local utile, clair et professionnel."

def query_model(prompt, model="qwen3:4b", context=None, system_note=None):
    persona = get_persona()
    context = context or []
    system_note = system_note or ""

    memory_block = ""
    if context:
        lines = []
        for item in context[-5:]:
            user = item.get("input", "")
            answer = item.get("response", "")
            expert = item.get("expert", "mémoire")
            lines.append(f"- [{expert}] Utilisateur: {user}\n  Réponse: {answer}")
        memory_block = "\n\nMémoire récente:\n" + "\n".join(lines)

    full_prompt = (
        f"{persona}\n\n"
        f"{system_note}\n"
        f"{memory_block}\n\n"
        f"Demande utilisateur:\n{prompt}\n\n"
        "Réponse E-ZZIO:"
    )

    try:
        response = ollama.chat(
            model=model,
            messages=[{"role": "user", "content": full_prompt}],
            options=CPU_OPTIONS,
        )
        return response["message"]["content"]
    except Exception as exc:
        return f"Erreur modèle E-ZZIO ({model}) : {exc}"
