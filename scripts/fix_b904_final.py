
'''fix_b904_final.py - Ajoute from X aux raise B904.'''
import ast, json, re, subprocess, sys, pathlib

ROOT = pathlib.Path(r'G:\AI\E-zzio')
PY   = str(ROOT / '.venv' / 'Scripts' / 'python.exe')

def ruff_json():
    r = subprocess.run(
        [PY, '-m', 'ruff', 'check', '.', '--select', 'B904',
         '--output-format=json', '--no-cache'],
        cwd=str(ROOT), capture_output=True, text=True, encoding='utf-8'
    )
    return json.loads(r.stdout or '[]')

def find_except(tree, line_no):
    for node in ast.walk(tree):
        if isinstance(node, ast.ExceptHandler):
            if node.lineno <= line_no <= (node.end_lineno or node.lineno):
                return node.name
    return 'NOT_FOUND'

def add_from(filepath, vios):
    src = filepath.read_text(encoding='utf-8')
    tree = ast.parse(src)
    lines = src.splitlines(keepends=True)
    vios.sort(key=lambda v: v['location']['row'], reverse=True)
    n = 0
    for v in vios:
        line_no = v['location']['row']
        var = find_except(tree, line_no)
        if var == 'NOT_FOUND':
            print(f'    SKIP L{line_no}: pas de except')
            continue
        from_clause = f' from {var}' if var else ' from None'
        idx = line_no - 1
        while idx < len(lines) and 'raise ' not in lines[idx]:
            idx += 1
        if idx >= len(lines):
            continue
        depth = 0
        end = idx
        in_str = None
        while end < len(lines):
            line = lines[end]
            i = 0
            while i < len(line):
                ch = line[i]
                if in_str:
                    if ch == chr(92):
                        i += 2
                        continue
                    if ch == in_str:
                        in_str = None
                    i += 1
                    continue
                if ch in (chr(34), chr(39)):
                    if line[i:i+3] in (chr(34)*3, chr(39)*3):
                        in_str = ch
                        i += 3
                        continue
                    in_str = ch
                    i += 1
                    continue
                if ch == '(':
                    depth += 1
                elif ch == ')':
                    depth -= 1
                elif ch == '#':
                    break
                i += 1
            if depth <= 0 and in_str is None and not line.rstrip().endswith(chr(92)):
                break
            end += 1
        last = lines[end].rstrip(chr(10)).rstrip(chr(13))
        if re.search(r'from\s+\w+\s*$', last) or ' from None' in last:
            continue
        lines[end] = last + from_clause + chr(10)
        n += 1
        print(f'    OK L{line_no}: ...{from_clause}')
    if n:
        new_src = ''.join(lines)
        try:
            ast.parse(new_src)
        except SyntaxError as e:
            print(f'    FAIL AST L{e.lineno}: {e.msg}')
            return 0
        filepath.write_text(new_src, encoding='utf-8', newline=chr(10))
    return n

def main():
    print('=== FIX B904 FINAL ===')
    vios = ruff_json()
    print(f'Violations: {len(vios)}')
    by_file = {}
    for v in vios:
        by_file.setdefault(ROOT / v['filename'], []).append(v)
    total = 0
    for fp, vs in by_file.items():
        print(f'  {fp.relative_to(ROOT)} ({len(vs)})')
        total += add_from(fp, vs)
    print(f'Total fixes: {total}')
    remaining = len(ruff_json())
    print(f'B904 restants: {remaining}')
    if remaining:
        print('ECHEC')
        sys.exit(1)
    print('SUCCESS - 0 B904')

if __name__ == '__main__':
    main()
