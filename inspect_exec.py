from pathlib import Path

for f in [
"runtime/tools/executors/powershell.py",
"runtime/tools/executors/filesystem.py"
]:

    print("\n======",f)

    p=Path(f)

    txt=p.read_text(encoding="utf-8")

    for line in txt.splitlines():
        if (
            "class " in line
            or "def execute" in line
            or "timeout" in line
            or "subprocess" in line
            or "blocked" in line
            or "policy" in line
        ):
            print(line)
