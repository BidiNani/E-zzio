from kokoro_onnx import Kokoro
model_path = r"G:\AI\E-zzio\runtime\realtime\models\kokoro\kokoro-v0_19.onnx"
cand_path = r"G:\AI\E-zzio\runtime\realtime\models\kokoro\voices_extended.bin"

k = Kokoro(model_path, cand_path)
voices = list(k.voices)
print(f"[OK] Loader initialisé. Voix totales détectées : {len(voices)}")
if "ff_siwis" in voices:
    print("[SUCCESS 10/10] La voix 'ff_siwis' est certifiée et reconnue par le runtime principal !")
else:
    raise RuntimeError("[FAIL] 'ff_siwis' est absente des voix chargées.")
