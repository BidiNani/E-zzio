from pathlib import Path

files_to_fix = [
    "runtime/agent/controller.py",
    "runtime/core/microkernel.py",
    "runtime/tools/pipeline.py"
]

for f_path in files_to_fix:
    p = Path(f_path)
    if p.exists():
        content = p.read_text(encoding="utf-8")
        content = content.replace('.get("error")', ".get('error')")
        content = content.replace('.get("success", False)', ".get('success', False)")
        content = content.replace('.get("output", "")', ".get('output', '')")
        content = content.replace('getattr(tool_result, "error", None)', "getattr(tool_result, 'error', None)")
        content = content.replace('getattr(result, "success", False)', "getattr(result, 'success', False)")
        content = content.replace('getattr(result, "output", "")', "getattr(result, 'output', '')")
        p.write_text(content, encoding="utf-8")
        print(f"[+] f-strings nettoyés dans {f_path}")
