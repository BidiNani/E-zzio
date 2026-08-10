import ast
from pathlib import Path

path = Path(r"G:\AI\E-zzio\runtime\memory\events.py")

try:
    ast.parse(
        path.read_text(encoding="utf-8-sig"),
        filename=str(path)
    )
    print("PASS|runtime\memory\events.py")
except Exception as e:
    print("FAIL|runtime\memory\events.py|" + repr(e))
    raise
