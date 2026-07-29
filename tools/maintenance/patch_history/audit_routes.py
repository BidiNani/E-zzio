from pathlib import Path

targets=[
    "system.powershell",
    "powershell.safe.execute",
    "filesystem.read",
    "ExecutorRegistry",
    "PowerShellExecutor",
    "FileSystemExecutor"
]

for p in Path("runtime").rglob("*.py"):
    try:
        txt=p.read_text(encoding="utf-8")
    except:
        continue

    hits=[x for x in targets if x in txt]

    if hits:
        print("\n==============================")
        print(p)
        for i,line in enumerate(txt.splitlines(),1):
            if any(x in line for x in hits):
                print(f"{i}: {line.strip()}")
