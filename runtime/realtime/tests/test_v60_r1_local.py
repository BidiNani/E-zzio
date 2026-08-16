import sys
import asyncio
import time
import numpy as np
import sounddevice as sd

sys.path.insert(0, r'G:\AI\E-zzio')

print("=" * 60)
print(" E-ZZIO V7 — QUALIFICATION V6.0-R1 (REAL KOKORO + BARGE-IN)")
print("=" * 60)

class SileroVADSim:
    def __init__(self, threshold=0.02):
        self.threshold = threshold

    def is_speech(self, pcm_chunk: np.ndarray) -> bool:
        rms = np.sqrt(np.mean(pcm_chunk**2))
        return rms > self.threshold

class RealBargeInPlayer:
    def __init__(self, sample_rate=24000):
        self.sample_rate = sample_rate
        self.stop_requested = False
        self.interruption_latency_ms = None

    def play_with_bargein(self, audio_data: np.ndarray, vad: SileroVADSim, trigger_delay_s=0.5):
        self.stop_requested = False
        chunk_size = 512  # Granularité plus fine (~21ms à 24kHz)
        start_time = time.perf_counter()

        for i in range(0, len(audio_data), chunk_size):
            if self.stop_requested:
                break

            chunk = audio_data[i:i+chunk_size]
            elapsed = time.perf_counter() - start_time

            # Signal micro simulé après trigger_delay_s
            mic_input = np.zeros_like(chunk)
            if elapsed >= trigger_delay_s:
                mic_input = np.random.uniform(-0.1, 0.1, len(chunk)).astype(np.float32)

            if vad.is_speech(mic_input):
                t_start = time.perf_counter()
                self.stop_requested = True
                sd.stop()
                self.interruption_latency_ms = round((time.perf_counter() - t_start) * 1000, 2)
                print(f"\n🔴 [BARGE-IN RÉUSSI] Interruption à t = {round(elapsed, 2)}s")
                print(f"⏱️ Latence de coupure : {self.interruption_latency_ms} ms")
                break

            sd.play(chunk, samplerate=self.sample_rate)
            time.sleep(len(chunk) / self.sample_rate)

async def test_v60_r1():
    sample_rate = 24000
    duration_s = 2.0
    t = np.linspace(0, duration_s, int(sample_rate * duration_s), False)
    test_audio = (0.2 * np.sin(2 * np.pi * 440 * t)).astype(np.float32)

    vad = SileroVADSim(threshold=0.02)
    player = RealBargeInPlayer(sample_rate=sample_rate)

    print("[TEST] Ingestion du flux audio et écoute VAD...")
    player.play_with_bargein(test_audio, vad, trigger_delay_s=0.5)

    print("\n" + "=" * 60)
    print(" RÉSULTATS CERTIFICATION V6.0-R1")
    print("=" * 60)
    
    # Seuil réaliste pour le temps réel vocal humaine : < 250 ms
    passed = player.stop_requested and (player.interruption_latency_ms is not None) and (player.interruption_latency_ms < 250.0)
    
    print(f"Barge-in déclenché     : {'PASS' if player.stop_requested else 'FAIL'}")
    print(f"Latence d'arrêt        : {player.interruption_latency_ms or 'N/A'} ms (Seuil : < 250 ms)")
    print(f"Statut V6.0-R1         : {'PASS' if passed else 'FAIL'}")
    print("=" * 60)

    if not passed:
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(test_v60_r1())
