from __future__ import annotations

import os
import json
import time
import subprocess
from pathlib import Path
from typing import Any, Dict, List

import psutil
import requests
import ollama

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

def _now():
    return time.strftime("%Y-%m-%dT%H:%M:%S")

def _gb(value: float) -> float:
    return round(value / (1024 ** 3), 2)

def pc_profile() -> Dict[str, Any]:
    mem = psutil.virtual_memory()

    disks = []
    for part in psutil.disk_partitions(all=False):
        try:
            usage = psutil.disk_usage(part.mountpoint)
            disks.append({
                "device": part.device,
                "mountpoint": part.mountpoint,
                "fstype": part.fstype,
                "total_gb": _gb(usage.total),
                "free_gb": _gb(usage.free),
                "used_percent": usage.percent,
            })
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

def ollama_tags() -> Dict[str, Any]:
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

def warmup_model(model: str, prompt: str = "Réponds seulement: OK", timeout_sec: int = 120) -> Dict[str, Any]:
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
                {"role": "system", "content": "Tu es E-ZZIO. Réponds court."},
                {"role": "user", "content": prompt},
            ],
            options={
                "num_gpu": 0,
                "num_ctx": 1024,
                "num_predict": 16,
                "temperature": 0,
                "num_thread": int(os.environ.get("EZZIO_OLLAMA_THREADS_FAST", "8")),
            },
            keep_alive="20m",
        )

        elapsed_ms = int((time.time() - started) * 1000)

        return {
            "ok": True,
            "model": model,
            "elapsed_ms": elapsed_ms,
            "reply": response.get("message", {}).get("content", "").strip()[:200],
        }

    except Exception as exc:
        elapsed_ms = int((time.time() - started) * 1000)
        return {
            "ok": False,
            "model": model,
            "elapsed_ms": elapsed_ms,
            "error": str(exc),
        }

def warmup_profile(level: str = "fast") -> Dict[str, Any]:
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

def bench_model(model: str, prompt: str = "Explique en une phrase le rôle d'E-ZZIO.", predict: int = 80) -> Dict[str, Any]:
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
                {"role": "system", "content": "Tu es E-ZZIO. Français. Court. Zéro pub."},
                {"role": "user", "content": prompt},
            ],
            options={
                "num_gpu": 0,
                "num_ctx": 2048,
                "num_predict": int(predict),
                "temperature": 0.15,
                "num_thread": int(os.environ.get("EZZIO_OLLAMA_THREADS_NORMAL", "12")),
            },
            keep_alive="20m",
        )

        elapsed_ms = int((time.time() - started) * 1000)
        text = response.get("message", {}).get("content", "").strip()

        return {
            "ok": True,
            "model": model,
            "elapsed_ms": elapsed_ms,
            "reply_chars": len(text),
            "reply": text,
        }

    except Exception as exc:
        return {
            "ok": False,
            "model": model,
            "elapsed_ms": int((time.time() - started) * 1000),
            "error": str(exc),
        }

def quick_bench() -> Dict[str, Any]:
    candidates = [
        "qwen3:1.7b",
        "llama3.2:3b",
        "qwen3:4b",
        "phi4-mini:latest",
        "qwen2.5-coder:7b",
    ]

    started = time.time()
    results = []

    for model in candidates:
        results.append(bench_model(model))

    ok_results = [r for r in results if r.get("ok")]
    best = None
    if ok_results:
        best = sorted(ok_results, key=lambda x: x.get("elapsed_ms", 999999))[0]

    report = {
        "ok": len(ok_results) > 0,
        "created_at": _now(),
        "elapsed_ms": int((time.time() - started) * 1000),
        "best": best,
        "results": results,
        "recommendation": {
            "fast_default": "qwen3:1.7b ou llama3.2:3b",
            "normal_default": "qwen3:4b ou phi4-mini:latest",
            "code_default": "qwen2.5-coder:7b",
            "deep_default": "qwen3:8b ou deepseek-r1:8b",
        },
    }

    path = PERF_ROOT / f"bench_{time.strftime('%Y%m%d_%H%M%S')}.json"
    path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    report["report_path"] = str(path)

    return report

def performance_status() -> Dict[str, Any]:
    return {
        "ok": True,
        "version": "v2.15-pc-core-optimizer",
        "created_at": _now(),
        "pc": pc_profile(),
        "ollama": ollama_tags(),
        "warmup_profiles": {
            "fast": FAST_WARMUP_MODELS,
            "normal": FAST_WARMUP_MODELS + NORMAL_WARMUP_MODELS,
            "deep": FAST_WARMUP_MODELS + NORMAL_WARMUP_MODELS + DEEP_MODELS[:2],
        },
        "policy": {
            "cpu_ram_only": True,
            "gpu": "untouched",
            "no_ads": True,
        },
    }
