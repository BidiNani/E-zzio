from pathlib import Path

for path_str in ["runtime/tools/executors/powershell.py", "runtime/tools/executors/filesystem.py"]:
    p = Path(path_str)
    if p.exists():
        code = p.read_text(encoding="utf-8")
        
        # S'assurer que l'import est tout en haut après les éventuels docstrings/future imports
        if "ExternalExecutorBase" in code and "from runtime.external.base import ExternalExecutorBase" not in code:
            lines = code.splitlines()
            insert_idx = 0
            for i, line in enumerate(lines):
                if line.startswith("import ") or line.startswith("from "):
                    insert_idx = i
                    break
            lines.insert(insert_idx, "from runtime.external.base import ExternalExecutorBase")
            code = "\n".join(lines)
            p.write_text(code, encoding="utf-8")
            print(f"[+] Import de ExternalExecutorBase injecté dans {path_str}")

print("[OK] Imports corrigés.")
