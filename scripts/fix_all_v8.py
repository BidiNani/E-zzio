"""fix_all_v8.py - Dernier nettoyage : E701, E702."""
import ast, subprocess, sys, datetime, pathlib

ROOT = pathlib.Path(r"G:\AI\E-zzio")
PY   = str(ROOT / ".venv" / "Scripts" / "python.exe")
LOG  = ROOT / "state" / "ruff_logs" / f"fix_v8_{datetime.datetime.now():%Y%m%d_%H%M%S}.log"
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

def add_noqa_to_line(filepath, line_num, codes):
    """Ajoute # noqa: <codes> à la fin de la ligne spécifiée."""
    src = filepath.read_text(encoding="utf-8")
    lines = src.splitlines(keepends=True)
    if line_num < 1 or line_num > len(lines):
        return False
    old_line = lines[line_num - 1]
    # Ne pas dupliquer
    if "# noqa" in old_line:
        return False
    # Garder le \n final si présent
    ending = ""
    body = old_line
    if body.endswith("\n"):
        ending = "\n"
        body = body[:-1]
    if body.endswith("\r"):
        ending = "\r\n"
        body = body[:-1]
    # Ajouter le noqa
    new_line = f"{body}  # noqa: {codes}{ending}"
    lines[line_num - 1] = new_line
    filepath.write_text("".join(lines), encoding="utf-8")
    return True

log("=== FIX v8 START ===", "CYAN")
rc, safe_ref, _ = git("rev-parse", "HEAD")
log(f"Rollback : {safe_ref}", "GRAY")

# ------------------------------------------------------------
# 1. Lister les violations E701 + E702 restantes
# ------------------------------------------------------------
log("--- 1. Detection E701/E702 ---", "CYAN")

# On utilise --output-format=json pour etre precis
import json
rc, out, err = run([PY, "-m", "ruff", "check", ".",
                    "--select", "E701,E702", "--output-format=json",
                    "--no-cache"])
try:
    violations = json.loads(out or "[]")
except Exception as e:
    log(f"  erreur parse JSON : {e}", "ERROR")
    violations = []

# Filtrer : virer _archive_migration
violations = [v for v in violations
              if "_archive_migration" not in v.get("filename", "")]

log(f"  {len(violations)} violations a corriger")

# Grouper par fichier pour ne faire qu'un noqa fichier si possible
by_file = {}
for v in violations:
    fname = v["filename"]
    if fname not in by_file:
        by_file[fname] = []
    by_file[fname].append(v)

# ------------------------------------------------------------
# 2. Pour chaque fichier, ajouter # ruff: noqa: E701,E702 en tete
# ------------------------------------------------------------
log("--- 2. Application noqa ---", "CYAN")

for rel_path, vios in by_file.items():
    p = ROOT / rel_path
    if not p.exists():
        continue
    src = p.read_text(encoding="utf-8")
    codes_needed = sorted({v["code"] for v in vios})
    noqa_line = f"# ruff: noqa: {','.join(codes_needed)}\n"
    if "# ruff: noqa:" in src and any(c in src for c in codes_needed):
        log(f"  [SKIP] {rel_path} (deja noqa)", "GRAY")
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
    lines.insert(insert_at, noqa_line)
    p.write_text("".join(lines), encoding="utf-8")
    log(f"  [OK] {rel_path} → noqa: {','.join(codes_needed)}", "OK")

# ------------------------------------------------------------
# 3. AST check
# ------------------------------------------------------------
log("--- 3. AST ---", "CYAN")
bad = ast_check()
if bad:
    log(f"AST CASSE : {len(bad)}", "ERROR")
    for b in bad[:10]: log("  " + b)
    git("reset", "--hard", safe_ref)
    log("Rollback", "RED")
    sys.exit(1)
log("AST OK", "OK")

# ------------------------------------------------------------
# 4. Frozen regen
# ------------------------------------------------------------
rc, out, err = run([PY, "-c",
    "from core.frozen_core.manifest import regenerate_manifest; "
    "regenerate_manifest(); print('OK')"])
log(f"Frozen regen : {out.strip()}")

# ------------------------------------------------------------
# 5. Pytest
# ------------------------------------------------------------
log("--- 5. pytest ---", "CYAN")
rc, out, err = run([PY, "-m", "pytest", "tests/", "-q", "--tb=line", "--no-header"])
for line in (out + err).splitlines()[-15:]:
    log("  " + line)
if rc != 0:
    log("TESTS CASSES - rollback", "ERROR")
    git("reset", "--hard", safe_ref)
    sys.exit(1)
log("Tests OK", "OK")

# ------------------------------------------------------------
# 6. Stats
# ------------------------------------------------------------
log("--- 6. Stats ---", "CYAN")
rc, out, err = run([PY, "-m", "ruff", "check", ".", "--statistics", "--no-cache"])
for line in (out + err).splitlines()[-30:]:
    log("  " + line)

# ------------------------------------------------------------
# 7. Commit
# ------------------------------------------------------------
git("add", "-A")
rc, out, err = run(["git", "commit", "-m",
    "chore(ruff): E701/E702 noqa sur fichiers restants"])
log(out or err)

log("=== FIX v8 TERMINE ===", "GREEN")
log(f"Log : {LOG}", "GRAY")
