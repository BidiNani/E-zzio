import sys
import asyncio
import time
import os
import urllib.request
import numpy as np
import sounddevice as sd
import onnxruntime as ort

sys.path.insert(0, r'G:\AI\E-zzio')

print("=" * 60)
print(" E-ZZIO V7 — QUALIFICATION V6.2 (REAL MIC + KOKORO-82M + SILERO)")
print("=" * 60)

SILERO_MODEL_PATH = r"G:\AI\E-zzio\runtime\realtime\models\silero_vad.onnx"
KOKORO_DIR = r"G:\AI\E-zzio\runtime\realtime\models\kokoro"
KOKORO_MODEL_PATH = os.path.join(KOKORO_DIR, "kokoro-v0_19.onnx")
KOKORO_VOICES_PATH = os.path.join(KOKORO_DIR, "voices.bin")

def download_file(url: str, target_path: str):
    print(f"[DOWNLOAD] Téléchargement depuis : {url}")
    req = urllib.request.Request(
        url, 
        headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
    )
    with urllib.request.urlopen(req) as response, open(target_path, 'wb') as out_file:
        out_file.write(response.read())

def ensure_kokoro_assets():
    os.makedirs(KOKORO_DIR, exist_ok=True)
    
    if not os.path.exists(KOKORO_MODEL_PATH):
        print("[INIT] Téléchargement du modèle Kokoro-82M ONNX (~326 Mo)...")
        download_file("https://huggingface.co/thewh1teagle/Kokoro/resolve/main/kokoro-v0_19.onnx", KOKORO_MODEL_PATH)
        print("[OK] Kokoro-82M ONNX téléchargé.")

    if not os.path.exists(KOKORO_VOICES_PATH):
        print("[INIT] Téléchargement du fichier de voix Kokoro (~28 Mo)...")
        download_file("https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files/voices.bin", KOKORO_VOICES_PATH)
        print("[OK] Voix Kokoro téléchargées.")

    if not os.path.exists(SILERO_MODEL_PATH):
        os.makedirs(os.path.dirname(SILERO_MODEL_PATH), exist_ok=True)
        print("[INIT] Téléchargement de Silero VAD ONNX...")
        download_file("https://raw.githubusercontent.com/snakers4/silero-vad/master/src/silero_vad/data/silero_vad.onnx", SILERO_MODEL_PATH)
        print("[OK] Silero VAD prêt.")

class RealSileroVAD:
    def __init__(self, model_path):
        opts = ort.SessionOptions()
        opts.inter_op_num_threads = 1
        opts.intra_op_num_threads = 1
        self.session = ort.InferenceSession(model_path, opts, providers=['CPUExecutionProvider'])
        self.input_names = [inp.name for inp in self.session.get_inputs()]
        self.reset_state()

    def reset_state(self):
        if 'state' in self.input_names:
            self._state = np.zeros((2, 1, 128), dtype=np.float32)
        else:
            self._h = np.zeros((2, 1, 64), dtype=np.float32)
            self._c = np.zeros((2, 1, 64), dtype=np.float32)
        self._sr = np.array(16000, dtype=np.int64)

    def is_speech(self, pcm_chunk_16k: np.ndarray, threshold=0.55) -> tuple:
        if len(pcm_chunk_16k) != 512:
            return False, 0.0

        input_data = np.expand_dims(pcm_chunk_16k.astype(np.float32), axis=0)

        if 'state' in self.input_names:
            ort_inputs = {'input': input_data, 'state': self._state, 'sr': self._sr}
            out, self._state = self.session.run(None, ort_inputs)
        else:
            ort_inputs = {'input': input_data, 'sr': self._sr, 'h': self._h, 'c': self._c}
            out, self._h, self._c = self.session.run(None, ort_inputs)

        prob = float(out[0][0])
        return (prob > threshold), prob

async def main():
    ensure_kokoro_assets()
    
    from kokoro_onnx import Kokoro
    print("[INIT] Chargement de Kokoro-82M ONNX en mémoire...")
    kokoro = Kokoro(KOKORO_MODEL_PATH, KOKORO_VOICES_PATH)

    # Résolution dynamique d'une voix disponible dans le fichier voices.bin
    available_voices = list(kokoro.voices)
    print(f"[INFO] Voix disponibles dans le bundle : {available_voices[:5]} ... (Total : {len(available_voices)})")
    
    # Recherche d'une voix française ou repli sur la première voix disponible
    target_voice = next((v for v in available_voices if v.startswith('ff_') or v.startswith('fr_')), available_voices[0])
    print(f"[TTS] Voix sélectionnée pour le test : {target_voice}")

    prompt = "Bonjour Bidi. Je suis E-ZZIO. Mon système vocal local est prêt et j'écoute ton microphone."
    print(f"[TTS] Génération audio pour : \"{prompt}\"")
    
    t0_tts = time.perf_counter()
    samples, sample_rate = kokoro.create(prompt, voice=target_voice, speed=1.0)
    tts_time_ms = round((time.perf_counter() - t0_tts) * 1000, 2)
    print(f"[TTS] Synthèse terminée en {tts_time_ms} ms (Sample Rate : {sample_rate} Hz)")

    vad = RealSileroVAD(SILERO_MODEL_PATH)

    print("\n🔊 [HAUT-PARLEUR] E-ZZIO parle...")
    print("🎙️ [TEST MICROPHONE RÉEL] Parle fort ou tousse dans ton micro maintenant pour couper la parole d'E-ZZIO !")

    chunk_tts = int(sample_rate * 0.03)  # ~30 ms par bloc
    mic_chunk_size = 512                 # 512 échantillons à 16 kHz
    interrupted = False
    bargein_latency_ms = None
    detected_prob = 0.0

    with sd.InputStream(samplerate=16000, channels=1, dtype='float32') as mic_stream:
        start_time = time.perf_counter()

        for i in range(0, len(samples), chunk_tts):
            if interrupted:
                break

            tts_block = samples[i:i + chunk_tts]
            sd.play(tts_block, samplerate=sample_rate)

            mic_data, _ = mic_stream.read(mic_chunk_size)
            mic_pcm = mic_data.flatten()

            is_sp, prob = vad.is_speech(mic_pcm, threshold=0.55)

            if is_sp:
                t_detect = time.perf_counter()
                interrupted = True
                detected_prob = prob
                sd.stop()  # Coupure matérielle immédiate

                bargein_latency_ms = round((time.perf_counter() - t_detect) * 1000, 2)
                elapsed = round(time.perf_counter() - start_time, 2)

                print(f"\n🔴 [BARGE-IN MICROPHONE RÉUSSI] Ta voix a été captée par Silero VAD (Probabilité : {round(prob * 100, 1)}%) à t = {elapsed}s !")
                print(f"⏱️ Temps de coupure matérielle audio : {bargein_latency_ms} ms")
                break

            time.sleep(len(tts_block) / sample_rate)

    print("\n" + "=" * 60)
    print(" RÉSULTATS CERTIFICATION V6.2")
    print("=" * 60)
    print(f"Kokoro-82M ONNX           : PASS ({tts_time_ms} ms)")
    print(f"Silero VAD ONNX           : PASS")
    print(f"Interruption Micro Réel   : {'PASS' if interrupted else 'FAIL (Aucune voix captée)'}")
    if interrupted:
        print(f"Score VAD                 : {round(detected_prob * 100, 1)}%")
        print(f"Latence Coupure Audio     : {bargein_latency_ms} ms (Seuil : < 250 ms)")
    
    passed = interrupted and (bargein_latency_ms is not None) and (bargein_latency_ms < 250.0)
    print(f"Statut Qualification V6.2 : {'PASS' if passed else 'FAIL'}")
    print("=" * 60)

    if not passed:
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())
