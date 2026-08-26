from pathlib import Path
import ast
import sys

ROOT = Path(r"G:\AI\E-zzio")

FILES = [
    ROOT / "routers/master.py",
    ROOT / "core/dispatcher.py",
    ROOT / "core/ezzio_master.py",
    ROOT / "core/cloud_brain_broker.py",
    ROOT / "runtime/model_router/context.py",
]

errors = 0

for p in FILES:
    if not p.exists():
        continue

    text = p.read_text(encoding="utf-8", errors="replace")

    try:
        ast.parse(text)
    except SyntaxError as exc:
        print(f"[FAIL] Syntaxe: {p.relative_to(ROOT)}:{exc.lineno}")
        errors += 1

    if p.name in {"dispatcher.py", "ezzio_master.py"}:
        for i, line in enumerate(text.splitlines(), 1):
            if "system_prompt" in line:
                print(f"[FAIL] system_prompt: {p.relative_to(ROOT)}:{i}")
                errors += 1

        for i, line in enumerate(text.splitlines(), 1):
            if 'provider="gemini"' in line or "provider='gemini'" in line:
                print(f"[FAIL] provider Gemini imposé: {p.relative_to(ROOT)}:{i}")
                errors += 1

print("-" * 78)

if errors:
    print(f"[VERDICT] 🔴 {errors} anomalie(s)")
    sys.exit(1)

print("[VERDICT] 🟢 MASTER/DELEGATOR CLEAN")
