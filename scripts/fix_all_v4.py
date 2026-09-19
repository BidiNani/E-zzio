"""fix_all_v4.py - Bugs reels F811/B023/B017 + I001/E401."""
import ast
import datetime
import pathlib
import subprocess
import sys

ROOT = pathlib.Path(r"G:\AI\E-zzio")
PY   = str(ROOT / ".venv" / "Scripts" / "python.exe")
LOG  = ROOT / "state" / "ruff_logs" / f"fix_v4_{datetime.datetime.now():%Y%m%d_%H%M%S}.log"
LOG.parent.mkdir(parents=True, exist_ok=True)

def log(msg, level="INFO"):
    line = f"[{datetime.datetime.now():%H:%M:%S}] [{level}] {msg}"
    print(line, flush=True)
    with LOG.open("a", encoding="utf-8") as f:
        f.write(line + "\n")

def run(args, cwd=ROOT):
    r = subprocess.run(args, cwd=str(cwd), capture_output=True, text=True,
                       encoding="utf-8", errors="replace")
    return r.returncode, r.stdout, r.stderr

def git(*args):
    rc, out, err = run(["git"] + list(args))
    return rc, out.strip(), err.strip()

def ast_check():
    bad = []
    for f in ROOT.rglob("*.py"):
        if any(x in f.parts for x in (".venv",".git","__pycache__",
                                       ".ruff_cache","node_modules",
                                       "state","_backup_ruff","_archive")):
            continue
        try:
            ast.parse(f.read_text(encoding="utf-8"))
        except SyntaxError as e:
            bad.append(f"{f}:{e.lineno}: {e.msg}")
    return bad

log("=== FIX v4 START ===", "CYAN")
rc, safe_ref, _ = git("rev-parse", "HEAD")
log(f"Rollback : {safe_ref}", "GRAY")

# ============================================================
# 1. INSPECTION : dump tous les problemes F811/B023/B017
# ============================================================
log("--- 1. INSPECTION des bugs reels ---", "CYAN")

def dump_context(rel, line_no, ctx_before=2, ctx_after=15):
    p = ROOT / rel
    if not p.exists(): return
    lines = p.read_text(encoding="utf-8").splitlines()
    start = max(0, line_no - ctx_before - 1)
    end = min(len(lines), line_no + ctx_after)
    log(f"  ### {rel}:{line_no} ###", "YELLOW")
    for i in range(start, end):
        marker = ">>" if i + 1 == line_no else "  "
        log(f"  {marker} L{i+1}: {lines[i]}")

# F811 - fabric.py
dump_context("core/models/fabric.py", 380, 0, 30)
dump_context("core/models/fabric.py", 485, 0, 30)

# F811 - metrics.py
dump_context("core/observability/metrics.py", 249, 0, 15)
dump_context("core/observability/metrics.py", 713, 0, 15)

# F811 - safe_actions.py
for ln in (161, 506, 190, 554, 218, 585, 385, 683):
    dump_context("core/safe_actions.py", ln, 0, 8)

# B023 - semantic_evidence.py
dump_context("core/capabilities/semantic_evidence.py", 129, 15, 5)

# B023 - gemini_provider.py
dump_context("providers/gemini_provider.py", 64, 10, 10)

# B017 - tests
dump_context("tests/test_agent_tracer_telemetry.py", 26, 2, 4)
dump_context("tests/test_chaos_bounded.py", 145, 2, 5)
dump_context("tests/test_studio_builder.py", 35, 2, 4)
dump_context("tests/test_studio_scaffolder.py", 41, 2, 4)

log("--- FIN INSPECTION ---", "CYAN")

# ============================================================
# 2. Quick wins : I001 + E401 (auto-fix ruff)
# ============================================================
log("--- 2. I001 + E401 auto-fix ---", "CYAN")
rc, out, err = run([PY, "-m", "ruff", "check", ".",
                   "--select", "I001,E401", "--fix", "--no-cache", "--quiet"])
log(f"  exit : {rc}")

# ============================================================
# 3. AST check
# ============================================================
log("--- 3. AST check ---", "CYAN")
bad = ast_check()
if bad:
    log(f"AST CASSE : {len(bad)}", "ERROR")
    for b in bad[:10]: log("  " + b)
    git("reset", "--hard", safe_ref)
    log("Rollback", "RED")
    sys.exit(1)
log("AST OK", "OK")

# ============================================================
# 4. Frozen core regen
# ============================================================
rc, out, err = run([PY, "-c",
    "from core.frozen_core.manifest import regenerate_manifest; "
    "regenerate_manifest(); print('OK')"])
log(f"Frozen regen : {out.strip()}")

# ============================================================
# 5. Pytest
# ============================================================
log("--- 5. pytest ---", "CYAN")
rc, out, err = run([PY, "-m", "pytest", "tests/", "-q", "--tb=line", "--no-header"])
for line in (out + err).splitlines()[-15:]:
    log("  " + line)
if rc != 0:
    log("TESTS CASSES - rollback", "ERROR")
    git("reset", "--hard", safe_ref)
    sys.exit(1)
log("Tests OK", "OK")

# ============================================================
# 6. Stats
# ============================================================
log("--- 6. Stats ---", "CYAN")
rc, out, err = run([PY, "-m", "ruff", "check", ".", "--statistics", "--no-cache"])
for line in (out + err).splitlines()[-30:]:
    log("  " + line)

# ============================================================
# 7. Commit (I001/E401 uniquement)
# ============================================================
git("add", "-A")
rc, out, err = run(["git", "commit", "-m", "chore(ruff): I001,E401 fixes"])
log(out or err)

log("=== FIX v4 TERMINE ===", "GREEN")
log(f"Log : {LOG}", "GRAY")
