"""fix_b904_v2.py - Corrige B904 via AST robuste."""
import ast
import json
import pathlib
import re
import subprocess
import sys

ROOT = pathlib.Path(r"G:\AI\E-zzio")
PY   = str(ROOT / ".venv" / "Scripts" / "python.exe")

def run_ruff_json():
    r = subprocess.run(
        [PY, "-m", "ruff", "check", ".", "--select", "B904",
         "--output-format=json", "--no-cache"],
        cwd=str(ROOT), capture_output=True, text=True, encoding="utf-8"
    )
    return json.loads(r.stdout or "[]")

def find_except_for_line(tree, line_no):
    """Trouve l'ExceptHandler qui contient la ligne donnée."""
    for node in ast.walk(tree):
        if isinstance(node, ast.ExceptHandler):
            # Le corps du except
            for stmt in node.body:
                # Utiliser end_lineno du statement (dispo py3.8+)
                if stmt.lineno <= line_no <= (stmt.end_lineno or stmt.lineno):
                    return node
    return None

def add_from_to_raise(filepath, violations):
    """Ajoute `from X` à chaque raise B904."""
    src = filepath.read_text(encoding="utf-8")
    tree = ast.parse(src)
    lines = src.splitlines(keepends=True)

    # Trier par ligne décroissante pour ne pas décaler
    violations.sort(key=lambda v: v["location"]["row"], reverse=True)

    modified = 0
    for v in violations:
        line_no = v["location"]["row"]
        except_node = find_except_for_line(tree, line_no)
        if except_node is None:
            print(f"    [SKIP] L{line_no}: pas de except trouvé")
            continue

        var = except_node.name  # None ou "e"/"exc"
        from_clause = f" from {var}" if var else " from None"

        # Trouver le raise dans le fichier à partir de line_no
        # C'est la ligne qui contient "raise " en premier
        idx = line_no - 1
        while idx < len(lines) and not lines[idx].lstrip().startswith("raise "):
            idx += 1
        if idx >= len(lines):
            continue

        # Trouver la fin du raise : parcourir jusqu'à équilibre parenthèses
        # en ignorant les strings
        depth = 0
        end_idx = idx
        in_string = False
        string_char = None
        while end_idx < len(lines):
            line = lines[end_idx]
            i = 0
            while i < len(line):
                ch = line[i]
                if in_string:
                    if ch == "\\":
                        i += 2
                        continue
                    if ch == string_char:
                        in_string = False
                    i += 1
                    continue
                if ch in ('"', "'"):
                    # Vérifier triple quotes
                    if line[i:i+3] in ('"""', "'''"):
                        in_string = True
                        string_char = line[i]
                        i += 3
                        continue
                    in_string = True
                    string_char = ch
                    i += 1
                    continue
                if ch == "(":
                    depth += 1
                elif ch == ")":
                    depth -= 1
                elif ch == "#":
                    break
                i += 1
            # Si on est à depth 0 et qu'on a fini la ligne, c'est bon
            if depth <= 0 and not in_string:
                # Vérifier que la ligne n'est pas une continuation avec \
                stripped = line.rstrip()
                if not stripped.endswith("\\"):
                    break
            end_idx += 1

        last_line = lines[end_idx].rstrip("\n").rstrip("\r")
        # Ne pas doubler si déjà `from X`
        if re.search(r"\bfrom\s+\w+\s*$", last_line) or " from None" in last_line:
            continue

        lines[end_idx] = last_line + from_clause + "\n"
        modified += 1
        print(f"    [OK] L{line_no} → {last_line.strip()[:60]}...{from_clause}")

    if modified:
        new_src = "".join(lines)
        # Vérif AST
        try:
            ast.parse(new_src)
        except SyntaxError as e:
            print(f"    [FAIL] AST cassé: L{e.lineno} {e.msg}")
            return 0
        filepath.write_text(new_src, encoding="utf-8", newline="\n")
    return modified

def main():
    print("=== FIX B904 v2 ===")
    violations = run_ruff_json()
    print(f"Violations: {len(violations)}")

    # Grouper par fichier
    by_file = {}
    for v in violations:
        by_file.setdefault(ROOT / v["filename"], []).append(v)

    total = 0
    for filepath, vios in by_file.items():
        print(f"\n  {filepath.relative_to(ROOT)}  ({len(vios)} B904)")
        total += add_from_to_raise(filepath, vios)

    print(f"\nTotal modifiés: {total}")

    # Vérif finale
    remaining = run_ruff_json()
    print(f"B904 restants: {len(remaining)}")

    # AST global
    bad = 0
    for p in ROOT.rglob("*.py"):
        if any(x in p.parts for x in (".venv", ".git", "__pycache__",
                                       "_archive", "_archive_migration", "state")):
            continue
        try:
            ast.parse(p.read_text(encoding="utf-8"))
        except SyntaxError as e:
            print(f"AST FAIL {p}:{e.lineno}: {e.msg}")
            bad += 1
    if bad:
        print(f"AST CASSE: {bad}")
        sys.exit(1)
    print("AST OK")

if __name__ == "__main__":
    main()
