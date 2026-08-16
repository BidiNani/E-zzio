import ast
from pathlib import Path

path = Path(r"G:\AI\E-zzio\runtime\memory__init__.py")

try:
    ast.parse(
        path.read_text(encoding="utf-8-sig"),
        filename=str(path)
    )
    print("PASS|runtime\memory__init__.py")
except Exception as e:
    print("FAIL|runtime\memory__init__.py|" + repr(e))
    raise
