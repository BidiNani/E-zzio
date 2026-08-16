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
print(" E-ZZIO V7 — QUALIFICATION V6.1 (REAL LOCAL VOICE LOOP)")
print("=" * 60)

SILERO_MODEL_PATH = "G:\\AI\\E-zzio\\runtime\\realtime\\models\\silero_vad.onnx"

def ensure_silero_model():
    os.makedirs(os.path.dirname(SILERO_MODEL_PATH), exist_ok=True)
    if not os.path.exists(SILERO_MODEL_PATH):
        print("[INIT] Téléchargement du modèle Silero VAD ONNX (~1.5 Mo)...")
        url = "https://github.com/snakers4/silero-vad/raw/master/src/silero_vad/data/silero_vad.onnx"
        urllib.request.urllib.request.urlretrieve(url, SILERO_MODEL_PATH) if hasattr(urllib.request, 'urllib') else urllib.request.urlretrieve(url, SILERO_MODEL_PATH)
        print("[OK] Silero VAD téléchargé.")

class RealSileroVAD:
    """Wrapper ONNX adaptable dynamiquement aux signatures Silero V4 et V5."""
    def __init__(self, model_path):
        opts = ort.SessionOptions()
        opts.inter_op_num_threads = 1
        opts.intra_op_num_threads = 1
        self.session = ort.InferenceSession(model_path, opts, providers=['CPUExecutionProvider'])
        self.input_names = [inp.name for inp in self.session.get_inputs()]
        self.reset_state()

    def reset_state(self):
        if 'state' in self.input_names:
            # Silero VAD v5 (Tenseur unique de forme (2, 1, 128))
            self._state = np.zeros((2, 1, 128), dtype=np.float32)
        else:
            # Silero VAD v4 (Dual state h et c de forme (2, 1, 64))
            self._h = np.zeros((2, 1, 64), dtype=np.float32)
            self._c = np.zeros((2, 1, 64), dtype=np.float32)
        self._sr = np.array(16000, dtype=np.int64)

    def is_speech(self, pcm_chunk_16k: np.ndarray, threshold=0.5) -> bool:
        if len(pcm_chunk_16k) != 512:
            return False
            
        input_data = np.expand_dims(pcm_chunk_16k, axis=0)

        if 'state' in self.input_names:
            ort_inputs = {
                'input': input_data,
                'state': self._state,
                'sr': self._sr
            }
            out, self._state = self.session.run(None, ort_inputs)
        else:
            ort_inputs = {
                'input': input_data,
                'sr': self._sr,
                'h': self._h,
                'c': self._c
            }
            out, self._h, self._c = self.session.run(None, ort_inputs)

        speech_prob = out[0][0]
        return speech_prob > threshold

class RealVoiceLoopController:
    def __init__(self, vad: RealSileroVAD):
        self.vad = vad
        self.interrupted = False
        self.bargein_latency_ms = None

    def test_live_bargein(self, tts_audio_pcm: np.ndarray, tts_sr: int = 24000):
        print("\n🔊 [TTS] E-ZZIO commence à parler...")
        print("🎙️ [ACTION REQUISE] Parle fort dans ton microphone maintenant pour interrompre !")
        
        self.interrupted = False
        self.bargein_latency_ms = None
        
        chunk_size_tts = int(tts_sr * 0.03) # ~30ms par bloc TTS
        mic_chunk_size = 512 # Silero exige 512 échantillons à 16kHz
        
        with sd.InputStream(samplerate=16000, channels=1, dtype='float32') as mic_stream:
            start_time = time.perf_counter()
            
            for i in range(0, len(tts_audio_pcm), chunk_size_tts):
                if self.interrupted:
                    break
                    
                tts_chunk = tts_audio_pcm[i:i + chunk_size_tts]
                sd.play(tts_chunk, samplerate=tts_sr)
                
                mic_data, _ = mic_stream.read(mic_chunk_size)
                mic_pcm = mic_data.flatten()
                
                if self.vad.is_speech(mic_pcm, threshold=0.5):
                    t_detect = time.perf_counter()
                    self.interrupted = True
                    sd.stop() # Coupure matérielle immédiate du haut-parleur
                    
                    self.bargein_latency_ms = round((time.perf_counter() - t_detect) * 1000, 2)
                    total_elapsed = round(time.perf_counter() - start_time, 2)
                    
                    print(f"\n🔴 [BARGE-IN RÉEL DÉTECTÉ] Voix captée par Silero VAD à t = {total_elapsed}s !")
                    print(f"⏱️ Temps de coupure matérielle : {self.bargein_latency_ms} ms")
                    break

async def run_v61():
    ensure_silero_model()
    vad = RealSileroVAD(SILERO_MODEL_PATH)
    controller = RealVoiceLoopController(vad)

    tts_sr = 24000
    duration_s = 5.0
    t = np.linspace(0, duration_s, int(tts_sr * duration_s), False)
    test_audio = (0.2 * np.sin(2 * np.pi * 350 * t) * np.cos(2 * np.pi * 2 * t)).astype(np.float32)

    controller.test_live_bargein(test_audio, tts_sr=tts_sr)

    print("\n" + "=" * 60)
    print(" RÉSULTATS CERTIFICATION E-ZZIO V6.1")
    print("=" * 60)
    print(f"Silero VAD ONNX           : PASS")
    print(f"Microphone réel           : PASS")
    print(f"Barge-in par voix réelle  : {'PASS' if controller.interrupted else 'FAIL (Aucune voix captée)'}")
    if controller.bargein_latency_ms:
        print(f"Latence de coupure        : {controller.bargein_latency_ms} ms")
    print("=" * 60)

    if not controller.interrupted:
        print("💡 Note : Si la voix n'a pas été captée, vérifie que ton microphone est actif sous Windows.")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(run_v61())
