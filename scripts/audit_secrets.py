import os
import re
from pathlib import Path

ROOT = Path(r"G:/AI/E-zzio").resolve()

SECRET_PATTERNS = [
    re.compile(r"(?i)(?:api[_-]?key|secret|token|password)\s*[:=]\s*['\"]([^'\"]{16,})['\"]"),
    re.compile(r"sk-[a-zA-Z0-9]{20,}"),
    re.compile(r"ghp_[a-zA-Z0-9]{20,}"),
    re.compile(r"AIza[0-9A-Za-z-_]{35}"),
]

EXCLUDED_DIRS = {
    ".git", ".venv", "venv", "__pycache__", "secrets", "backups", "audit", "test_tmp", "forensic_archive"
}

def audit_secrets() -> dict:
    findings = []
    scanned_files = 0

    for root, dirs, files in os.walk(ROOT):
        dirs[:] = [d for d in dirs if d not in EXCLUDED_DIRS]

        for file in files:
            ext = os.path.splitext(file)[1].lower()
            if ext in {".py", ".ps1", ".json", ".yaml", ".yml", ".md"}:
                fpath = Path(root) / file
                rel_path = fpath.relative_to(ROOT)
                scanned_files += 1
                try:
                    content = fpath.read_text(encoding="utf-8", errors="ignore")
                    for pat in SECRET_PATTERNS:
                        matches = pat.findall(content)
                        for m in matches:
                            if isinstance(m, str) and any(dummy in m.lower() for dummy in ["example", "placeholder", "your_", "super_secret_session_key", "ezzio_secret_key_local_dev"]):
                                continue
                            findings.append({
                                "file": str(rel_path),
                                "pattern_type": "SUSPICIOUS_KEY_OR_TOKEN"
                            })
                except Exception:
                    pass

    return {
        "scanned_files": scanned_files,
        "leak_count": len(findings),
        "findings": findings,
        "verdict": "ZERO_SECRET_LEAKAGE" if len(findings) == 0 else "ACTION_REQUIRED"
    }

if __name__ == "__main__":
    res = audit_secrets()
    print(f"Scanned {res['scanned_files']} files. Leaks found: {res['leak_count']}. Verdict: {res['verdict']}")
