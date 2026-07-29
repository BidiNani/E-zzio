from pathlib import Path

files = [
    "runtime/tools/executors/powershell.py",
    "runtime/tools/executors/filesystem.py"
]

for file in files:

    p = Path(file)

    code = p.read_text(encoding="utf-8")

    old = "def execute(context, *args, **kwargs):"
    new = "def execute(self, context, *args, **kwargs):"

    if old in code:
        code = code.replace(old,new)
        print("[+] Signature corrigée :",file)
    else:
        print("[OK] Signature déjà correcte :",file)

    p.write_text(code,encoding="utf-8")


print("Patch signatures terminé")
