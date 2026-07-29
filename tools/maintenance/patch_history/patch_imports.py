from pathlib import Path

files = [
    "runtime/tools/executors/powershell.py",
    "runtime/tools/executors/filesystem.py"
]

for file in files:
    p = Path(file)
    code = p.read_text(encoding="utf-8")

    if "from runtime.external.base import ExternalExecutorBase" not in code:

        lines = code.splitlines()

        # insertion après les imports existants
        index = 0
        for i,l in enumerate(lines):
            if l.startswith("import ") or l.startswith("from "):
                index=i+1

        lines.insert(index,
            "from runtime.external.base import ExternalExecutorBase"
        )

        code="\n".join(lines)+"\n"

        p.write_text(code,encoding="utf-8")

        print("[+] Import ajouté :",file)

    else:
        print("[OK] Import déjà présent :",file)

print("Terminé")
