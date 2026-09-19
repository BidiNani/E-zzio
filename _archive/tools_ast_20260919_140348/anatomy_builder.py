#!/usr/bin/env python3
"""Anatomie E-ZZIO : organes par sous-dossier + orphelins exploitables."""
import json
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RUNTIME_ENTRY = {
    "routers/master.py", "core/ezzio_master.py",
    "core/agent/coder_federation.py", "core/routing/model_registry.py",
    "web_server.py", "routers/openai_compat.py", "routers/telemetry.py",
    "core/memory/unified_gateway.py", "core/memory/tiers.py",
    "core/security/audit_ledger.py",
    "core/integrations/discord/discord_client.py",
    "core/llm_engine.py", "runtime/model_router/router.py",
}

g = json.load(open(ROOT / "data" / "audit_graph.json", encoding="utf-8"))
files = g["files"]
incoming = g["incoming"]

organs = defaultdict(lambda: {"n": 0, "loc": 0, "classes": 0, "entry": [], "orphans": []})
for path, r in files.items():
    if "module" not in r:
        continue
    top = path.split("\\")[0] + "/" + (path.split("\\")[1] if "\\" in path else "")
    o = organs[top]
    o["n"] += 1
    o["loc"] += r.get("loc", 0)
    o["classes"] += len(r.get("classes", []))
    if path.replace("\\", "/") in {p.replace("/", "\\") for p in RUNTIME_ENTRY} or \
       path.replace("\\", "/") in RUNTIME_ENTRY:
        o["entry"].append(path)

for path in g["orphans"]:
    if "module" not in files.get(path, {}):
        continue
    if "__init__" in path or "/tests/" in path:
        continue
    top = path.split("\\")[0] + "/" + (path.split("\\")[1] if "\\" in path else "")
    # exclure points d'entrée connus
    if Path(path).name in ("run_ezzio.py", "app.py", "main.py", "ezzio_cli.py"):
        continue
    organs[top]["orphans"].append(path)

anatomy = {k: {"fichiers": v["n"], "loc": v["loc"], "classes": v["classes"],
               "entrees_runtime": v["entry"], "n_orphelins": len(v["orphans"]),
               "orphelins": sorted(v["orphans"])[:25]} for k, v in sorted(organs.items())}
out = ROOT / "core" / "system_anatomy.json"
out.write_text(json.dumps(anatomy, indent=1, ensure_ascii=False), encoding="utf-8")
tot_f = sum(v["fichiers"] for v in anatomy.values())
tot_o = sum(v["n_orphelins"] for v in anatomy.values())
print(f"sous-dossiers: {len(anatomy)} | fichiers: {tot_f} | orphelins: {tot_o}")
for k, v in anatomy.items():
    if v["n_orphelins"]:
        print(f"{k}: {v['fichiers']}f/{v['loc']}loc classes={v['classes']} ORPHELINS={v['n_orphelins']}")
print("wrote", out)
