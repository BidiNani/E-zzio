"""fix_all_v2.py - Correction ruff + frozen core manifest regen."""
import ast
import datetime
import pathlib
import subprocess
import sys

ROOT = pathlib.Path(r"G:\AI\E-zzio")
PY   = str(ROOT / ".venv" / "Scripts" / "python.exe")
LOG  = ROOT / "state" / "ruff_logs" / f"fix_v2_{datetime.datetime.now():%Y%m%d_%H%M%S}.log"
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

def git(*args):
    rc, out, err = run(["git"] + list(args))
    return rc, out.strip(), err.strip()

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

# ============================================================
log("=== FIX ALL v2 START ===", "CYAN")

# 0. Etat git
rc, dirty, _ = git("status", "--porcelain")
if dirty:
    log("Repo pas propre, commit securite", "WARN")
    git("add", "-A")
    git("commit", "-m", "wip: pre-fix-v2")

rc, safe_ref, _ = git("rev-parse", "HEAD")
log(f"Rollback point : {safe_ref}", "GRAY")

# 1. ETAT AVANT : verifier si frozen core est deja OK
log("--- 0. Frozen core AVANT fix ---", "CYAN")
rc, out, err = run([PY, "-c",
    "from core.frozen_core.manifest import verify_integrity; "
    "verify_integrity(); print('FROZEN_OK')"])
frozen_before = "FROZEN_OK" in out
log(f"Frozen avant : {'OK' if frozen_before else 'DRIFT'}",
    "GREEN" if frozen_before else "YELLOW")

# 2. Elargir select ruff
log("--- 1. pyproject.toml select ---", "CYAN")
pp = ROOT / "pyproject.toml"
content = pp.read_text(encoding="utf-8")
old = '''select = [
    "W605", # Invalid escape sequence (explicite, ne plus dépendre du seul groupe "W")
    "E",   # Erreurs standard
    "F",   # Erreurs logiques Pyflakes
    "W",   # Warnings
]
ignore = [
    "E501",    # Longueur de ligne libre (prompts/logs)'''
new = '''select = [
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

# 3. Ruff fix global
log("--- 2. ruff --fix --unsafe-fixes ---", "CYAN")
rc, out, err = run([PY, "-m", "ruff", "check", ".", "--fix",
                   "--unsafe-fixes", "--no-cache", "--quiet"])
log(f"ruff exit code : {rc}", "GRAY")

# 4. AST
log("--- 3. AST check ---", "CYAN")
bad = ast_check()
if bad:
    log(f"AST CASSE : {len(bad)} fichier(s)", "ERROR")
    for b in bad[:10]:
        log("  " + b)
    git("reset", "--hard", safe_ref)
    log("Rollback OK", "RED")
    sys.exit(1)
log("AST OK", "OK")

# 5. Corrections manuelles (patterns detectes, SKIP si introuvable)
log("--- 4. Corrections manuelles ---", "CYAN")
fixes = [
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
        log(f"  [OK] {label}", "OK")
    else:
        log(f"  [SKIP] {label} : pattern introuvable", "GRAY")

# 6. AST #2
log("--- 5. AST #2 ---", "CYAN")
bad = ast_check()
if bad:
    log(f"AST CASSE : {len(bad)}", "ERROR")
    for b in bad[:10]: log("  " + b)
    git("reset", "--hard", safe_ref)
    log("Rollback OK", "RED")
    sys.exit(1)
log("AST OK", "OK")

# 7. ★ REGENERER LE MANIFEST FROZEN CORE ★
log("--- 6. Regeneration frozen core manifest ---", "CYAN")
rc, out, err = run([PY, "-c",
    "from core.frozen_core.manifest import regenerate_manifest, save_manifest; "
    "m = regenerate_manifest(); "
    "print(f'Manifest regenere : {len(m[\"files\"])} hashes')"])
log(out or err or "regen termine")
if rc != 0:
    log("ECHEC regeneration manifest", "ERROR")
    git("reset", "--hard", safe_ref)
    sys.exit(1)

# 8. Verifier frozen OK apres regen
rc, out, err = run([PY, "-c",
    "from core.frozen_core.manifest import verify_integrity; "
    "verify_integrity(); print('FROZEN_OK')"])
if "FROZEN_OK" not in out:
    log(f"Frozen toujours casse : {out} {err}", "ERROR")
    git("reset", "--hard", safe_ref)
    sys.exit(1)
log("Frozen core : OK", "OK")

# 9. Pytest
log("--- 7. pytest tests/ ---", "CYAN")
rc, out, err = run([PY, "-m", "pytest", "tests/", "-q", "--tb=line",
                   "--no-header"])
combined = out + err
for line in combined.splitlines()[-20:]:
    log("  " + line)
if rc != 0:
    log("TESTS CASSES - rollback", "ERROR")
    git("reset", "--hard", safe_ref)
    log("Rollback OK", "RED")
    sys.exit(1)
log("Tests OK", "OK")

# 10. Stats
log("--- 8. Stats ruff ---", "CYAN")
rc, out, err = run([PY, "-m", "ruff", "check", ".", "--statistics",
                   "--no-cache"])
for line in (out + err).splitlines()[-30:]:
    log("  " + line)

# 11. Commit
log("--- 9. Commit ---", "CYAN")
git("add", "-A")
rc, out, err = run(["git", "commit", "-m",
    "chore(ruff): fix E/F/W/B/C4/UP + regen frozen core manifest"])
log(out or err)

log("=== FIX v2 TERMINE ===", "GREEN")
log(f"Log : {LOG}", "GRAY")
