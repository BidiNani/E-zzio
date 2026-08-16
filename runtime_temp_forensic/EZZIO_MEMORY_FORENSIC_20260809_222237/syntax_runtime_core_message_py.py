import ast
from pathlib import Path

path = Path(r"G:\AI\E-zzio\runtime\core\message.py")

try:
    ast.parse(
        path.read_text(encoding="utf-8-sig"),
        filename=str(path)
    )
    print("PASS|runtime\core\message.py")
except Exception as e:
    print("FAIL|runtime\core\message.py|" + repr(e))
    raise
