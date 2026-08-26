from __future__ import annotations
from core.identity.canonical_identity import CanonicalIdentity

import os
import re
import json
import time
from pathlib import Path
from typing import Any, Dict

import requests
import ollama

from core.response_guard import deterministic_reply, sanitize_ezzio_reply

PROJECT_ROOT = Path("G:/AI/E-zzio")
STATE_ROOT = PROJECT_ROOT / "state"
PERF_ROOT = STATE_ROOT / "performance"
POLICY_PATH = PERF_ROOT / "model_policy.json"

PERF_ROOT.mkdir(parents=True, exist_ok=True)

CPU_ONLY_ENV = {
    "OLLAMA_NUM_GPU": "0",
    "CUDA_VISIBLE_DEVICES": "",
    "GGML_CUDA": "0",
    "CUDA_DEVICE_ORDER": "PCI_BUS_ID",
    "EZZIO_GPU_POLICY": "cpu_ram_only",
    "EZZIO_NUM_GPU": "0",
    "PYTORCH_ENABLE_MPS_FALLBACK": "0",
    "EZZIO_NO_ADS": "true",
    "EZZIO_NO_TRACKING": "true",
    "EZZIO_NO_SPONSORS": "true",
    "EZZIO_OLLAMA_THREADS_FAST": "8",
    "EZZIO_OLLAMA_THREADS_NORMAL": "12",
    "EZZIO_OLLAMA_THREADS_DEEP": "16",
}

for key, value in CPU_ONLY_ENV.items():
    os.environ[key] = value

# ---------------------------------------------------------------------------
# CHANGELOG v2.19-pc-policy-realign-and-healthcheck
# - DEFAULT_POLICY réalignée sur l'inventaire Ollama réel (23/08/2026) :
#   retire llama3.2:3b, phi4-mini:latest, deepseek-r1:8b, hermes3:8b,
#   qwen2.5vl:3b, shieldgemma:2b, granite3.3:8b, qwen2.5-coder:1.5b,
#   qwen3:1.7b, qwen3:4b (aucun n'est installé, tous absents de `ollama list`)
#   ajoute qwen3-coder:30b, qwen2.5-coder:14b, qwen3:14b, granite4.1:8b,
#   gpt-oss-20b (mrasif/gpt-oss-20b-GGUF), bge-m3, nomic-embed-text,
#   Kiwi-4b (hf.co/mradermacher/Kiwi-4b-i1-GGUF)
# - Aucune catégorie de tâche n'a plus de candidat introuvable dans
#   installed_models (vérifié contre ollama_models() live)
# - ajout classify_error() : distingue connection_refused / timeout /
#   model_not_found / other au lieu d'un except générique opaque
# - ajout is_available() : healthcheck rapide (GET /api/tags) réutilisable
#   par un futur Cognitive Router (web_server.py) pour décider d'un
#   fallback cloud -> local, sans dupliquer la logique de connexion ici
# - route ajoutée pour "guard" et "vision" et "archive"/"music" avec des
#   modèles réellement installés faute d'équivalent exact : ces catégories
#   pointent maintenant vers un modèle générique existant plutôt que vers
#   un modèle absent (voir commentaires inline). À revalider si des
#   modèles dédiés (vision, garde) sont un jour pull.
# - AUCUN changement de comportement pour fast/companion/identity/code/
#   powershell/logic/deep : mêmes règles de sélection, juste des noms de
#   modèles différents pointant vers des binaires qui existent réellement
# ---------------------------------------------------------------------------

DEFAULT_POLICY = {
    "version": "v2.19-pc-policy-realign-and-healthcheck",
    "models": {
        "fast": ["qwen3:8b", "qwen2.5-coder:7b"],
        "companion": ["qwen3:8b", "qwen3:14b"],
        "identity": ["qwen3:8b", "qwen2.5-coder:7b"],
        "code": ["qwen2.5-coder:7b", "qwen2.5-coder:14b", "qwen3-coder:30b"],
        "powershell": ["qwen2.5-coder:7b", "qwen2.5-coder:14b"],
        "logic": ["qwen3:14b", "qwen3:8b", "qwen2.5-coder:7b"],
        "deep": ["qwen3:14b", "qwen3-coder:30b", "qwen3:8b"],
        # pas de modèle vision installé actuellement (qwen2.5vl:3b absent) ;
        # fallback explicite sur un modèle texte, à corriger si un modèle
        # vision est pull un jour (ex: qwen2.5vl, llava)
        "vision": ["qwen3:8b"],
        # pas de modèle guard dédié installé (shieldgemma:2b absent) ;
        # fallback explicite, PAS un vrai remplacement fonctionnel
        "guard": ["qwen3:8b"],
        "archive": ["granite4.1:8b", "qwen3:14b"],
        "music": ["qwen3:8b", "qwen3:14b"],
        "embed": ["nomic-embed-text", "bge-m3"],
    },
    "avoid_for_identity": ["qwen3:1.7b", "qwen3:4b"],
    "policy": {
        "cpu_ram_only": True,
        "gpu": "untouched",
        "no_ads": True,
        "no_tracking": True,
        "no_sponsors": True,
    },
}

IDENTITY_SYSTEM = CanonicalIdentity().build_system_prompt().strip()

TASK_SYSTEMS = {
    "fast": """
Réponds très court, maximum 2 phrases.
Ne développe pas inutilement.
Ne prétends pas qu'E-ZZIO fonctionne sans Internet pour tout : dis seulement que le cœur PC est local.
Confirme CPU/RAM only, GPU intact, zéro pub si pertinent.
""".strip(),
    "powershell": """
Tu écris des scripts PowerShell professionnels pour E-ZZIO.
Règles : param() en première instruction si paramètres, chemins intégrés, backup, logs, rapport JSON, validation endpoint, rollback si utile.
Évite les patchs regex fragiles et les injections `r`n littérales.
Ne donne pas de conseil vague : donne des règles concrètes.
""".strip(),
    "code": """
Tu aides à coder proprement E-ZZIO.
Privilégie architecture simple, fonctions claires, validation JSON, logs, erreurs explicites et compatibilité Windows.
""".strip(),
    "identity": CanonicalIdentity().build_system_prompt(),
    "deep": """
Analyse de façon structurée et honnête. Distingue actif, prêt, configuré et futur.
""".strip(),
}


def _now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%S")


def clean_reply(text: str) -> str:
    text = text or ""
    text = re.sub(r"<think>.*?</think>", "", text, flags=re.DOTALL | re.IGNORECASE)
    text = text.replace("\x00", "").strip()
    return text


def sanitize_truth(reply: str, task: str) -> str:
    text = clean_reply(reply)

    # Corrections identité/typos récurrentes
    text = text.replace("E-ZZZIO", "E-ZZIO")
    text = text.replace("EZZZIO", "EZZIO")
    text = text.replace("E-ZZIOO", "E-ZZIO")

    low = text.lower()

    risky_internet_claims = [
        "sans nécessiter de connexion internet",
        "ne nécessite pas de connexion internet",
        "sans connexion internet pour fonctionner",
        "fonctionner sans connexion internet",
        "conçu pour fonctionner sans connexion internet",
        "pas besoin d'internet",
        "n'a pas besoin d'internet",
    ]

    if any(x in low for x in risky_internet_claims):
        text = (
            "Le cœur PC d'E-ZZIO fonctionne localement en CPU/RAM only, "
            "sans pub ni tracking. Les connecteurs externes comme Discord, Messenger "
            "ou certaines API publiques nécessitent Internet seulement s'ils sont configurés."
        )

    if task == "powershell":
        low2 = text.lower()

        vague_patterns = [
            "noms de variables explicites",
            "commentaires clairs",
            "try-catch",
            "gestion des erreurs",
        ]

        concrete_terms = [
            "backup",
            "logs",
            "rapport json",
            "rollback",
            "validation endpoint",
            "param()",
            "convertto-json",
        ]

        if any(v in low2 for v in vague_patterns) and not any(c in low2 for c in concrete_terms):
            text = (
                "Règle E-ZZIO PowerShell : commence par param() si paramètres, "
                "écris un backup daté, des logs, un rapport JSON, une validation d'endpoint, "
                "et prévois un rollback avant toute modification risquée."
            )

    if task == "fast":
        parts = []
        current = ""

        for char in text:
            current += char
            if char in ".!?":
                if current.strip():
                    parts.append(current.strip())
                current = ""

        if current.strip():
            parts.append(current.strip())

        text = " ".join(parts[:2]).strip()

    return text


def words(text: str) -> set[str]:
    return set(re.findall(r"[a-zA-ZÀ-ÿ0-9_.:-]+", (text or "").lower()))


def has_phrase(low: str, phrases: list[str]) -> bool:
    return any(p in low for p in phrases)


def ollama_models() -> list[str]:
    try:
        response = requests.get("http://127.0.0.1:11434/api/tags", timeout=5)
        data = response.json()
        return sorted([item.get("name") for item in data.get("models", []) if item.get("name")])
    except Exception:
        return []


def is_available() -> Dict[str, Any]:
    """
    Healthcheck léger et rapide (pas de génération, juste /api/tags).
    Pensé pour être appelé par un futur Cognitive Router (dans
    web_server.py) AVANT de décider d'un fallback cloud -> local, sans
    dupliquer ici de logique de décision : ce module reste un routeur
    intra-Ollama, la décision cloud/local reste hors de ce fichier.
    """
    started = time.time()
    try:
        response = requests.get("http://127.0.0.1:11434/api/tags", timeout=3)
        response.raise_for_status()
        elapsed_ms = int((time.time() - started) * 1000)
        return {"available": True, "elapsed_ms": elapsed_ms, "error": None}
    except requests.exceptions.ConnectionError:
        return {"available": False, "elapsed_ms": int((time.time() - started) * 1000), "error": "connection_refused"}
    except requests.exceptions.Timeout:
        return {"available": False, "elapsed_ms": int((time.time() - started) * 1000), "error": "timeout"}
    except Exception as exc:
        return {"available": False, "elapsed_ms": int((time.time() - started) * 1000), "error": f"other:{exc}"}


def classify_error(exc: Exception) -> str:
    """
    Classification grossière mais utile pour qu'un appelant en amont
    (E-zzio) puisse distinguer "modèle absent -> pull ou changer de
    policy" de "Ollama down -> basculer sur le cloud" de "timeout ->
    peut-être juste réessayer".
    """
    name = type(exc).__name__
    text = str(exc).lower()

    if isinstance(exc, requests.exceptions.ConnectionError) or "connection refused" in text or "connection error" in text:
        return "connection_refused"
    if isinstance(exc, requests.exceptions.Timeout) or "timeout" in text or "timed out" in text:
        return "timeout"
    if "model" in text and ("not found" in text or "not exist" in text or "no such" in text):
        return "model_not_found"
    return f"other:{name}"


def load_policy() -> Dict[str, Any]:
    if POLICY_PATH.exists():
        try:
            policy = json.loads(POLICY_PATH.read_text(encoding="utf-8"))
            policy["version"] = "v2.19-pc-policy-realign-and-healthcheck"
            return policy
        except Exception:
            pass

    save_policy(DEFAULT_POLICY)
    return DEFAULT_POLICY


def save_policy(policy: Dict[str, Any]) -> Dict[str, Any]:
    PERF_ROOT.mkdir(parents=True, exist_ok=True)
    policy["version"] = "v2.19-pc-policy-realign-and-healthcheck"
    POLICY_PATH.write_text(json.dumps(policy, ensure_ascii=False, indent=2), encoding="utf-8")
    return policy


def latest_guarded_bench():
    files = sorted(PERF_ROOT.glob("bench_guarded_*.json"), key=lambda p: p.stat().st_mtime, reverse=True)
    for path in files:
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            data["_path"] = str(path)
            return data
        except Exception:
            continue
    return None


def infer_task(text: str, requested_task: str = "auto", speed: str = "auto") -> str:
    requested_task = (requested_task or "auto").lower().strip()
    speed = (speed or "auto").lower().strip()

    if requested_task and requested_task != "auto":
        return requested_task

    low = (text or "").lower()
    token_set = words(low)

    explicit_code_words = {
        "python",
        "fastapi",
        "code",
        "fonction",
        "classe",
        "router",
        "endpoint",
        "json",
        "traceback",
        "syntaxerror",
        "debug",
    }

    explicit_powershell_words = {
        "powershell",
        ".ps1",
        "script",
        "backup",
        "rollback",
        "logs",
        "log",
        "set-content",
        "invoke-restmethod",
        "get-content",
    }

    if token_set.intersection(explicit_powershell_words):
        return "powershell"

    if token_set.intersection(explicit_code_words):
        return "code"

    if has_phrase(low, ["qui es-tu", "ton rôle", "identité", "brothereye", "ami ia"]) or "e-zzio" in low or "ezzio" in low:
        return "identity"

    if has_phrase(low, ["réfléchis", "analyse profonde", "architecture", "stratégie", "plan complet"]):
        return "deep"

    if token_set.intersection({"image", "photo", "vision", "screenshot", "capture"}):
        return "vision"

    if speed == "fast" or token_set.intersection({"vite", "rapide", "court", "bref"}):
        return "fast"

    if len(low) < 160:
        return "fast"

    return "companion"


def select_model(task: str = "auto", text: str = "", speed: str = "auto") -> Dict[str, Any]:
    policy = load_policy()
    installed = ollama_models()
    resolved_task = infer_task(text, task, speed)
    speed = (speed or "auto").lower().strip()

    if speed == "fast" and resolved_task not in ("powershell", "code", "vision", "guard"):
        candidate_keys = ["fast", resolved_task, "companion"]
    elif speed == "deep":
        candidate_keys = ["deep", resolved_task, "companion"]
    else:
        candidate_keys = [resolved_task, "companion", "fast"]

    candidates = []
    for key in candidate_keys:
        candidates.extend(policy.get("models", {}).get(key, []))

    deduped = []
    for item in candidates:
        if item not in deduped:
            deduped.append(item)

    for model in deduped:
        if model in installed:
            return {
                "ok": True,
                "task": resolved_task,
                "speed": speed,
                "model": model,
                "installed": True,
                "candidates": deduped,
                "reason": "first_installed_policy_match",
                "policy_path": str(POLICY_PATH),
            }

    return {
        "ok": False,
        "task": resolved_task,
        "speed": speed,
        "model": None,
        "installed": False,
        "candidates": deduped,
        "installed_models": installed,
        "reason": "no_candidate_installed",
        "policy_path": str(POLICY_PATH),
    }


def router_status() -> Dict[str, Any]:
    policy = load_policy()
    bench = latest_guarded_bench()
    installed = ollama_models()
    health = is_available()

    route_preview = {}
    for task in ["fast", "companion", "identity", "powershell", "code", "logic", "deep", "vision", "guard", "archive", "music"]:
        route_preview[task] = select_model(task=task, text="", speed="auto")

    return {
        "ok": True,
        "version": "v2.19-pc-policy-realign-and-healthcheck",
        "created_at": _now(),
        "policy_path": str(POLICY_PATH),
        "health": health,
        "installed_models": installed,
        "route_preview": route_preview,
        "latest_guarded_bench": {
            "available": bench is not None,
            "best": bench.get("best") if bench else None,
            "accepted_count": bench.get("accepted_count") if bench else None,
            "report_path": bench.get("report_path") or bench.get("_path") if bench else None,
        },
        "policy": policy,
    }


def chat_with_route(text: str, task: str = "auto", speed: str = "auto", predict: int = 260) -> Dict[str, Any]:
    route = select_model(task=task, text=text, speed=speed)
    if not route.get("ok"):
        return {"ok": False, "route": route, "reply": "Aucun modèle local installé ne correspond à cette tâche.", "error_kind": "no_candidate_installed"}

    model = route["model"]
    resolved_task = route["task"]

    static = deterministic_reply(text, resolved_task)
    if static:
        return {
            "ok": True,
            "created_at": _now(),
            "route": route,
            "elapsed_ms": 0,
            "reply": sanitize_ezzio_reply(static, resolved_task),
            "deterministic": True,
            "policy": {"cpu_ram_only": True, "gpu": "untouched", "no_ads": True},
        }

    if resolved_task == "fast":
        threads = int(os.environ.get("EZZIO_OLLAMA_THREADS_FAST", "8"))
        num_ctx = 1536
        temperature = 0.05
        predict = min(int(predict), 80)
    elif resolved_task == "deep":
        threads = int(os.environ.get("EZZIO_OLLAMA_THREADS_DEEP", "16"))
        num_ctx = 4096
        temperature = 0.2
    else:
        threads = int(os.environ.get("EZZIO_OLLAMA_THREADS_NORMAL", "12"))
        num_ctx = 4096
        temperature = 0.1

    task_rules = TASK_SYSTEMS.get(resolved_task, "")

    started = time.time()

    try:
        response = ollama.chat(
            model=model,
            messages=[{"role": "system", "content": IDENTITY_SYSTEM + "\n\n" + task_rules}, {"role": "user", "content": text or ""}],
            options={"num_gpu": 0, "num_ctx": num_ctx, "num_predict": int(predict), "temperature": temperature, "num_thread": threads},
            keep_alive="20m",
        )

        reply = sanitize_ezzio_reply(sanitize_truth(response.get("message", {}).get("content", ""), resolved_task), resolved_task)

        return {
            "ok": True,
            "created_at": _now(),
            "route": route,
            "elapsed_ms": int((time.time() - started) * 1000),
            "reply": reply,
            "policy": {"cpu_ram_only": True, "gpu": "untouched", "no_ads": True},
        }

    except Exception as exc:
        return {
            "ok": False,
            "created_at": _now(),
            "route": route,
            "elapsed_ms": int((time.time() - started) * 1000),
            "error": str(exc),
            "error_kind": classify_error(exc),
        }


def write_default_policy() -> Dict[str, Any]:
    return save_policy(DEFAULT_POLICY)
