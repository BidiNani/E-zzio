from pathlib import Path

p = Path("runtime/action/registry.py")

code = p.read_text(encoding="utf-8")

old = "if active_permissions and ctx:"

new = "if active_permissions is not None and ctx:"

if old not in code:
    raise Exception("Bloc permissions introuvable")

code = code.replace(old,new)

p.write_text(code,encoding="utf-8")

print("[OK] Correction active_permissions vide appliquée")
