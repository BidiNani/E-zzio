import sys
sys.path.insert(0, r"G:\AI\E-zzio")

from kokoro_onnx import Kokoro

MODEL = r"G:\AI\E-zzio\runtime\realtime\models\kokoro\kokoro-v0_19.onnx"
VOICES = r"G:\AI\E-zzio\runtime\realtime\models\kokoro\voices.bin"

kokoro = Kokoro(MODEL, VOICES)

print("=" * 70)
print(" E-ZZIO — INVENTAIRE FORENSIQUE DES VOIX KOKORO")
print("=" * 70)

voices = list(kokoro.voices)

print(f"\nNombre de voix disponibles : {len(voices)}\n")

for i, voice in enumerate(voices, 1):
    print(f"{i:3d}. {voice}")

print("\n" + "=" * 70)
print(" VOIX FRANÇAISES / CANDIDATES")
print("=" * 70)

candidates = [
    v for v in voices
    if v.lower().startswith(("fr_", "ff_", "f_"))
    or "french" in v.lower()
    or "fr" in v.lower()
]

if candidates:
    for v in candidates:
        print(f"  -> {v}")
else:
    print("  Aucune candidate détectée automatiquement.")

print("=" * 70)
