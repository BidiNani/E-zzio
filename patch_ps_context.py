from pathlib import Path

p=Path("runtime/tools/executors/powershell.py")

code=p.read_text(encoding="utf-8")

code=code.replace(
'''cmd = kwargs.get("command") or (args[0] if args else None)''',
'''cmd = (
    kwargs.get("command")
    or getattr(context, "arguments", {}).get("command")
    or (args[0] if args else None)
)'''
)

code=code.replace(
'''timeout_sec = float(kwargs.get("timeout_sec") or getattr(context, "timeout_sec", 10.0))''',
'''timeout_sec = float(
    kwargs.get("timeout_sec")
    or getattr(context, "arguments", {}).get("timeout_sec")
    or getattr(context, "timeout_sec", 10.0)
)'''
)

p.write_text(code,encoding="utf-8")

print("[OK] Extraction contexte PowerShell corrigée")
