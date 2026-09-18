import hashlib
import json
import sys

files = ['core/capabilities/capability_policy.py', 'core/capabilities/registry.py', 'core/security/audit_ledger.py']
manifest = json.load(open('docs/FROZEN_CORE_MANIFEST.json'))['components']
for f in files:
    h = hashlib.sha256(open(f, 'rb').read()).hexdigest().lower()
    expected = manifest.get(f, {}).get('sha256', '').lower()
    if h != expected:
        sys.exit(1)
print("FROZEN_CORE_OK")
