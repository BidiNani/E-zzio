"""
E-ZZIO : Test des 3 Prompts Constitutionnels d'Auto-Connaissance et d'Ingestion.
"""
import os
import sys
import json
import time
import asyncio
from pathlib import Path

root = Path("G:/AI/E-zzio")
if str(root) not in sys.path:
    sys.path.insert(0, str(root))

from core.cognition.cognitive_gateway import CognitiveGateway

async def run_prompts():
    cg = CognitiveGateway()
    await cg.init()

    prompts = [
        ("que_sais_tu_faire", "Que sais-tu faire ?"),
        ("connais_tu_chaque_fichier", "Connais-tu chaque fichier qui te compose ?"),
        ("resous_ingestion_universelle", "Trouve une solution pour résoudre ton ingestion universelle.")
    ]

    results = {}
    for p_id, p_text in prompts:
        t0 = time.perf_counter()
        print(f"--- TESTING PROMPT: {p_text} ---")
        try:
            res = await cg.ask_async(p_text, session_id=f"test_session_{p_id}")
            lat_ms = (time.perf_counter() - t0) * 1000
            content = res.get("result", "")
            results[p_id] = {
                "prompt": p_text,
                "latency_ms": round(lat_ms, 2),
                "response": content,
                "forbidden_omniscience_detected": "tous en tête" in content.lower(),
                "parallel_fastapi_detected": "app = fastapi" in content.lower() or "/ingest/" in content.lower(),
                "canonical_pipeline_mentioned": "perception" in content.lower() or "universalreader" in content.lower() or "unifiedperception" in content.lower()
            }
            print(f"RESPONSE ({lat_ms:.1f}ms):\n{content}\n")
        except Exception as exc:
            print(f"ERROR ON {p_id}: {exc}")
            results[p_id] = {"prompt": p_text, "error": str(exc)}

    out_file = root / "state/audit/optimization/self_knowledge_and_ingestion_evidence.json"
    out_file.parent.mkdir(parents=True, exist_ok=True)
    out_file.write_text(json.dumps(results, indent=2, ensure_ascii=False), encoding="utf-8")
    print("PROMPT EVALUATION SAVED TO:", out_file)

asyncio.run(run_prompts())
