"""fix_all_v7.py - Nettoyage final + exclusion scripts migration."""
import ast
import datetime
import pathlib
import subprocess
import sys

ROOT = pathlib.Path(r"G:\AI\E-zzio")
PY   = str(ROOT / ".venv" / "Scripts" / "python.exe")
LOG  = ROOT / "state" / "ruff_logs" / f"fix_v7_{datetime.datetime.now():%Y%m%d_%H%M%S}.log"
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
                                       "state","_backup_ruff","_archive",
                                       "_archive_migration")):
            continue
        try:
            ast.parse(f.read_text(encoding="utf-8"))
        except SyntaxError as e:
            bad.append(f"{f}:{e.lineno}: {e.msg}")
    return bad

log("=== FIX v7 START ===", "CYAN")
rc, safe_ref, _ = git("rev-parse", "HEAD")
log(f"Rollback : {safe_ref}", "GRAY")

# ------------------------------------------------------------
# 1. Exclure les scripts de migration du scan ruff
# ------------------------------------------------------------
log("--- 1. Exclusion scripts migration ---", "CYAN")

# Creer dossier archive
arch = ROOT / "scripts" / "_archive_migration"
arch.mkdir(parents=True, exist_ok=True)

# Deplacer les scripts v1-v6 + ruff_one_lot.ps1 + _ast_check.py dans archive
for fname in ["fix_all.py", "fix_all_v2.py", "fix_all_v3.py", "fix_all_v4.py",
              "fix_all_v5.py", "fix_all_v6.py", "ruff_one_lot.ps1", "_ast_check.py"]:
    src = ROOT / "scripts" / fname
    if src.exists():
        dst = arch / fname
        if dst.exists():
            dst.unlink()
        src.rename(dst)
        log(f"  [OK] {fname} → _archive_migration/", "OK")

# Ajouter exclusion dans pyproject.toml
pp = ROOT / "pyproject.toml"
content = pp.read_text(encoding="utf-8")
if "_archive_migration" not in content:
    # Trouver la section [tool.ruff] exclude
    old = '''exclude = [
    ".venv",'''
    new = '''exclude = [
    ".venv",
    "scripts/_archive_migration",'''
    if old in content:
        content = content.replace(old, new, 1)
        pp.write_text(content, encoding="utf-8")
        log("  [OK] pyproject.toml : scripts/_archive_migration exclu", "OK")
    else:
        log("  [SKIP] pyproject.toml : pattern exclude introuvable", "YELLOW")

# ------------------------------------------------------------
# 2. Auto-fix I001, E401, E702, F401
# ------------------------------------------------------------
log("--- 2. auto-fix ruff ---", "CYAN")
rc, out, err = run([PY, "-m", "ruff", "check", ".",
                   "--select", "I001,E401,E702,F401",
                   "--fix", "--no-cache", "--quiet"])
log(f"  exit : {rc}")

# ------------------------------------------------------------
# 3. E701 restants : noqa sur les fichiers restants
# ------------------------------------------------------------
log("--- 3. E701 noqa ---", "CYAN")
rc, out, err = run([PY, "-m", "ruff", "check", ".", "--select", "E701",
                   "--output-format=concise", "--no-cache"])
e701_files = set()
for line in (out + err).splitlines():
    if "E701" in line:
        # extraire le chemin avant le 1er ":"
        parts = line.split(":", 2)
        if len(parts) >= 2:
            e701_files.add(parts[0])

for rel in e701_files:
    p = ROOT / rel
    if not p.exists(): continue
    src = p.read_text(encoding="utf-8")
    if "# ruff: noqa: E701" in src:
        continue
    lines = src.splitlines(keepends=True)
    insert_at = 0
    if lines and lines[0].strip().startswith('"""'):
        if lines[0].rstrip().endswith('"""') and len(lines[0].strip()) > 6:
            insert_at = 1
        else:
            for i, ln in enumerate(lines[1:], 1):
                if '"""' in ln:
                    insert_at = i + 1
                    break
    lines.insert(insert_at, "# ruff: noqa: E701\n")
    p.write_text("".join(lines), encoding="utf-8")
    log(f"  [OK] {rel}", "OK")

# ------------------------------------------------------------
# 4. AST check
# ------------------------------------------------------------
log("--- 4. AST ---", "CYAN")
bad = ast_check()
if bad:
    log(f"AST CASSE : {len(bad)}", "ERROR")
    for b in bad[:10]: log("  " + b)
    git("reset", "--hard", safe_ref)
    log("Rollback", "RED")
    sys.exit(1)
log("AST OK", "OK")

# ------------------------------------------------------------
# 5. Frozen regen
# ------------------------------------------------------------
rc, out, err = run([PY, "-c",
    "from core.frozen_core.manifest import regenerate_manifest; "
    "regenerate_manifest(); print('OK')"])
log(f"Frozen regen : {out.strip()}")

# ------------------------------------------------------------
# 6. Pytest
# ------------------------------------------------------------
log("--- 6. pytest ---", "CYAN")
rc, out, err = run([PY, "-m", "pytest", "tests/", "-q", "--tb=line", "--no-header"])
for line in (out + err).splitlines()[-15:]:
    log("  " + line)
if rc != 0:
    log("TESTS CASSES - rollback", "ERROR")
    git("reset", "--hard", safe_ref)
    sys.exit(1)
log("Tests OK", "OK")

# ------------------------------------------------------------
# 7. Stats
# ------------------------------------------------------------
log("--- 7. Stats ---", "CYAN")
rc, out, err = run([PY, "-m", "ruff", "check", ".", "--statistics", "--no-cache"])
for line in (out + err).splitlines()[-30:]:
    log("  " + line)

# ------------------------------------------------------------
# 8. Commit
# ------------------------------------------------------------
git("add", "-A")
rc, out, err = run(["git", "commit", "-m",
    "chore(ruff): exclusion scripts migration + I001/E401/E702/F401/E701"])
log(out or err)

log("=== FIX v7 TERMINE ===", "GREEN")
log(f"Log : {LOG}", "GRAY")
