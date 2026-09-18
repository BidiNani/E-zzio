from __future__ import annotations

import json
import os
import re
import time
from pathlib import Path
from typing import Any

import ollama
import psutil

from core.identity.canonical_identity import CanonicalIdentity

PROJECT_ROOT = Path("G:/AI/E-zzio")
STATE_ROOT = PROJECT_ROOT / "state"
PERF_ROOT = STATE_ROOT / "performance"
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
    "EZZIO_PC_PROFILE": "ryzen_5900x_32gb_cpu_first",
    "EZZIO_OLLAMA_THREADS_FAST": "8",
    "EZZIO_OLLAMA_THREADS_NORMAL": "12",
    "EZZIO_OLLAMA_THREADS_DEEP": "16",
}

for key, value in CPU_ONLY_ENV.items():
    os.environ[key] = value

FAST_WARMUP_MODELS = [
    "qwen3:1.7b",
    "llama3.2:3b",
    "qwen2.5-coder:1.5b",
]

NORMAL_WARMUP_MODELS = [
    "qwen3:4b",
    "phi4-mini:latest",
    "qwen2.5-coder:7b",
]

DEEP_MODELS = [
    "qwen3:8b",
    "deepseek-r1:8b",
    "hermes3:8b",
    "granite3.3:8b",
]

IDENTITY_SYSTEM = CanonicalIdentity().build_system_prompt().strip()

IDENTITY_PROMPT = """
Réponds en une seule phrase.
Question : Quel est le rôle d'E-ZZIO ?
Réponse attendue : E-ZZIO est l'organisme souverain géré par CanonicalIdentity.
""".strip()

BAD_TERMS = [
    "voiture",
    "automobile",
    "garage",
    "pièces auto",
    "marque de produits",
    "réparations",
    "vieillissante voiture",
    "non filtré",
    "sans restrictions de contenu",
    "contenu non restreint",
    "publicité",
    "sponsorisé",
    "tracking publicitaire",
]

GOOD_TERMS = [
    "ami ia",
    "assistant",
    "local",
    "enrik",
    "pc",
    "cpu",
    "ram",
    "sans pub",
    "zéro pub",
    "tracking",
    "vision",
    "forge",
    "supervision",
    "watchdog",
]


def _now():
    return time.strftime("%Y-%m-%dT%H:%M:%S")


def _gb(value: float) -> float:
    return round(value / (1024**3), 2)


def clean_reply(text: str) -> str:
    text = text or ""
    text = re.sub(r"<think>.*?</think>", "", text, flags=re.DOTALL | re.IGNORECASE)
    text = text.replace("\x00", "").strip()
    return text


NEGATED_BAD_PATTERNS = {
    "publicité": [
        "sans publicité",
        "zéro publicité",
        "aucune publicité",
        "pas de publicité",
        "sans pub",
        "zéro pub",
    ],
    "tracking": [
        "sans tracking",
        "zéro tracking",
        "aucun tracking",
        "pas de tracking",
    ],
    "tracking publicitaire": [
        "sans tracking",
        "zéro tracking",
        "aucun tracking",
        "pas de tracking",
        "sans tracking publicitaire",
        "aucun tracking publicitaire",
    ],
    "sponsorisé": [
        "non sponsorisé",
        "pas sponsorisé",
        "sans sponsor",
        "sans sponsors",
        "zéro sponsor",
        "aucun sponsor",
    ],
}


def collect_bad_hits(low: str):
    hits = []

    for term in BAD_TERMS:
        if term not in low:
            continue

        negated_patterns = NEGATED_BAD_PATTERNS.get(term, [])
        if any(pattern in low for pattern in negated_patterns):
            continue

        hits.append(term)

    return hits


def identity_score(text: str) -> dict[str, Any]:
    cleaned = clean_reply(text)
    low = cleaned.lower()

    bad_hits = collect_bad_hits(low)
    good_hits = [term for term in GOOD_TERMS if term in low]

    score = 0
    score += min(len(good_hits), 6) * 10
    score -= len(bad_hits) * 25

    if len(cleaned) < 20:
        score -= 40

    if "e-zzio" in low or "ezzio" in low:
        score += 10

    if "enrik" in low:
        score += 10

    if ("sans pub" in low) or ("zéro pub" in low):
        score += 10

    accepted = score >= 25 and len(bad_hits) == 0 and len(cleaned) >= 20

    return {
        "accepted": accepted,
        "score": score,
        "bad_hits": bad_hits,
        "good_hits": good_hits,
        "cleaned": cleaned,
    }


def pc_profile() -> dict[str, Any]:
    mem = psutil.virtual_memory()

    disks = []
    for part in psutil.disk_partitions(all=False):
        try:
            usage = psutil.disk_usage(part.mountpoint)
            disks.append(
                {
                    "device": part.device,
                    "mountpoint": part.mountpoint,
                    "fstype": part.fstype,
                    "total_gb": _gb(usage.total),
                    "free_gb": _gb(usage.free),
                    "used_percent": usage.percent,
                }
            )
        except Exception:
            pass

    return {
        "ok": True,
        "created_at": _now(),
        "profile": "ryzen_5900x_32gb_cpu_ram_nvme_first",
        "cpu": {
            "physical_cores": psutil.cpu_count(logical=False),
            "logical_cores": psutil.cpu_count(logical=True),
            "current_percent": psutil.cpu_percent(interval=0.25),
            "recommended_threads": {
                "fast": int(os.environ.get("EZZIO_OLLAMA_THREADS_FAST", "8")),
                "normal": int(os.environ.get("EZZIO_OLLAMA_THREADS_NORMAL", "12")),
                "deep": int(os.environ.get("EZZIO_OLLAMA_THREADS_DEEP", "16")),
            },
        },
        "ram": {
            "total_gb": _gb(mem.total),
            "available_gb": _gb(mem.available),
            "used_percent": mem.percent,
            "policy": "garder marge RAM pour Windows, navigateur, ComfyUI CPU et Ollama",
        },
        "disks": disks,
        "gpu_policy": {
            "gpu": "untouched",
            "ollama_num_gpu": os.environ.get("OLLAMA_NUM_GPU"),
            "cuda_visible_devices": os.environ.get("CUDA_VISIBLE_DEVICES"),
            "ezzio_gpu_policy": os.environ.get("EZZIO_GPU_POLICY"),
        },
        "no_ads": {
            "ads": os.environ.get("EZZIO_NO_ADS"),
            "tracking": os.environ.get("EZZIO_NO_TRACKING"),
            "sponsors": os.environ.get("EZZIO_NO_SPONSORS"),
        },
    }


def ollama_tags() -> dict[str, Any]:
    try:
        response = requests.get("http://127.0.0.1:11434/api/tags", timeout=5)
        data = response.json()
        models = [item.get("name") for item in data.get("models", []) if item.get("name")]
        return {"ok": True, "models": sorted(models)}
    except Exception as exc:
        return {"ok": False, "error": str(exc), "models": []}


def model_available(model: str) -> bool:
    tags = ollama_tags()
    return model in tags.get("models", [])


def warmup_model(model: str, prompt: str = "Réponds uniquement par: OK", timeout_sec: int = 120) -> dict[str, Any]:
    started = time.time()

    if not model_available(model):
        return {
            "ok": False,
            "model": model,
            "error": "model_not_installed",
            "elapsed_ms": 0,
        }

    try:
        response = ollama.chat(
            model=model,
            messages=[
                {"role": "system", "content": IDENTITY_SYSTEM},
                {"role": "user", "content": prompt},
            ],
            options={
                "num_gpu": 0,
                "num_ctx": 1024,
                "num_predict": 24,
                "temperature": 0,
                "num_thread": int(os.environ.get("EZZIO_OLLAMA_THREADS_FAST", "8")),
            },
            keep_alive="20m",
        )

        elapsed_ms = int((time.time() - started) * 1000)
        text = clean_reply(response.get("message", {}).get("content", ""))

        return {
            "ok": True,
            "model": model,
            "elapsed_ms": elapsed_ms,
            "reply": text[:200],
        }

    except Exception as exc:
        elapsed_ms = int((time.time() - started) * 1000)
        return {
            "ok": False,
            "model": model,
            "elapsed_ms": elapsed_ms,
            "error": str(exc),
        }


def warmup_profile(level: str = "fast") -> dict[str, Any]:
    level = (level or "fast").lower().strip()

    if level == "normal":
        models = FAST_WARMUP_MODELS + NORMAL_WARMUP_MODELS
    elif level == "deep":
        models = FAST_WARMUP_MODELS + NORMAL_WARMUP_MODELS + DEEP_MODELS[:2]
    else:
        models = FAST_WARMUP_MODELS

    results = []
    started = time.time()

    for model in models:
        results.append(warmup_model(model))

    report = {
        "ok": all(item.get("ok") or item.get("error") == "model_not_installed" for item in results),
        "level": level,
        "created_at": _now(),
        "elapsed_ms": int((time.time() - started) * 1000),
        "results": results,
        "policy": {
            "cpu_ram_only": True,
            "gpu": "untouched",
        },
    }

    path = PERF_ROOT / f"warmup_{level}_{time.strftime('%Y%m%d_%H%M%S')}.json"
    path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    report["report_path"] = str(path)

    return report


def bench_model(model: str, prompt: str = IDENTITY_PROMPT, predict: int = 80) -> dict[str, Any]:
    started = time.time()

    if not model_available(model):
        return {
            "ok": False,
            "model": model,
            "error": "model_not_installed",
        }

    try:
        response = ollama.chat(
            model=model,
            messages=[
                {"role": "system", "content": IDENTITY_SYSTEM},
                {"role": "user", "content": prompt or IDENTITY_PROMPT},
            ],
            options={
                "num_gpu": 0,
                "num_ctx": 2048,
                "num_predict": int(predict),
                "temperature": 0.05,
                "top_p": 0.8,
                "num_thread": int(os.environ.get("EZZIO_OLLAMA_THREADS_NORMAL", "12")),
            },
            keep_alive="20m",
        )

        elapsed_ms = int((time.time() - started) * 1000)
        text = clean_reply(response.get("message", {}).get("content", ""))
        guard = identity_score(text)

        return {
            "ok": True,
            "accepted": guard["accepted"],
            "identity_score": guard["score"],
            "bad_hits": guard["bad_hits"],
            "good_hits": guard["good_hits"],
            "model": model,
            "elapsed_ms": elapsed_ms,
            "reply_chars": len(text),
            "reply": text,
        }

    except Exception as exc:
        return {
            "ok": False,
            "accepted": False,
            "identity_score": -999,
            "model": model,
            "elapsed_ms": int((time.time() - started) * 1000),
            "error": str(exc),
        }


def quick_bench() -> dict[str, Any]:
    candidates = [
        "qwen3:1.7b",
        "llama3.2:3b",
        "qwen3:4b",
        "phi4-mini:latest",
        "qwen2.5-coder:7b",
        "hermes3:8b",
    ]

    started = time.time()
    results = []

    for model in candidates:
        results.append(bench_model(model))

    accepted_results = [r for r in results if r.get("ok") and r.get("accepted")]
    ok_results = [r for r in results if r.get("ok")]

    best = None
    if accepted_results:
        best = sorted(accepted_results, key=lambda x: (-x.get("identity_score", 0), x.get("elapsed_ms", 999999)))[0]

    report = {
        "ok": len(ok_results) > 0,
        "guarded": True,
        "created_at": _now(),
        "elapsed_ms": int((time.time() - started) * 1000),
        "best": best,
        "accepted_count": len(accepted_results),
        "results": results,
        "recommendation": {
            "rule": "ne jamais choisir un modèle qui répond vide, hallucine E-ZZIO automobile, ou viole la politique zéro pub",
            "fast_default": "à choisir selon bench accepté, sinon qwen2.5-coder:1.5b pour tâches courtes",
            "normal_default": "phi4-mini:latest ou qwen2.5-coder:7b si accepté",
            "code_default": "qwen2.5-coder:7b",
            "deep_default": "qwen3:8b ou deepseek-r1:8b après bench deep",
        },
    }

    path = PERF_ROOT / f"bench_guarded_{time.strftime('%Y%m%d_%H%M%S')}.json"
    path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    report["report_path"] = str(path)

    return report


def performance_status() -> dict[str, Any]:
    return {
        "ok": True,
        "version": "v2.15.3b-negation-aware-bench-guard",
        "created_at": _now(),
        "pc": pc_profile(),
        "ollama": ollama_tags(),
        "warmup_profiles": {
            "fast": FAST_WARMUP_MODELS,
            "normal": FAST_WARMUP_MODELS + NORMAL_WARMUP_MODELS,
            "deep": FAST_WARMUP_MODELS + NORMAL_WARMUP_MODELS + DEEP_MODELS[:2],
        },
        "bench_guard": {
            "enabled": True,
            "rejects_empty": True,
            "rejects_wrong_identity": True,
            "rejects_ads_or_non_filtered_claims": True,
            "negation_aware": True,
        },
        "policy": {
            "cpu_ram_only": True,
            "gpu": "untouched",
            "no_ads": True,
        },
    }
