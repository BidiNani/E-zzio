# ruff: noqa: E701
import os
import re
import sys
import zipfile

patterns = [re.compile(r'AIza[0-9A-Za-z-_]{35}'), re.compile(r'gsk_[0-9A-Za-z]{40,}'), re.compile(r'Bearer\s+[A-Za-z0-9\-\._~\+\/]{20,}='), re.compile(r'-----BEGIN (?:RSA )?PRIVATE KEY-----')]
targets = ['tools/launch_desktop.ps1', 'tools/build_android_apk.ps1', 'runtime/web/index.html', 'android/app/build.gradle', 'android/app/src/main/AndroidManifest.xml']
for t in targets:
    if os.path.exists(t):
        c = open(t, encoding='utf-8', errors='ignore').read()
        for p in patterns:
            if p.search(c): sys.exit(1)
apk = 'dist/android/E-ZzIO-v9.1-release.apk'
if os.path.exists(apk):
    with zipfile.ZipFile(apk, 'r') as z:
        for item in z.infolist():
            d = z.read(item.filename)
            for p in patterns:
                if p.search(d.decode('latin1', errors='ignore')): sys.exit(1)
print("SECRETS_SCAN_OK")
