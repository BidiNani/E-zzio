import hashlib
import json
import sys

files = [
    "core/capabilities/capability_policy.py",
    "core/capabilities/registry.py",
    "core/security/audit_ledger.py",
]

with open("docs/FROZEN_CORE_MANIFEST.json", encoding="utf-8") as f:
    raw = json.load(f)

# Support des 2 formats : "files" (nouveau) et "components" (ancien)
if "files" in raw:
    manifest = raw["files"]
elif "components" in raw:
    manifest = {
        path: meta["sha256"] if isinstance(meta, dict) else meta
        for path, meta in raw["components"].items()
    }
else:
    print("FROZEN_CORE_FAIL: manifest format inconnu")
    sys.exit(1)

for path in files:
    h = hashlib.sha256(open(path, "rb").read()).hexdigest().lower()
    expected = manifest.get(path, "").lower()
    if h != expected:
        print(f"FROZEN_CORE_FAIL: {path}")
        sys.exit(1)

print("FROZEN_CORE_OK")