import ast
from pathlib import Path

path = Path(r"G:\AI\E-zzio\runtime\memory\session.py")

try:
    ast.parse(
        path.read_text(encoding="utf-8-sig"),
        filename=str(path)
    )
    print("PASS|runtime\memory\session.py")
except Exception as e:
    print("FAIL|runtime\memory\session.py|" + repr(e))
    raise
