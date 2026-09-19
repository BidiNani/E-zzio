import hashlib
import json
import os
from pathlib import Path

ROOT = Path("G:/AI/E-zzio")
OUTPUT_FILE = ROOT / "state/audit/golden/v9.1/golden_file_manifest.json"

def sha256_file(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        while chunk := f.read(65536):
            h.update(chunk)
    return h.hexdigest().upper()

EXCLUDE_DIRS = {
    ".git", ".venv", "__pycache__", ".pytest_cache", ".system_generated",
    "node_modules", "build", ".gradle", "captures"
}
EXCLUDE_EXTENSIONS = {
    ".pyc", ".pyo", ".pyd", ".log", ".tmp"
}

files_catalog = []

# Scan targeted directories
TARGET_DIRS = ["core", "runtime", "android", "tools", "assets", "docs", "tests", "dist"]

for target in TARGET_DIRS:
    base = ROOT / target
    if not base.exists():
        continue
    for dirpath, dirnames, filenames in os.walk(base):
        # Exclude directories
        dirnames[:] = [d for d in dirnames if d not in EXCLUDE_DIRS and not d.startswith(".")]
        for fn in filenames:
            ext = os.path.splitext(fn)[1].lower()
            if ext in EXCLUDE_EXTENSIONS:
                continue
            full_path = Path(dirpath) / fn
            rel_path = full_path.relative_to(ROOT).as_posix()

            # Classification
            classification = "other"
            if rel_path.startswith("core/capabilities/capability_policy.py") or \
               rel_path.startswith("core/capabilities/registry.py") or \
               rel_path.startswith("core/security/audit_ledger.py"):
                classification = "frozen_core"
            elif rel_path.startswith("core/"):
                classification = "core_subsystem"
            elif rel_path.startswith("runtime/"):
                classification = "runtime_service"
            elif rel_path.startswith("android/"):
                classification = "android_source"
            elif rel_path.startswith("dist/android/"):
                classification = "android_distributable"
            elif rel_path.startswith("dist/"):
                classification = "distributable"
            elif rel_path.startswith("tools/"):
                classification = "tooling_and_automation"
            elif rel_path.startswith("tests/"):
                classification = "regression_test"
            elif rel_path.startswith("docs/"):
                classification = "documentation"
            elif rel_path.startswith("assets/"):
                classification = "asset"

            files_catalog.append({
                "relative_path": rel_path,
                "size_bytes": full_path.stat().st_size,
                "sha256": sha256_file(full_path),
                "classification": classification
            })

# Sort by relative_path
files_catalog.sort(key=lambda x: x["relative_path"])

manifest = {
    "version": "9.0.1",
    "release": "V9.1",
    "release_type": "GOLDEN_RELEASE",
    "total_files": len(files_catalog),
    "files": files_catalog
}

with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
    json.dump(manifest, f, indent=2)

print(f"GOLDEN FILE MANIFEST GENERATED: {len(files_catalog)} files cataloged in {OUTPUT_FILE}")
