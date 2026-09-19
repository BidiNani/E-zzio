import ast
import pathlib
import sys

bad = 0
EXCLUDE = ('.venv','.git','__pycache__','.ruff_cache','node_modules','state',
           '_backup_ruff','_archive','archive','dist','build','.mypy_cache',
           '.pytest_cache','.tox','.eggs')
for p in pathlib.Path('.').rglob('*.py'):
    if any(x in p.parts for x in EXCLUDE):
        continue
    try:
        ast.parse(p.read_text(encoding='utf-8'))
    except SyntaxError as e:
        print(f"AST FAIL {p}:{e.lineno}: {e.msg}")
        bad += 1
sys.exit(1 if bad else 0)
