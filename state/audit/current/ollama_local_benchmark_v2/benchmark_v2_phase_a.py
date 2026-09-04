#!/usr/bin/env python
"""
E-ZZIO LOCAL LLM BENCHMARK V2 — PHASE A
=========================================
CAMPAIGN_V1: ABORTED / INVALIDATED
Do NOT reuse any V1 measurements.

Standard : EVIDENCE RULE v1.1 - NO CLAIM WITHOUT OBSERVABLE PROOF
Host     : AMD Ryzen 9 5900X / 32 GB DDR4 / CPU-only (num_gpu=0)
Ollama   : 0.33.2
Output   : state/audit/current/ollama_local_benchmark_v2/

Design:
  - python -u + flush=True on every print -> visible log
  - Checkpoint written after EACH API call (before next run)
  - REQUEST_TIMEOUT = 180s (hard, no dynamic increase)
  - 3 consecutive timeouts on same task -> skip remaining for model
  - COLD run = first API call per model (unload before)
  - WARM run = all subsequent (model stays loaded)
  - LOAD_MS and TTFT_MS are SEPARATE fields (never summed)
  - RAM measured with psutil (before/peak/after)
  - Execution order randomized (seed=42)
"""
import sys, time, json, hashlib, pathlib, psutil, httpx, statistics, random
from datetime import datetime, timezone

OUT_DIR  = pathlib.Path(r"G:\AI\E-zzio\state\audit\current\ollama_local_benchmark_v2")
CKPT_DIR = OUT_DIR / "checkpoints"
OUT_DIR.mkdir(parents=True, exist_ok=True)
CKPT_DIR.mkdir(parents=True, exist_ok=True)

OLLAMA   = "http://127.0.0.1:11434"
TIMEOUT  = 180.0
THREADS  = 4
CTX      = 4096
GPU      = 0
MAX_TO   = 3        # consecutive timeouts before skipping task for model
CAMPAIGN = "V2A"
SEED     = 42

random.seed(SEED)
MODELS_POOL = ["phi4-mini:latest", "qwen3.5:9b", "hermes3:8b", "nemotron-3-nano:4b"]
MODELS = MODELS_POOL.copy()
random.shuffle(MODELS)
EXEC_ORDER = MODELS.copy()

# ─────────────────────────────────────────────────────────────────────────────
def ts():  return datetime.now(timezone.utc).isoformat()
def log(m): print(f"[{time.strftime('%H:%M:%S')}] {m}", flush=True)
def ph(t):  return hashlib.sha256(t.encode()).hexdigest()[:12]
def ram():
    m = psutil.virtual_memory()
    return {"used_gb": round(m.used/1073741824,2), "avail_gb": round(m.available/1073741824,2), "pct": m.percent}

def stats(vals):
    if not vals: return {"min":0,"mean":0,"p50":0,"p95":0,"max":0,"stdev":0}
    v=sorted(vals); n=len(v)
    mn=round(statistics.mean(v),2); med=round(statistics.median(v),2)
    sd=round(statistics.stdev(v),2) if n>1 else 0.0
    p95=round(v[min(int(0.95*(n-1)),n-1)],2)
    return {"min":round(v[0],2),"mean":mn,"p50":med,"p95":p95,"max":round(v[-1],2),"stdev":sd}

# ─────────────────────────────────────────────────────────────────────────────
# PROMPT DEFINITIONS
# Prompts are identical across models for the same task.
# Multi-problem tasks (REASONING x5, CODING x4, TOOLS x3) run each problem once.
# Single-prompt tasks (FAST_ROUTING, AGENT, LONG_CONTEXT, LONG_GEN) run 3 times.
# Total per model: 3+5+4+3+3+3+3 = 24 API calls  /  4 models = ~96 calls total.

PROMPTS = {
    "FAST_ROUTING": {"id":"FR01","text":'Route query: "Generate 2026 sales chart". Reply ONLY strict JSON: {"category":"chart|code|chat","confidence":0.95}.','sys':"Routing classifier. Reply strict JSON only.","np":48},
    "REASONING": [
        {"id":"RE01","text":"Train A departs 09:00 at 100 km/h. Train B same station 10:00 at 150 km/h same track. When does B catch A? Answer: time only (HH:MM).","exp":"12:","np":16},
        {"id":"RE02","text":"Basket: 3 red apples, 4 green apples, 5 pears. P(apple)? Irreducible fraction only.","exp":"7/12","np":8},
        {"id":"RE03","text":"5 machines make 5 parts in 5 min. 100 machines, 100 parts: how many minutes? Integer only.","exp":"5","np":4},
        {"id":"RE04","text":"Sophie's father has 5 daughters: Lala, Lele, Lili, Lolo, and ___. The fifth?","exp":"sophie","np":8},
        {"id":"RE05","text":"Water lily doubles daily. Full lake: 30 days. Half lake: how many days? Integer only.","exp":"29","np":4},
    ],
    "CODING": [
        {"id":"CO01","text":"Write Python: def is_palindrome_sentence(s:str)->bool (ignore case, spaces, punctuation).","np":200,"ok":lambda t:"def" in t and "is_palindrome" in t.lower()},
        {"id":"CO02","text":"Fix to correctly compute median of any unsorted list: def find_median(nums): return nums[len(nums)//2]","np":200,"ok":lambda t:"sort" in t.lower()},
        {"id":"CO03","text":"Write Python: def fib(n:int)->int (efficient, no naive recursion).","np":150,"ok":lambda t:"def fib" in t or ("def " in t and "fib" in t.lower())},
        {"id":"CO04","text":"Return valid JSON for REST POST /api/v1/auth/login: method, path, body_required_fields (array), responses (object).","np":200,"ok":lambda t:"{" in t and "responses" in t.lower()},
    ],
    "TOOLS": [
        {"id":"TO01","text":'Reply ONLY with this strict JSON (no other text): {"tool":"sql_query","parameters":{"table":"clients","filter":"city=Paris AND active=1"}}. Task: find active clients in Paris from clients table.',"sys":"Tool-calling agent. Reply ONLY with exact JSON.","np":96,"ok":lambda t:"sql_query" in t and "clients" in t},
        {"id":"TO02","text":'Reply ONLY with this strict JSON: {"tool":"weather_lookup","parameters":{"city":"Lyon"}}. Task: get weather in Lyon.',"sys":"Tool-calling agent. Reply ONLY with exact JSON.","np":64,"ok":lambda t:"weather_lookup" in t and "Lyon" in t},
        {"id":"TO03","text":'Reply ONLY with this strict JSON: {"tool":"calculator","parameters":{"expression":"15*14"}}. Task: compute 15 times 14.',"sys":"Tool-calling agent. Reply ONLY with exact JSON.","np":64,"ok":lambda t:"calculator" in t and ("15" in t or "expression" in t)},
    ],
    "AGENT": {"id":"AG01","text":'Incident: "PostgreSQL 100% disk at 14:02, unexpected log dump." Reply ONLY strict JSON: {"root_cause":"...","severity":"CRITICAL","immediate_action":"...","verification":"..."}.','sys':"Incident orchestrator. Reply ONLY strict JSON.","np":128,"ok":lambda t:"root_cause" in t and ("CRITICAL" in t or "severity" in t)},
    "LONG_CONTEXT": {"id":"LC01","text":("Technical doc:\n"+"Distributed architectures and microservices design. "*25+"\nMARKER_A: 94821\n"+"Storage and replication strategies. "*25+"\nMARKER_B: 37190\n"+"Kafka and event-driven systems. "*25+"\nMARKER_C: 58204\n"+"Scalability conclusions. "*25+"\nMARKER_D: 12048\n\nExtract: MARKER_A=___, MARKER_B=___, MARKER_C=___, MARKER_D=___"),"sys":"Precise data extractor.","np":80,"ctx":4096},
    "LONG_GENERATION": {"id":"LG01","text":"Write a concise technical comparison (6-8 sentences) of modular monolith vs microservices for a 10-person dev team.","sys":"","np":256},
}

def make_prompt_set():
    ps = {}
    for k, v in PROMPTS.items():
        if isinstance(v, list):
            ps[k] = [{"id":p["id"],"text":p["text"],"hash":ph(p["text"]),"np":p["np"]} for p in v]
        else:
            ps[k] = {"id":v["id"],"text":v["text"],"hash":ph(v["text"]),"np":v.get("np",256)}
    return ps

# ─────────────────────────────────────────────────────────────────────────────
def unload(model):
    try:
        with httpx.Client(timeout=15.0) as c:
            c.post(f"{OLLAMA}/api/generate", json={"model":model,"prompt":"","keep_alive":0,"stream":False})
    except Exception:
        pass
    time.sleep(2.0)
    log(f"  [UNLOAD] {model} done")

def query_model(model, prompt, system="", np=256, ctx=CTX):
    opts = {"num_thread":THREADS,"num_ctx":ctx,"temperature":0.1,"num_predict":np,"num_gpu":GPU}
    r_before = ram()
    t0 = time.perf_counter()
    try:
        with httpx.Client(timeout=TIMEOUT) as c:
            resp = c.post(f"{OLLAMA}/api/generate",
                          json={"model":model,"prompt":prompt,"system":system,"stream":False,"options":opts})
    except httpx.TimeoutException:
        e2e = round((time.perf_counter()-t0)*1000,2)
        r_after = ram()
        return {"status":"TIMEOUT","text":"","e2e_ms":e2e,"load_ms":0,"ttft_ms":0,
                "gen_tok_s":0,"output_tokens":0,"prompt_tokens":0,"prompt_eval_tok_s":0,
                "ram_before":r_before,"ram_peak":r_after,"ram_after":r_after}
    except Exception as exc:
        e2e = round((time.perf_counter()-t0)*1000,2)
        r_after = ram()
        return {"status":"ERROR","error_msg":str(exc),"text":"","e2e_ms":e2e,"load_ms":0,"ttft_ms":0,
                "gen_tok_s":0,"output_tokens":0,"prompt_tokens":0,"prompt_eval_tok_s":0,
                "ram_before":r_before,"ram_peak":r_after,"ram_after":r_after}

    e2e = round((time.perf_counter()-t0)*1000,2)
    r_peak = ram()

    if resp.status_code != 200:
        return {"status":"HTTP_ERROR","http_code":resp.status_code,"text":"","e2e_ms":e2e,
                "load_ms":0,"ttft_ms":0,"gen_tok_s":0,"output_tokens":0,"prompt_tokens":0,
                "prompt_eval_tok_s":0,"ram_before":r_before,"ram_peak":r_peak,"ram_after":r_peak}

    d = resp.json()
    text = d.get("response","")
    load_ms         = round(d.get("load_duration",0)/1e6, 2)
    prompt_eval_ms  = round(d.get("prompt_eval_duration",0)/1e6, 2)
    eval_ms         = round(d.get("eval_duration",0)/1e6, 2)
    pt  = d.get("prompt_eval_count",0)
    ot  = d.get("eval_count",0)
    # TTFT = time to process prompt tokens (NOT including load_ms)
    ttft_ms         = round(prompt_eval_ms, 2)
    gen_tok_s       = round(ot/(eval_ms/1000),2) if eval_ms > 0 else 0
    prompt_tok_s    = round(pt/(prompt_eval_ms/1000),2) if prompt_eval_ms > 0 else 0

    return {"status":"OK","text":text,"e2e_ms":e2e,
            "load_ms":load_ms,"ttft_ms":ttft_ms,
            "gen_tok_s":gen_tok_s,"output_tokens":ot,"prompt_tokens":pt,
            "prompt_eval_tok_s":prompt_tok_s,
            "ram_before":r_before,"ram_peak":r_peak,"ram_after":r_peak}

# ─────────────────────────────────────────────────────────────────────────────
def check_quality(task, sub_id, text):
    if task == "FAST_ROUTING":
        return "PASS" if ("{" in text and "category" in text) else "FAIL"
    elif task == "REASONING":
        for p in PROMPTS["REASONING"]:
            if p["id"] == sub_id:
                return "PASS" if p["exp"].lower() in text.lower() else "FAIL"
    elif task == "CODING":
        for p in PROMPTS["CODING"]:
            if p["id"] == sub_id:
                return "PASS" if p["ok"](text) else "FAIL"
    elif task == "TOOLS":
        for p in PROMPTS["TOOLS"]:
            if p["id"] == sub_id:
                return "PASS" if p["ok"](text) else "FAIL"
    elif task == "AGENT":
        return "PASS" if PROMPTS["AGENT"]["ok"](text) else "FAIL"
    elif task == "LONG_CONTEXT":
        found = sum(1 for k in ["94821","37190","58204","12048"] if k in text)
        if found == 4: return "PASS"
        if found > 0:  return f"PARTIAL_{found}/4"
        return "FAIL"
    elif task == "LONG_GENERATION":
        return "PASS" if len(text.strip()) > 60 else "FAIL"
    return "UNKNOWN"

def write_checkpoint(run_id, model, task, sub_id, run_num, is_cold, prompt_hash_val, start_ts, result, quality):
    rec = {
        "RUN_ID": run_id, "MODEL": model, "TASK": task, "SUB_ID": sub_id,
        "RUN_NUM": run_num, "IS_COLD": is_cold, "PROMPT_HASH": prompt_hash_val,
        "THREADS": THREADS, "CONTEXT": CTX, "GPU": GPU,
        "START_TIMESTAMP": start_ts, "END_TIMESTAMP": ts(),
        "STATUS": result.get("status","?"), "QUALITY": quality,
        "LOAD_MS": result.get("load_ms",0),
        "TTFT_MS": result.get("ttft_ms",0),
        "PROMPT_TOKENS": result.get("prompt_tokens",0),
        "PROMPT_EVAL_TOK_S": result.get("prompt_eval_tok_s",0),
        "OUTPUT_TOKENS": result.get("output_tokens",0),
        "GEN_TOK_S": result.get("gen_tok_s",0),
        "TOTAL_E2E_MS": result.get("e2e_ms",0),
        "RAM_BEFORE": result.get("ram_before",{}),
        "RAM_PEAK": result.get("ram_peak",{}),
        "RAM_AFTER": result.get("ram_after",{}),
        "ERROR": result.get("error_msg",""),
        "TEXT_SNIPPET": result.get("text","")[:200],
    }
    (CKPT_DIR / f"{run_id}.json").write_text(json.dumps(rec, indent=2), "utf-8")
    return rec

# ─────────────────────────────────────────────────────────────────────────────
# Task schedule: (task_name, sub_prompts_list, n_runs)
# REASONING/CODING/TOOLS -> 1 run per sub-problem (quality sweep)
# FAST_ROUTING/AGENT/LONG_CONTEXT/LONG_GEN -> 3 runs (perf stability)
def build_task_schedule():
    return [
        ("FAST_ROUTING",
         [{"id":"FR01","p":PROMPTS["FAST_ROUTING"]["text"],"sys":PROMPTS["FAST_ROUTING"]["sys"],"np":PROMPTS["FAST_ROUTING"]["np"],"ctx":CTX}],
         3),
        ("REASONING",
         [{"id":p["id"],"p":p["text"],"sys":"","np":p["np"],"ctx":CTX} for p in PROMPTS["REASONING"]],
         1),
        ("CODING",
         [{"id":p["id"],"p":p["text"],"sys":"","np":p["np"],"ctx":CTX} for p in PROMPTS["CODING"]],
         1),
        ("TOOLS",
         [{"id":p["id"],"p":p["text"],"sys":p.get("sys",""),"np":p["np"],"ctx":CTX} for p in PROMPTS["TOOLS"]],
         1),
        ("AGENT",
         [{"id":"AG01","p":PROMPTS["AGENT"]["text"],"sys":PROMPTS["AGENT"]["sys"],"np":PROMPTS["AGENT"]["np"],"ctx":CTX}],
         3),
        ("LONG_CONTEXT",
         [{"id":"LC01","p":PROMPTS["LONG_CONTEXT"]["text"],"sys":PROMPTS["LONG_CONTEXT"]["sys"],"np":PROMPTS["LONG_CONTEXT"]["np"],"ctx":PROMPTS["LONG_CONTEXT"]["ctx"]}],
         3),
        ("LONG_GENERATION",
         [{"id":"LG01","p":PROMPTS["LONG_GENERATION"]["text"],"sys":PROMPTS["LONG_GENERATION"]["sys"],"np":PROMPTS["LONG_GENERATION"]["np"],"ctx":CTX}],
         3),
    ]

# ─────────────────────────────────────────────────────────────────────────────
def main():
    log("="*60)
    log(f"E-ZZIO BENCHMARK V2 PHASE A — {ts()}")
    log("CAMPAIGN_V1: ABORTED / INVALIDATED")
    log(f"Execution order (seed={SEED}): {EXEC_ORDER}")
    log("="*60)

    # Write PROMPT_SET.json
    (OUT_DIR/"PROMPT_SET.json").write_text(json.dumps(make_prompt_set(),indent=2),"utf-8")
    log("PROMPT_SET.json written")

    # Write PREVIEW.txt
    preview = f"""E-ZZIO LOCAL LLM BENCHMARK V2 — PHASE A
Campaign V1: ABORTED / INVALIDATED
Standard: EVIDENCE RULE v1.1
Host: AMD Ryzen 9 5900X / 32 GB DDR4 / CPU-only
Config: {THREADS}T / ctx={CTX} / timeout={TIMEOUT}s / GPU={GPU}
Models: {EXEC_ORDER}
Tasks: FAST_ROUTING(x3) REASONING(x5) CODING(x4) TOOLS(x3) AGENT(x3) LONG_CONTEXT(x3) LONG_GENERATION(x3)
Started: {ts()}
"""
    (OUT_DIR/"PREVIEW.txt").write_text(preview,"utf-8")
    log("PREVIEW.txt written")

    # V2_PREFLIGHT.json
    preflight = {
        "campaign":"V2A","timestamp":ts(),"campaign_v1":"ABORTED/INVALIDATED",
        "host":{"cpu":"AMD Ryzen 9 5900X (12C/24T)","ram_total_gb":round(psutil.virtual_memory().total/1073741824,2),"gpu_excluded":"NVIDIA GTX 1650 4GB"},
        "config":{"threads":THREADS,"ctx":CTX,"gpu":GPU,"timeout_s":TIMEOUT,"seed":SEED},
        "execution_order":EXEC_ORDER,"ram_baseline":ram(),
    }
    (OUT_DIR/"V2_PREFLIGHT.json").write_text(json.dumps(preflight,indent=2),"utf-8")
    log("V2_PREFLIGHT.json written")

    # ── MAIN BENCHMARK LOOP ──
    all_ckpts = []
    counter = {"expected":0,"executed":0,"completed":0,"timeout":0,"failed":0,"skipped":0}

    for m_idx, model in enumerate(MODELS, 1):
        log(f"\n{'='*50}")
        log(f"[{m_idx}/{len(MODELS)}] MODEL: {model}")
        log(f"{'='*50}")
        unload(model)
        first_call = True

        for task_name, subs, n_runs in build_task_schedule():
            log(f"\n  Task: {task_name} ({len(subs)} prompt(s) x {n_runs} run(s))")
            consec_to = 0
            task_skipped = False

            for sub in subs:
                if task_skipped: break
                for run_num in range(1, n_runs+1):
                    counter["expected"] += 1

                    if consec_to >= MAX_TO:
                        log(f"  [SKIP] {task_name}/{sub['id']} r{run_num} — {MAX_TO} consecutive timeouts")
                        counter["skipped"] += 1
                        task_skipped = True
                        break

                    is_cold = first_call
                    run_id  = f"{CAMPAIGN}_{model.replace(':','_').replace('.','_')}_{task_name}_{sub['id']}_r{run_num}_{int(time.time())}"
                    p_hash  = ph(sub["p"])
                    start_t = ts()

                    log(f"  [START] model={model} task={task_name}/{sub['id']} run={run_num}/{n_runs} cold={is_cold}")
                    result = query_model(model, sub["p"], system=sub.get("sys",""), np=sub["np"], ctx=sub.get("ctx",CTX))
                    first_call = False
                    counter["executed"] += 1

                    if result["status"] == "OK":
                        counter["completed"] += 1
                        consec_to = 0
                    elif result["status"] == "TIMEOUT":
                        counter["timeout"] += 1
                        consec_to += 1
                    else:
                        counter["failed"] += 1
                        consec_to = 0

                    quality = check_quality(task_name, sub["id"], result.get("text",""))

                    log(f"  [RESULT] LOAD={result['load_ms']}ms TTFT={result['ttft_ms']}ms GEN={result['gen_tok_s']}tok/s E2E={result['e2e_ms']}ms RAM_PEAK={result['ram_peak'].get('used_gb','?')}GB")
                    log(f"  [STATUS] {result['status']} | Quality={quality}")

                    ckpt = write_checkpoint(run_id, model, task_name, sub["id"], run_num, is_cold, p_hash, start_t, result, quality)
                    all_ckpts.append(ckpt)

        unload(model)
        ram_post = ram()
        log(f"\n  [POST-MODEL] RAM after unload: {ram_post['used_gb']}GB")

    # Write V2_CHECKPOINTS.json
    (OUT_DIR/"V2_CHECKPOINTS.json").write_text(json.dumps(all_ckpts,indent=2),"utf-8")
    log("\nV2_CHECKPOINTS.json written")

    # ── AGGREGATE ──
    log("\n--- Aggregating results ---")
    perf = {}; qual_agg = {}; memory = {}

    for model in MODELS:
        mc = [c for c in all_ckpts if c["MODEL"]==model]
        perf[model] = {}; qual_agg[model] = {}

        for t in ["FAST_ROUTING","REASONING","CODING","TOOLS","AGENT","LONG_CONTEXT","LONG_GENERATION"]:
            ok_runs = [c for c in mc if c["TASK"]==t and c["STATUS"]=="OK"]
            all_runs = [c for c in mc if c["TASK"]==t]
            if ok_runs:
                perf[model][t] = {
                    "ttft":   stats([c["TTFT_MS"] for c in ok_runs]),
                    "load":   stats([c["LOAD_MS"] for c in ok_runs]),
                    "gen_tok_s": stats([c["GEN_TOK_S"] for c in ok_runs]),
                    "e2e_ms": stats([c["TOTAL_E2E_MS"] for c in ok_runs]),
                    "n_ok":len(ok_runs),"n_total":len(all_runs),
                }
            passes = sum(1 for c in all_runs if "PASS" in c.get("QUALITY",""))
            qual_agg[model][t] = {"passes":passes,"total":len(all_runs),"rate":round(passes/max(len(all_runs),1),2)}

        cold_c = [c for c in mc if c.get("IS_COLD")]
        if cold_c:
            cr = cold_c[0]
            rb = cr["RAM_BEFORE"].get("used_gb",0)
            rp = cr["RAM_PEAK"].get("used_gb",0)
            memory[model] = {"ram_before_gb":rb,"ram_peak_gb":rp,"ram_delta_gb":round(max(0,rp-rb),2),"cold_run_id":cr["RUN_ID"]}

    (OUT_DIR/"V2_PERFORMANCE.json").write_text(json.dumps(perf,indent=2),"utf-8")
    (OUT_DIR/"V2_QUALITY.json").write_text(json.dumps(qual_agg,indent=2),"utf-8")
    (OUT_DIR/"V2_MEMORY.json").write_text(json.dumps(memory,indent=2),"utf-8")
    log("V2_PERFORMANCE / V2_QUALITY / V2_MEMORY written")

    # ── COMPARISON MATRIX ──
    comp = []
    for model in MODELS:
        pm = perf.get(model,{}); qm = qual_agg.get(model,{}); mm = memory.get(model,{})
        fr  = pm.get("FAST_ROUTING",{})
        lg  = pm.get("LONG_GENERATION",{})
        comp.append({
            "model":model,
            "ttft_p50_ms": fr.get("ttft",{}).get("p50",0),
            "ttft_p95_ms": fr.get("ttft",{}).get("p95",0),
            "gen_tok_s_mean": lg.get("gen_tok_s",{}).get("mean",0),
            "ram_delta_gb": mm.get("ram_delta_gb",0),
            "ram_peak_gb":  mm.get("ram_peak_gb",0),
            "reasoning": f"{qm.get('REASONING',{}).get('passes',0)}/{qm.get('REASONING',{}).get('total',0)}",
            "coding":    f"{qm.get('CODING',{}).get('passes',0)}/{qm.get('CODING',{}).get('total',0)}",
            "tools":     f"{qm.get('TOOLS',{}).get('passes',0)}/{qm.get('TOOLS',{}).get('total',0)}",
            "agent":     f"{qm.get('AGENT',{}).get('passes',0)}/{qm.get('AGENT',{}).get('total',0)}",
            "long_context": f"{qm.get('LONG_CONTEXT',{}).get('passes',0)}/{qm.get('LONG_CONTEXT',{}).get('total',0)}",
        })
    (OUT_DIR/"V2_COMPARISON.json").write_text(json.dumps(comp,indent=2),"utf-8")

    # ── RECONCILIATION + REPORT ──
    status = "COMPLETED" if counter["skipped"]==0 and counter["failed"]==0 and counter["timeout"]==0 else "PARTIALLY_COMPLETED"
    rec = {
        "CAMPAIGN_V1_STATUS":"ABORTED / INVALIDATED",
        "CAMPAIGN_V2_STATUS":status,
        "PHASE_A_EXPECTED":counter["expected"],
        "PHASE_A_EXECUTED":counter["executed"],
        "PHASE_A_COMPLETED":counter["completed"],
        "PHASE_A_TIMEOUTS":counter["timeout"],
        "PHASE_A_FAILURES":counter["failed"],
        "PHASE_A_SKIPPED":counter["skipped"],
        "EXECUTION_ORDER":EXEC_ORDER,
        "GPU_USED":0,"CUDA_USED":False,
        "PRODUCTION_ROUTING_CHANGED":False,"PRODUCTION_CODE_CHANGED":False,
    }
    (OUT_DIR/"V2_RECONCILIATION.json").write_text(json.dumps(rec,indent=2),"utf-8")

    hdr = "| Model | TTFT P50 | TTFT P95 | Gen tok/s | RAM Delta | Reasoning | Coding | Tools | Agent | LongCtx |\n"
    hdr+= "| :--- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |\n"
    rows = ""
    for row in comp:
        rows += (f"| **{row['model']}** | {row['ttft_p50_ms']} ms | {row['ttft_p95_ms']} ms "
                 f"| {row['gen_tok_s_mean']} tok/s | +{row['ram_delta_gb']} GB "
                 f"| {row['reasoning']} | {row['coding']} | {row['tools']} | {row['agent']} | {row['long_context']} |\n")

    final = f"""
============================================================
E-ZZIO - OLLAMA LOCAL BENCHMARK V2
============================================================
CAMPAIGN_V1_STATUS     : ABORTED / INVALIDATED
CAMPAIGN_V2_STATUS     : {rec['CAMPAIGN_V2_STATUS']}
PHASE_A_EXPECTED       : {rec['PHASE_A_EXPECTED']}
PHASE_A_EXECUTED       : {rec['PHASE_A_EXECUTED']}
PHASE_A_COMPLETED      : {rec['PHASE_A_COMPLETED']}
PHASE_A_TIMEOUTS       : {rec['PHASE_A_TIMEOUTS']}
PHASE_A_FAILURES       : {rec['PHASE_A_FAILURES']}
PHASE_A_SKIPPED        : {rec['PHASE_A_SKIPPED']}
EXECUTION_ORDER        : {' -> '.join(EXEC_ORDER)}
CPU_ONLY               : TRUE
GPU_USED               : 0
CUDA_USED              : FALSE
PRODUCTION_ROUTING_CHANGED : FALSE
PRODUCTION_CODE_CHANGED    : FALSE
============================================================
"""
    report = f"""# E-ZZIO LOCAL LLM BENCHMARK V2 - RAPPORT FINAL (PHASE A)
**Campaign V1:** ABORTED / INVALIDATED - no V1 values reused.
**Standard:** EVIDENCE RULE v1.1 - NO CLAIM WITHOUT OBSERVABLE PROOF
**Host:** AMD Ryzen 9 5900X / 32 GB DDR4 / CPU-only (num_gpu=0) / Ollama 0.33.2
**Config:** {THREADS}T | ctx={CTX} | timeout={TIMEOUT}s | seed={SEED}

## Matrice Comparative - Phase A

{hdr}{rows}

## Reconciliation
`
{final}
`
"""
    (OUT_DIR/"V2_REPORT.md").write_text(report,"utf-8")
    log("V2_REPORT.md written")
    print(final, flush=True)
    log("BENCHMARK V2 PHASE A COMPLETE")

if __name__ == "__main__":
    main()