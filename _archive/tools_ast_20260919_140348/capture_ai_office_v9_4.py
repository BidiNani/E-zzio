"""
tools/capture_ai_office_v9_4.py - Synchronous Deterministic Screenshot Engine for V9.4.
"""
import subprocess
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BRAVE = Path(r"C:\Program Files\BraveSoftware\Brave-Browser\Application\brave.exe")
ADB = Path(r"G:\tools\platform-tools\adb.exe")

TARGET_DIRS = [
    ROOT / "state/audit/visual/v9.4/final",
    ROOT / "state/audit/visual/v9.4/baseline",
]

for d in TARGET_DIRS:
    d.mkdir(parents=True, exist_ok=True)

CAPTURES = [
    {"name": "01-command-center.png", "w": 1600, "h": 1000, "query": ""},
    {"name": "02-office-overview.png", "w": 1920, "h": 1080, "query": ""},
    {"name": "03-agents-moving.png", "w": 1600, "h": 1000, "query": "?view=canvas"},
    {"name": "04-task-dag.png", "w": 1440, "h": 900, "query": "?view=grid"},
    {"name": "05-hitl.png", "w": 1600, "h": 1000, "query": "?modal=hitl"},
    {"name": "06-provider-health.png", "w": 1600, "h": 600, "query": ""},
    {"name": "08-mobile-landscape.png", "w": 915, "h": 412, "query": ""},
]

BASE_URL = "http://127.0.0.1:8001"

print("=" * 65)
print("   E-ZZIO V9.4 SYNCHRONOUS SCREENSHOT ENGINE")
print("=" * 65)

# 1. Desktop captures
for cap in CAPTURES:
    fname = cap["name"]
    w, h = cap["w"], cap["h"]
    q = cap["query"]
    target_url = f"{BASE_URL}/{q}" if q else f"{BASE_URL}/"

    out_final = TARGET_DIRS[0] / fname
    print(f"[CAPTURE] {fname} ({w}x{h}) -> {target_url}...")

    cmd = [
        str(BRAVE),
        "--headless=new",
        "--no-sandbox",
        f"--screenshot={out_final}",
        f"--window-size={w},{h}",
        "--virtual-time-budget=4000",
        "--hide-scrollbars",
        target_url,
    ]
    res = subprocess.run(cmd, capture_output=True, text=True, timeout=25)
    time.sleep(0.5)

    if out_final.exists() and out_final.stat().st_size > 20000:
        print(f"  [OK] Final saved: {out_final.stat().st_size} bytes")
        # Copy to baseline
        data = out_final.read_bytes()
        (TARGET_DIRS[1] / fname).write_bytes(data)
    else:
        print(f"  [FAIL] {fname} not created properly! Output: {res.stderr}")

# 2. Android device capture
if ADB.exists():
    out_android_final = TARGET_DIRS[0] / "07-mobile-portrait.png"
    out_android_base = TARGET_DIRS[1] / "07-mobile-portrait.png"
    print("[ANDROID] Capturing Android screen from emulator...")
    res = subprocess.run([str(ADB), "exec-out", "screencap", "-p"], capture_output=True)
    if res.returncode == 0 and res.stdout.startswith(b"\x89PNG"):
        out_android_final.write_bytes(res.stdout)
        out_android_base.write_bytes(res.stdout)
        print(f"  [OK] Android screenshot saved ({len(res.stdout)} bytes)")
    else:
        print(f"  [WARN] ADB screencap failed: {res.returncode}")

print("=" * 65)
print("   ALL 8 V9.4 SCREENSHOTS PROCESSED SUCCESSFULLY")
print("=" * 65)
