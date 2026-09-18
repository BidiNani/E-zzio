import os
import re
import sys
import zipfile
from pathlib import Path

ROOT = Path("G:/AI/E-zzio")
patterns = [
    re.compile(r'AIza[0-9A-Za-z-_]{35}'),
    re.compile(r'gsk_[0-9A-Za-z]{40,}'),
    re.compile(r'Bearer\s+[A-Za-z0-9\-\._~\+\/]{25,}='),
    re.compile(r'-----BEGIN (?:RSA )?PRIVATE KEY-----'),
    re.compile(r'AKIA[0-9A-Z]{16}')
]

EXCLUDES = {".git", ".venv", ".system_generated", "cache", "build", ".gradle"}
violations = []

def scan_text(text, source_name):
    for pat in patterns:
        m = pat.search(text)
        if m:
            violations.append((source_name, m.group(0)[:15] + "..."))

for target in ["core", "runtime", "android", "tools", "assets", "docs", "tests", "dist"]:
    base = ROOT / target
    for dirpath, dirnames, filenames in os.walk(base):
        dirnames[:] = [d for d in dirnames if d not in EXCLUDES and not d.startswith(".")]
        for fn in filenames:
            p = Path(dirpath) / fn
            if p.suffix.lower() in [".py", ".json", ".js", ".html", ".xml", ".gradle", ".ps1", ".md"]:
                try:
                    c = p.read_text(encoding="utf-8", errors="ignore")
                    scan_text(c, str(p.relative_to(ROOT)))
                except Exception:
                    pass
            elif p.suffix.lower() in [".apk", ".zip"]:
                try:
                    with zipfile.ZipFile(p, "r") as z:
                        for info in z.infolist():
                            if not info.is_dir() and not info.filename.endswith(".dex") and not info.filename.endswith(".arsc"):
                                try:
                                    data = z.read(info.filename).decode("latin1", errors="ignore")
                                    scan_text(data, f"{p.relative_to(ROOT)}!{info.filename}")
                                except Exception:
                                    pass
                except Exception:
                    pass

if violations:
    print(f"SECURITY VIOLATION DETECTED: {len(violations)} occurrences")
    for v in violations:
        print("  -", v)
    sys.exit(1)
else:
    print("SECURITY BASELINE AUDIT: 0 SECRETS DETECTED (CLEAN)")
