def extract_code_block(text: str) -> str:
    if "```python" in text:
        return text.split("```python")[1].split("```")[0]
    if "```" in text:
        return text.split("```")[1].split("```")[0]
    return text

def safe_str(v) -> str:
    return "N/A" if v is None else str(v)


# ── 2. BLIND BENCHMARK ───────────────────────────────────────────────────────
async def run_model(client: httpx.AsyncClient, blind_name: str, real_name: str, size_gb: float) -> dict:
    timeout = TIMEOUT_LARGE if size_gb >= 10.0 else TIMEOUT_COMPACT
    model_class = "LARGE_MODEL" if size_gb >= 10.0 else "COMPACT_MODEL"

    print(f"\n{'='*72}")
    print(f"  [RUNNING] {blind_name}  [{size_gb} GB, timeout={timeout}s]")
    print(f"{'='*72}")

    # Le dictionnaire d'enregistrement ne contient PAS l'identité réelle (Blind strict)
    rec = {
        "BlindModel": blind_name,
        "ModelClass": model_class,
        "AllocatedTimeout": timeout,
        "EngineHealth": "UNKNOWN",
        "EngineError": "",
    }

    # S0 – Speed
    r_cold = await ollama_call(client, real_name, P_SPEED,  timeout)
    r_warm = await ollama_call(client, real_name, P_SPEED2, timeout)
    wd = r_warm["data"]
    eval_count    = wd.get("eval_count", 0)
    eval_dur_ns   = wd.get("eval_duration", 1) or 1
    tokens_per_s  = round(eval_count / (eval_dur_ns / 1e9), 2) if eval_count else 0.0
    warm_resp = wd.get("response", "").strip()
    speed_pass = r_warm["ok"] and len(warm_resp) > 0

    rec.update({"WarmLatencySec": r_warm["dur"], "EvalTokensPerSec": tokens_per_s, "SpeedPass": speed_pass})
    print(f"  [S0] Speed       : {'PASS' if speed_pass else 'FAIL'} ({tokens_per_s} tok/s)")
    if not r_warm["ok"]:
        rec["EngineHealth"], rec["EngineError"] = "UNHEALTHY_CPU", str(r_warm["err"] or "")

    # S1 – PowerShell (Strict)
    r_ps = await ollama_call(client, real_name, P_POWERSHELL, timeout)
    ps_text = r_ps["data"].get("response", "").lower()
    if not ps_text.strip():
        rec["PowerShellStatus"] = "EMPTY_RESPONSE"
        rec["PowerShellPass"] = False
    else:
        # VERIFICATION STRICTE : Cmdlet + Bloc try/catch exigé
        ps_pass = r_ps["ok"] and "get-filehash" in ps_text and "sha256" in ps_text and "try" in ps_text and "catch" in ps_text
        rec["PowerShellPass"] = ps_pass
        rec["PowerShellStatus"] = "PASS" if ps_pass else "FAIL"
    print(f"  [S1] PowerShell  : {rec['PowerShellStatus']}")

    # S2 – Python AST
    r_py = await ollama_call(client, real_name, P_PYTHON, timeout)
    py_text = r_py["data"].get("response", "")
    if not py_text.strip():
        rec["PythonStatus"], rec["PythonPass"], rec["PythonASTValid"] = "EMPTY_RESPONSE", False, False
    else:
        code = extract_code_block(py_text)
        try:
            ast.parse(code)
            py_ast_ok = True
        except Exception:
            py_ast_ok = False
        py_pass = r_py["ok"] and py_ast_ok and "wait_for" in py_text and "FetchTimeoutException" in py_text
        rec["PythonPass"], rec["PythonStatus"], rec["PythonASTValid"] = py_pass, "PASS" if py_pass else "FAIL", py_ast_ok
    print(f"  [S2] Python AST  : {rec['PythonStatus']}")

    # S3 – Logic (Strict Sequence)
    r_logic = await ollama_call(client, real_name, P_LOGIC, timeout)
    logic_text = r_logic["data"].get("response", "").upper()
    if not logic_text.strip():
        rec["LogicStatus"], rec["LogicPass"] = "EMPTY_RESPONSE", False
    else:
        # Extraction séquentielle stricte par Regex (seulement les lettres isolées de A à E)
        letters = re.findall(r'\b[A-E]\b', logic_text)
        seq = []
        for l in letters:
            if l not in seq: seq.append(l)

        if len(seq) == 5:
            pa, pb, pc, pd, pe = [seq.index(x) for x in "ABCDE"]
            logic_pass = (pa < pb < pc < pd) and (pe < pd)
        else:
            logic_pass = False

        rec["LogicPass"], rec["LogicStatus"] = logic_pass, "PASS" if logic_pass else "FAIL"
    print(f"  [S3] Logic       : {rec['LogicStatus']}")

    # S4 – Context
    r_ctx = await ollama_call(client, real_name, P_CONTEXT, timeout)
    ctx_text = r_ctx["data"].get("response", "").lower()
    if not ctx_text.strip():
        rec["ContextStatus"], rec["ContextPass"] = "EMPTY_RESPONSE", False
    else:
        has_fts5 = "2.62" in ctx_text or "fts5" in ctx_text
        has_health = any(w in ctx_text for w in ["sain", "sante", "certifi", "ok", "operati"])
        ctx_pass = r_ctx["ok"] and (has_fts5 or has_health)
        rec["ContextPass"], rec["ContextStatus"] = ctx_pass, "PASS" if ctx_pass else "FAIL"
    print(f"  [S4] Context     : {rec['ContextStatus']}")

    # S5 – Strict JSON Schema
    r_json = await ollama_call(client, real_name, P_JSON, timeout, is_json=True)
    json_raw = r_json["data"].get("response", "").strip()
    parsed_s5 = None
    if not json_raw:
        rec["JsonStatus"], rec["JsonPass"] = "EMPTY_RESPONSE", False
    else:
        try:
            pj = json.loads(json_raw)
            expected_keys = {"system", "status", "target_id", "score"}

            # VERIFICATION STRICTE: Exact keys, exact values, strict explicit Python typing
            # L'utilisation de `type(x) is` exclut les booléens qui passeraient avec `isinstance(True, int)`
            sys_ok    = type(pj.get("system")) is str and pj["system"] == "E-ZZIO"
            stat_ok   = type(pj.get("status")) is str and pj["status"] == "CERTIFIED"
            target_ok = type(pj.get("target_id")) is int and pj["target_id"] == 42
            score_ok  = type(pj.get("score")) in (int, float) and pj["score"] == 100

            if set(pj.keys()) == expected_keys and sys_ok and stat_ok and target_ok and score_ok:
                json_pass = True
                parsed_s5 = pj
            else:
                json_pass = False
            rec["JsonStatus"] = "PASS" if json_pass else "FAIL"
        except Exception:
            json_pass, rec["JsonStatus"] = False, "INVALID_JSON"
        rec["JsonPass"] = json_pass
    print(f"  [S5] JSON Strict : {rec['JsonStatus']}")

    # S6 – Determinism (Structural Equality)
    r_det = await ollama_call(client, real_name, P_JSON, timeout, is_json=True)
    det_raw = r_det["data"].get("response", "").strip()
    try:
        pd2 = json.loads(det_raw)
        # VERIFICATION STRICTE : Égalité pure des dictionnaires S5 et S6
        det_pass = (parsed_s5 is not None) and (pj == pd2)
    except Exception:
        det_pass = False
    rec["DeterminismPass"] = det_pass
    print(f"  [S6] Determinism : {'PASS' if det_pass else 'FAIL'}")

    return rec


# ── 3. MAIN ORCHESTRATOR ─────────────────────────────────────────────────────
async def main():
    print(f"\n{'='*72}")
    print(f"  E-ZZIO MODEL QUALIFICATION GATE v{VERSION}")
    print(f"  Run ID: {run_id}")
    print(f"{'='*72}\n")

    # PREFLIGHT
    with httpx.Client(timeout=15.0) as client:
        resp = client.get(f"{OLLAMA_URL}/api/tags")
        assert resp.status_code == 200, "Ollama unavailable"
        all_models = resp.json().get("models", [])

    EMBED_PATTERNS = ["embed", "bge", "bert", "nomic"]
    gen_models = [m for m in all_models if not any(p in m["name"].lower() for p in EMBED_PATTERNS)]

    LETTERS = list("ABCDEFGHIJKLMNOPQRSTUVWXYZ")
    blind_map = {}
    for i, m in enumerate(gen_models):
        blind_map[f"MODEL_{LETTERS[i]}"] = {
            "real_name": m["name"],
            "size_gb": round(m["size"] / (1024**3), 3),
            "parameter_size": m.get("details", {}).get("parameter_size", "N/A"),
            "quantization": m.get("details", {}).get("quantization_level", "N/A")
        }

    print(f"Preflight: {len(gen_models)} models loaded for blind assignment.\n")

    # BENCHMARK
    results = []
    async with httpx.AsyncClient() as async_client:
        for blind_id, info in blind_map.items():
            r = await run_model(async_client, blind_id, info["real_name"], info["size_gb"])
            r["ParameterSize"] = info["parameter_size"]
            r["SizeGB"] = info["size_gb"]
            r["Quantization"] = info["quantization"]
            results.append(r)

    # POSTFLIGHT INTEGRITY
    print("\n--- POSTFLIGHT CORE INTEGRITY ---")
    core_ok = True
    core_checks = []
    for rel in CORE_FILES:
        h_after = sha256_file(ROOT / rel)
        h_before = core_before[rel]
        identical = (h_before == h_after)
        if not identical: core_ok = False
        core_checks.append({"path": rel, "before": h_before, "after": h_after, "intact": identical})
        print(f"  {'OK' if identical else 'TAMPERED'}: {rel}")

    # SCORING & FAIL-CLOSED HIERARCHY
    global_verdict = ""
    if not core_ok:
        print("\n[!] CRITICAL: Core altered during benchmark. Enforcing GLOBAL_FAIL_CLOSED.")
        global_verdict = "GLOBAL_FAIL_CLOSED"
        for r in results:
            # On mesure tout de même la performance brute, mais le contrat est caduc
            passes = sum([r.get(k, False) for k in ["SpeedPass", "PowerShellPass", "PythonPass", "LogicPass", "ContextPass", "JsonPass", "DeterminismPass"]])
            r["ContractScore"] = round((passes / 7) * 100, 2)
            r["PassCount"] = passes
            r["ContractStatus"] = "CORE_TAMPERED"  # Écrase et annule toute qualification
    else:
        for r in results:
            passes = sum([r.get(k, False) for k in ["SpeedPass", "PowerShellPass", "PythonPass", "LogicPass", "ContextPass", "JsonPass", "DeterminismPass"]])
            score = round((passes / 7) * 100, 2)
            r["ContractScore"] = score
            r["PassCount"] = passes

            if r.get("EngineHealth") == "UNHEALTHY_CPU": r["ContractStatus"] = "MODEL_TEST_FAIL"
            elif score >= 85.0: r["ContractStatus"] = "QUALIFIED"
            elif score >= 57.0: r["ContractStatus"] = "PARTIALLY_QUALIFIED"
            else: r["ContractStatus"] = "UNQUALIFIED"

        qualified = len([r for r in results if r["ContractStatus"] == "QUALIFIED"])
        partial = len([r for r in results if r["ContractStatus"] == "PARTIALLY_QUALIFIED"])

        if qualified == len(results) and len(results) > 0: global_verdict = "ALL_MODELS_QUALIFIED"
        elif qualified or partial: global_verdict = "PARTIAL_MODELS_QUALIFIED"
        else: global_verdict = "NO_MODELS_QUALIFIED"

    # REVEAL & EXPORT
    print("\n--- BLIND REVEAL & RANKING ---")
    # C'est ici, et seulement ici, que l'identité réelle rejoint l'objet de résultats
    for r in results:
        r["RealModel"] = blind_map[r["BlindModel"]]["real_name"]

    for r in sorted(results, key=lambda x: x["ContractScore"], reverse=True):
        bar = "#" * int(r["ContractScore"] / 10)
        print(f"  {r['BlindModel']} -> {r['RealModel']:<25} | {r['ContractScore']:>6}/100 {bar:<10} [{r['ContractStatus']}]")

    # JSON EXPORT
    json_data = {
        "Engine": "E-ZZIO MQG", "Version": VERSION, "RunId": run_id, "Timestamp": timestamp,
        "QualificationVerdict": global_verdict,
        "CoreIntegrity": {"intact": core_ok, "files": core_checks},
        "BlindMap": blind_map,
        "Results": results
    }
    json_path.write_text(json.dumps(json_data, indent=2, ensure_ascii=False), encoding="utf-8")

    # CSV EXPORT
    CSV_FIELDS = ["BlindModel", "RealModel", "ModelClass", "ParameterSize", "SizeGB", "Quantization", "ContractStatus", "ContractScore", "AllocatedTimeout", "WarmLatencySec", "EvalTokensPerSec", "PowerShellStatus", "PythonStatus", "LogicStatus", "ContextStatus", "JsonStatus"]
    csv_lines = [",".join(f'"{f}"' for f in CSV_FIELDS)]
    for r in results:
        csv_lines.append(",".join(f'"{safe_str(r.get(f, ""))}"' for f in CSV_FIELDS))
    csv_path.write_text("\n".join(csv_lines) + "\n", encoding="utf-8")

    # MARKDOWN EXPORT
    header = "| Blind ID | Real Model | Params | Quant | Score | Status | PS | PY | Logic | CTX | JSON | DET |"
    sep = "|---|---|---|---|---|---|---|---|---|---|---|---|"
    md_rows = [header, sep]
    for r in results:
        det = 'PASS' if r.get('DeterminismPass') else 'FAIL'
        md_rows.append(f"| `{r['BlindModel']}` | `{r.get('RealModel', 'N/A')}` | {r.get('ParameterSize')} | {r.get('Quantization')} | **{r.get('ContractScore')}/100** | `{r.get('ContractStatus')}` | {r.get('PowerShellStatus')} | {r.get('PythonStatus')} | {r.get('LogicStatus')} | {r.get('ContextStatus')} | {r.get('JsonStatus')} | {det} |")

    md_path.write_text(f"# E-ZZIO MQG v{VERSION}\n\n**Verdict Global:** `{global_verdict}`\n\n" + "\n".join(md_rows), encoding="utf-8")
    print(f"\n[OK] Rapports générés dans: {report_dir}")

if __name__ == "__main__":
    asyncio.run(main())
