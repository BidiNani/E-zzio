"""fix_all.py - Correction ruff E-ZzIO (Python only, robuste)."""
import ast
import datetime
import json
import pathlib
import subprocess
import sys

ROOT = pathlib.Path(r"G:\AI\E-zzio")
PY   = str(ROOT / ".venv" / "Scripts" / "python.exe")
LOG  = ROOT / "state" / "ruff_logs" / f"fix_all_{datetime.datetime.now():%Y%m%d_%H%M%S}.log"
LOG.parent.mkdir(parents=True, exist_ok=True)

def log(msg, level="INFO"):
    line = f"[{datetime.datetime.now():%H:%M:%S}] [{level}] {msg}"
    print(line, flush=True)
    with LOG.open("a", encoding="utf-8") as f:
        f.write(line + "\n")

def run(args, cwd=ROOT, capture=True):
    r = subprocess.run(args, cwd=str(cwd), capture_output=True, text=True,
                       encoding="utf-8", errors="replace")
    return r.returncode, r.stdout, r.stderr

def git(*args, check=False):
    rc, out, err = run(["git"] + list(args))
    if check and rc != 0:
        raise RuntimeError(f"git {' '.join(args)} failed: {err}")
    return out.strip()

def ast_check():
    bad = []
    for p in ROOT.rglob("*.py"):
        if any(x in p.parts for x in (".venv",".git","__pycache__",
                                       ".ruff_cache","node_modules",
                                       "state","_backup_ruff","_archive")):
            continue
        try:
            ast.parse(p.read_text(encoding="utf-8"))
        except SyntaxError as e:
            bad.append(f"{p}:{e.lineno}: {e.msg}")
    return bad

def ruff_count(select):
    rc, out, err = run([PY, "-m", "ruff", "check", ".", "--select", select,
                       "--output-format=json", "--no-cache"])
    try:
        return len(json.loads(out or "[]"))
    except Exception:
        return -1

def ruff_fix(select=None, unsafe=False):
    args = [PY, "-m", "ruff", "check", ".", "--fix", "--no-cache", "--quiet"]
    if select:
        args += ["--extend-select", select]
    if unsafe:
        args += ["--unsafe-fixes"]
    rc, out, err = run(args)
    return out + err

# ============================================================
log("=== FIX ALL START ===", "CYAN")

# 0. Safety
dirty = git("status", "--porcelain")
if dirty:
    log("Repo pas propre, commit securite", "WARN")
    git("add", "-A")
    git("commit", "-m", "wip: pre-fix-all")

safe_ref = git("rev-parse", "HEAD")
log(f"Rollback point : {safe_ref}", "GRAY")

# 1. Elargir select dans pyproject.toml
log("--- 1. pyproject.toml select ---", "CYAN")
pp = ROOT / "pyproject.toml"
content = pp.read_text(encoding="utf-8")
old = '''[tool.ruff.lint]
select = [
    "W605", # Invalid escape sequence (explicite, ne plus dépendre du seul groupe "W")
    "E",   # Erreurs standard
    "F",   # Erreurs logiques Pyflakes
    "W",   # Warnings
]
ignore = [
    "E501",    # Longueur de ligne libre (prompts/logs)'''
new = '''[tool.ruff.lint]
select = [
    "E", "F", "W", "W605",
    "B",
    "C4",
    "UP",
]
ignore = [
    "E501",
    "B904",
    "UP042",'''
if old in content:
    pp.write_text(content.replace(old, new), encoding="utf-8")
    log("pyproject.toml : select elargi", "OK")
else:
    log("pyproject.toml : bloc exact non trouve - SKIP", "WARN")

# 2. Ruff fix global (safe + unsafe)
log("--- 2. ruff --fix --unsafe-fixes ---", "CYAN")
out = ruff_fix(unsafe=True)
for line in out.splitlines()[:50]:
    log("  " + line)

# 3. AST check
log("--- 3. AST check ---", "CYAN")
bad = ast_check()
if bad:
    log(f"AST CASSE sur {len(bad)} fichier(s)", "ERROR")
    for b in bad[:10]:
        log("  " + b)
    git("reset", "--hard", safe_ref)
    log("Rollback OK", "RED")
    sys.exit(1)
log("AST OK", "OK")

# 4. Corrections manuelles
log("--- 4. Corrections manuelles ---", "CYAN")

fixes = [
    # (fichier, ancien, nouveau, label)
    ("tests/test_research_fabric.py",
     '    mk = lambda loc, c: SourceResult("t", "t", loc, c)',
     '    def mk(loc, c):\n        return SourceResult("t", "t", loc, c)',
     "E731"),
    ("tests/test_web_ui.py",
     '        assert False, "Should have thrown 422 HTTP error"',
     '        raise AssertionError("Should have thrown 422 HTTP error")',
     "B011"),
    ("core/models/router.py",
     'class TaggedPreRoutingStrategy(Generic[_PreRoutingStrategyT_co]):',
     'class TaggedPreRoutingStrategy[_PreRoutingStrategyT_co]:',
     "UP046"),
    ("core/cognitive_engine/founding_kernel_proof.py",
     '    for rel_path, node in nodes.items():',
     '    for _rel_path, node in nodes.items():',
     "B007#1"),
    ("scripts/cleanup_v2_engine.py",
     '        for sb, files in size_buckets.items():',
     '        for _sb, files in size_buckets.items():',
     "B007#2"),
]

for rel, old_s, new_s, label in fixes:
    p = ROOT / rel
    if not p.exists():
        log(f"  [SKIP] {label} : fichier absent", "GRAY")
        continue
    src = p.read_text(encoding="utf-8")
    if old_s in src:
        p.write_text(src.replace(old_s, new_s), encoding="utf-8")
        log(f"  [OK] {label} ({rel})", "OK")
    else:
        log(f"  [SKIP] {label} : pattern introuvable", "GRAY")

# 5. AST #2
log("--- 5. AST #2 ---", "CYAN")
bad = ast_check()
if bad:
    log(f"AST CASSE sur {len(bad)} fichier(s)", "ERROR")
    for b in bad[:10]:
        log("  " + b)
    git("reset", "--hard", safe_ref)
    log("Rollback OK", "RED")
    sys.exit(1)
log("AST OK", "OK")

# 6. Pytest
log("--- 6. pytest tests/ ---", "CYAN")
rc, out, err = run([PY, "-m", "pytest", "tests/", "-q", "--tb=short",
                   "--no-header"], capture=False)
# On re-run avec capture pour extraire le résumé
rc, out, err = run([PY, "-m", "pytest", "tests/", "-q", "--tb=short",
                   "--no-header"])
combined = out + err
for line in combined.splitlines()[-25:]:
    log("  " + line)

if rc != 0:
    log("TESTS CASSES - rollback", "ERROR")
    git("reset", "--hard", safe_ref)
    log("Rollback OK", "RED")
    sys.exit(1)
log("Tests OK", "OK")

# 7. Stats
log("--- 7. Stats ruff ---", "CYAN")
rc, out, err = run([PY, "-m", "ruff", "check", ".", "--statistics", "--no-cache"])
for line in (out + err).splitlines()[-30:]:
    log("  " + line)

# 8. Commit
log("--- 8. Commit ---", "CYAN")
git("add", "-A")
rc, out, err = run(["git", "commit", "-m",
                   "chore(ruff): fix global E/F/W/B/C4/UP + manuels"])
log(out or err)

log("=== FIX ALL TERMINE ===", "CYAN")
log(f"Log : {LOG}", "GRAY")
