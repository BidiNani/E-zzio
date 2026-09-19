"""fix_b904.py - Ajoute `from err` ou `from None` aux raise dans except."""
import ast
import datetime
import pathlib
import subprocess
import sys

ROOT = pathlib.Path(r"G:\AI\E-zzio")
PY   = str(ROOT / ".venv" / "Scripts" / "python.exe")
LOG  = ROOT / "state" / "ruff_logs" / f"b904_{datetime.datetime.now():%Y%m%d_%H%M%S}.log"
LOG.parent.mkdir(parents=True, exist_ok=True)

def log(msg):
    line = f"[{datetime.datetime.now():%H:%M:%S}] {msg}"
    print(line, flush=True)
    with LOG.open("a", encoding="utf-8") as f:
        f.write(line + "\n")

def git(*args):
    r = subprocess.run(["git"] + list(args), cwd=str(ROOT),
                       capture_output=True, text=True)
    return r.stdout.strip()

log("=== FIX B904 START ===")
rc, safe_ref = 0, git("rev-parse", "HEAD")
log(f"Rollback: {safe_ref}")

# 1. Fix fichier par fichier
fixed_total = 0
violations = []

# Récupérer la liste exacte via ruff JSON
r = subprocess.run([PY, "-m", "ruff", "check", ".", "--select", "B904",
                    "--output-format=json", "--no-cache"],
                   cwd=str(ROOT), capture_output=True, text=True)
try:
    import json
    violations = json.loads(r.stdout or "[]")
except Exception as e:
    log(f"Erreur parse JSON: {e}")
    violations = []

log(f"Violations a corriger: {len(violations)}")

# Grouper par fichier
by_file = {}
for v in violations:
    fname = ROOT / v["filename"]
    by_file.setdefault(fname, []).append(v)

for filepath, vios in by_file.items():
    src = filepath.read_text(encoding="utf-8")
    tree = ast.parse(src)
    lines = src.splitlines(keepends=True)

    # Trouver tous les except avec leur variable (as X ou pas)
    # et leur portée
    except_blocks = []  # (start_line, end_line, var_name)
    for node in ast.walk(tree):
        if isinstance(node, ast.ExceptHandler):
            var = node.name  # None ou "e"
            start = node.lineno
            # Fin du bloc except = fin du dernier statement du body
            if node.body:
                end = node.body[-1].end_lineno
            else:
                end = start
            except_blocks.append((start, end, var))

    # Pour chaque B904, déterminer quel except le contient
    fixes = []  # (line_num, raise_keyword, from_var)
    for v in vios:
        line_no = v["location"]["row"]
        # Trouver le except qui contient cette ligne
        containing = None
        for (s, e, var) in except_blocks:
            if s <= line_no <= e:
                containing = (s, e, var)
                break
        if not containing:
            continue
        var = containing[2]
        fixes.append((line_no, var))

    if not fixes:
        continue

    # Appliquer en ordre descendant pour ne pas décaler les lignes
    fixes.sort(key=lambda x: x[0], reverse=True)
    for line_no, var in fixes:
        idx = line_no - 1
        line = lines[idx]
        # Trouver où la ligne `raise X` se termine (peut être multi-ligne)
        # On cherche la fin du raise : on remonte jusqu'au raise et on descend
        # jusqu'à la ligne qui a la même indentation que `raise` OU qui finit par `)`
        stripped = line.lstrip()
        if not stripped.startswith("raise "):
            continue
        indent = len(line) - len(stripped)
        # Trouver la fin du raise (jusqu'à ce qu'on retombe à l'indentation
        # du raise ou en dessous, ou qu'on trouve une ligne qui n'est pas
        # dans une parenthèse ouvrante non fermée)
        # Heuristique simple : tant que la ligne suivante a plus d'indent
        # ou que le compte de parenthèses n'est pas équilibré
        end_idx = idx
        depth = line.count("(") - line.count(")")
        while depth > 0 and end_idx + 1 < len(lines):
            end_idx += 1
            depth += lines[end_idx].count("(") - lines[end_idx].count(")")

        # Ajouter `from var` ou `from None` à la fin
        from_clause = f" from {var}" if var else " from None"
        last_line = lines[end_idx].rstrip("\n")
        if from_clause.strip() in last_line:
            continue
        # Ne pas ajouter si déjà `from X`
        if " from " in last_line and last_line.rstrip().endswith(tuple("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_")):
            continue
        lines[end_idx] = last_line + from_clause + "\n"

    new_src = "".join(lines)
    # Vérif AST
    try:
        ast.parse(new_src)
    except SyntaxError as e:
        log(f"  [FAIL] {filepath.name}: AST casse ligne {e.lineno}: {e.msg}")
        continue
    filepath.write_text(new_src, encoding="utf-8", newline="\n")
    log(f"  [OK] {filepath.name} : {len(fixes)} fix")
    fixed_total += len(fixes)

log(f"Total fixes: {fixed_total}")

# 2. Vérif AST global
log("--- AST global ---")
bad = 0
for p in ROOT.rglob("*.py"):
    if any(x in p.parts for x in (".venv",".git","__pycache__",
                                   "_archive","_archive_migration","state")):
        continue
    try:
        ast.parse(p.read_text(encoding="utf-8"))
    except SyntaxError as e:
        log(f"  AST FAIL {p}:{e.lineno}: {e.msg}")
        bad += 1

if bad:
    log("AST CASSE - rollback")
    subprocess.run(["git", "reset", "--hard", safe_ref], cwd=str(ROOT))
    sys.exit(1)
log("AST OK")

# 3. Ruff stats
log("--- Ruff stats ---")
r = subprocess.run([PY, "-m", "ruff", "check", ".", "--statistics", "--no-cache"],
                   cwd=str(ROOT), capture_output=True, text=True)
for line in (r.stdout + r.stderr).splitlines()[-10:]:
    log("  " + line)

# 4. Pytest
log("--- pytest ---")
r = subprocess.run([PY, "-m", "pytest", "tests/", "-q", "--tb=line",
                    "--no-header"], cwd=str(ROOT), capture_output=True, text=True)
for line in (r.stdout + r.stderr).splitlines()[-5:]:
    log("  " + line)
if r.returncode != 0:
    log("TESTS CASSES - rollback")
    subprocess.run(["git", "reset", "--hard", safe_ref], cwd=str(ROOT))
    sys.exit(1)
log("Tests OK")

log("=== FIX B904 TERMINE ===")
