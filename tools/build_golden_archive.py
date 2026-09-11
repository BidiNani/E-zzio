import os
import zipfile
import hashlib
import json
from pathlib import Path

ROOT = Path("G:/AI/E-zzio")
RELEASES_DIR = ROOT / "dist/releases"
RELEASES_DIR.mkdir(parents=True, exist_ok=True)

ARCHIVE_PATH = RELEASES_DIR / "E-ZzIO-V9.1-GOLDEN-SOURCE.zip"
MANIFEST_PATH = RELEASES_DIR / "E-ZzIO-V9.1-GOLDEN-MANIFEST.json"

EXCLUDE_DIRS = {
    ".git", ".venv", "__pycache__", ".pytest_cache", ".system_generated",
    "node_modules", "build", ".gradle", "captures", "compression_cache"
}

EXCLUDE_FILES = {
    "release.keystore", ".env", "local.properties"
}

EXCLUDE_EXTENSIONS = {
    ".pyc", ".pyo", ".pyd", ".log", ".tmp", ".keystore", ".jks"
}

INCLUDED_ROOTS = ["core", "runtime", "android", "tools", "assets", "docs", "tests", "dist/android"]
ROOT_FILES = ["web_server.py", "pytest.ini", "requirements.txt", "README.md", "LICENSE"]

def sha256_file(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        while chunk := f.read(65536):
            h.update(chunk)
    return h.hexdigest().upper()

entries_info = []

print(f"Creating Golden Source Archive: {ARCHIVE_PATH} ...")
with zipfile.ZipFile(ARCHIVE_PATH, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=6) as z:
    # 1. Root files
    for rf in ROOT_FILES:
        p = ROOT / rf
        if p.exists():
            arcname = rf
            z.write(p, arcname)
            entries_info.append({
                "path": arcname,
                "size_bytes": p.stat().st_size,
                "sha256": sha256_file(p)
            })
    
    # 2. Subdirectories
    for d in INCLUDED_ROOTS:
        base = ROOT / d
        if not base.exists():
            continue
        for dirpath, dirnames, filenames in os.walk(base):
            dirnames[:] = [sub for sub in dirnames if sub not in EXCLUDE_DIRS and not sub.startswith(".")]
            for fn in filenames:
                if fn in EXCLUDE_FILES:
                    continue
                ext = os.path.splitext(fn)[1].lower()
                if ext in EXCLUDE_EXTENSIONS:
                    continue
                fp = Path(dirpath) / fn
                arcname = fp.relative_to(ROOT).as_posix()
                z.write(fp, arcname)
                entries_info.append({
                    "path": arcname,
                    "size_bytes": fp.stat().st_size,
                    "sha256": sha256_file(fp)
                })

archive_size = ARCHIVE_PATH.stat().st_size
archive_sha256 = sha256_file(ARCHIVE_PATH)

golden_manifest = {
    "product": "E-ZzIO",
    "version": "9.0.1",
    "release": "V9.1",
    "release_type": "GOLDEN_RELEASE",
    "status": "IMMUTABLE_BASELINE",
    "archive_name": "E-ZzIO-V9.1-GOLDEN-SOURCE.zip",
    "archive_size_bytes": archive_size,
    "archive_sha256": archive_sha256,
    "source_revision": "dde4d186ce8cee1bdcfa42f6850763adb08b25f8",
    "source_revision_short": "dde4d18",
    "branch": "checkpoint/voice-capabilities-hardware-agent-20260816",
    "total_entries": len(entries_info),
    "frozen_core_hashes": {
        "core/capabilities/capability_policy.py": sha256_file(ROOT / "core/capabilities/capability_policy.py"),
        "core/capabilities/registry.py": sha256_file(ROOT / "core/capabilities/registry.py"),
        "core/security/audit_ledger.py": sha256_file(ROOT / "core/security/audit_ledger.py")
    },
    "canonical_release_apk": {
        "path": "dist/android/E-ZzIO-v9.1-release.apk",
        "size_bytes": (ROOT / "dist/android/E-ZzIO-v9.1-release.apk").stat().st_size,
        "sha256": sha256_file(ROOT / "dist/android/E-ZzIO-v9.1-release.apk")
    }
}

with open(MANIFEST_PATH, "w", encoding="utf-8") as f:
    json.dump(golden_manifest, f, indent=2)

print(f"SUCCESS: Archive created: {archive_size} bytes, SHA256: {archive_sha256}")
print(f"SUCCESS: Manifest created: {MANIFEST_PATH}")
