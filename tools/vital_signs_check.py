#!/usr/bin/env python3
"""E-ZZIO — vital signs check (4 piliers). Static + dynamic, no model calls."""
import ast
import importlib.util
import json
import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
OUT = {"pillars": {}}


def find_mods(*keywords):
    hits = []
    for base in ("core", "runtime"):
        b = ROOT / base
        if not b.exists():
            continue
        for py in b.rglob("*.py"):
            if ".venv" in py.parts or "__pycache__" in py.parts:
                continue
            low = str(py).lower()
            if any(k in low for k in keywords):
                hits.append(str(py.relative_to(ROOT)))
    return sorted(hits)


def try_import(mod):
    try:
        spec = importlib.util.find_spec(mod)
        return "found" if spec else "missing"
    except Exception as exc:
        return f"error:{exc}"


def has_callable(mod, name):
    try:
        m = importlib.import_module(mod)
        return hasattr(m, name)
    except Exception as exc:
        return f"import-error:{type(exc).__name__}"


# ---- PILIER 1 : VOIX ----
voice_mods = find_mods("kokoro", "whisper", "tts", "stt", "voice", "audio")
pipelines = []
for pat in ("kokoro", "whisper", "sounddevice", "pyaudio", "TTS", "faster-whisper", "onnxruntime"):
    pipelines.append((pat, try_import(pat)))
weights = []
for pat in ("**/*.onnx", "**/kokoro*.pt", "**/kokoro*.bin", "**/*whisper*.pt"):
    weights.extend(str(p).relative_to(ROOT) for p in ROOT.glob(pat) if p.stat().st_size > 0)
entry = None
for cand in ("core/audio/synthesizer.py", "core/voice/voice_duplex_engine.py",
             "core/capabilities/kokoro_tts_adapter.py"):
    if (ROOT / cand).exists():
        entry = cand
        break
OUT["pillars"]["voix"] = {"modules": voice_mods[:15], "packages": pipelines,
                           "weights": weights[:10], "entry": entry}

# ---- PILIER 2 : MEMOIRE ----
mem = {}
mem["gateway_import"] = try_import("core.memory.unified_gateway")
mem["tiers_import"] = try_import("core.memory.tiers")
mem["instance_import"] = try_import("core.memory.instance")
dbs = {}
for db in ("runtime/evidence/evidence.db", "data/ezzio.db",
           "runtime/memory/sqlite/cognitive_store.db"):
    p = ROOT / db
    if p.exists():
        try:
            c = sqlite3.connect(str(p), timeout=5)
            mode = c.execute("PRAGMA journal_mode").fetchone()[0]
            integ = c.execute("PRAGMA integrity_check").fetchone()[0]
            c.close()
            dbs[db] = {"exists": True, "journal": mode, "integrity": integ}
        except Exception as exc:
            dbs[db] = {"exists": True, "error": str(exc)}
    else:
        dbs[db] = {"exists": False}
mem["dbs"] = dbs
# persistance conversationnelle : record_message x2 + relecture
try:
    import asyncio, tempfile, os
    from core.memory.unified_gateway import UnifiedMemoryGateway

    async def _t():
        d = tempfile.mkdtemp()
        gw = UnifiedMemoryGateway(db_path=os.path.join(d, "vital.db"))
        await gw.init()
        await gw.record_message("VITAL", "user", "ping vital 1", {})
        await gw.record_message("VITAL", "assistant", "pong vital 1", {})
        hist = await gw.get_session_history("VITAL")
        return len(hist) >= 2
    mem["roundtrip_2tours"] = asyncio.run(_t())
except Exception as exc:
    mem["roundtrip_2tours"] = f"error:{type(exc).__name__}:{str(exc)[:120]}"
OUT["pillars"]["memoire"] = mem

# ---- PILIER 3 : BATTEMENT ----
batt = {}
batt["signal_bus"] = (ROOT / "core/signals/signal_bus.py").exists()
batt["arbitrator"] = (ROOT / "core/operations/multi_mission_arbitrator.py").exists()
# découplage fleet : source-level (pas d'exécution)
try:
    src = (ROOT / "core/ezzio_master.py").read_text(encoding="utf-8", errors="ignore")
    batt["fleet_create_task"] = "asyncio.create_task(self.fleet.execute_mission_async(record))" in src
    batt["await_fleet_in_execute_intent"] = "await self.fleet.execute_mission_async" in src
except Exception as exc:
    batt["source_error"] = str(exc)
# arbitrator slots : borne max_concurrent + libération ?
try:
    asrc = (ROOT / "core/operations/multi_mission_arbitrator.py").read_text(encoding="utf-8", errors="ignore")
    batt["max_slots"] = "max_concurrent_missions" in asrc
    batt["release"] = any(k in asrc for k in ("release", "liber", "free_slot", "current_mission_id = None", "slots -= 1", "slots-=1"))
except Exception as exc:
    batt["arbitrator_error"] = str(exc)
OUT["pillars"]["battement"] = batt

# ---- PILIER 4 : DIALOGUE CONTINU ----
dlg = {}
dlg["cli_run_ezzio"] = (ROOT / "run_ezzio.py").exists()
dlg["cli_ezzio_cli"] = (ROOT / "ezzio_cli.py").exists()
eps = []
for f in ("routers/master.py", "web_server.py", "runtime/routers/llm.py"):
    p = ROOT / f
    if p.exists():
        t = p.read_text(encoding="utf-8", errors="ignore")
        tree = ast.parse(t)
        for n in ast.walk(tree):
            if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)) and "stream" in n.name.lower():
                eps.append(f"{f}:{n.name}")
            if isinstance(n, ast.Call) and getattr(getattr(n.func, "value", None), "id", "") == "router":
                pass
        if "StreamingResponse" in t or "WebSocket" in t:
            eps.append(f"{f}:stream-support")
dlg["streaming"] = eps
OUT["pillars"]["dialogue"] = dlg

print(json.dumps(OUT, indent=1, ensure_ascii=False))
