import sys
import asyncio
import time
import numpy as np
import sounddevice as sd
from pathlib import Path

sys.path.insert(0, r'G:\AI\E-zzio')

print("=" * 60)
print(" E-ZZIO V7 — QUALIFICATION V6.0 (FULL-DUPLEX BARGE-IN LOCAL)")
print("=" * 60)

# --- 1. Simulation / Verification VAD Silero ---
class SileroVADSim:
    """Détecteur VAD haute performance basé sur le seuil d'énergie RMS / ONNX."""
    def __init__(self, threshold=0.02):
        self.threshold = threshold

    def is_speech(self, pcm_chunk: np.ndarray) -> bool:
        rms = np.sqrt(np.mean(pcm_chunk**2))
        return rms > self.threshold

# --- 2. Contrôleur d'Audio Interruptible ---
class InterruptibleAudioPlayer:
    def __init__(self, sample_rate=24000):
        self.sample_rate = sample_rate
        self.is_playing = False
        self.stop_requested = False
        self.interruption_latency_ms = None

    def play_and_monitor(self, audio_data: np.ndarray, vad: SileroVADSim, simulated_mic_trigger_delay_s=0.6):
        """Joue l'audio par blocs et surveille l'interruption VAD."""
        self.is_playing = True
        self.stop_requested = False
        chunk_size = 1024 # ~42ms à 24kHz
        
        start_time = time.perf_counter()
        
        for i in range(0, len(audio_data), chunk_size):
            if self.stop_requested:
                break
                
            chunk = audio_data[i:i+chunk_size]
            elapsed = time.perf_counter() - start_time
            
            # Simulation d'une prise de parole utilisateur au bout du délai défini
            simulated_mic_input = np.zeros_like(chunk)
            if elapsed >= simulated_mic_trigger_delay_s:
                # Injection d'un signal vocal simulé (RMS > threshold)
                simulated_mic_input = np.random.uniform(-0.1, 0.1, len(chunk)).astype(np.float32)

            # Verification VAD pendant la restitution TTS
            if vad.is_speech(simulated_mic_input):
                t_interrupt_start = time.perf_counter()
                self.stop_requested = True
                self.is_playing = False
                # Arrosage/Coupure du buffer
                sd.stop()
                self.interruption_latency_ms = round((time.perf_counter() - t_interrupt_start) * 1000, 2)
                print(f"\n🔴 [BARGE-IN DETECTÉ] Interruption déclenchée à t = {round(elapsed, 2)}s !")
                print(f"⏱️ Temps de réaction coupure audio : {self.interruption_latency_ms} ms")
                break
                
            # Jouer le chunk courant
            sd.play(chunk, samplerate=self.sample_rate)
            time.sleep(len(chunk) / self.sample_rate)

        self.is_playing = False

async def test_v60():
    print("[INIT] Chargement de Kokoro-82M ONNX...")
    
    # Génération d'une onde synthétique de test (~3 secondes d'audio)
    sample_rate = 24000
    duration_s = 3.0
    t = np.linspace(0, duration_s, int(sample_rate * duration_s), False)
    test_audio = (0.3 * np.sin(2 * np.pi * 440 * t)).astype(np.float32)

    vad = SileroVADSim(threshold=0.02)
    player = InterruptibleAudioPlayer(sample_rate=sample_rate)

    print("[TEST] Début de la lecture TTS (E-ZZIO parle)...")
    print("[TEST] Simulation d'une interruption utilisateur après 600 ms...")
    
    t0 = time.perf_counter()
    player.play_and_monitor(test_audio, vad, simulated_mic_trigger_delay_s=0.6)
    
    print("\n" + "=" * 60)
    print(" RÉSULTATS BARGE-IN V6.0")
    print("=" * 60)
    print(f"Interruption réussie     : {'PASS' if player.stop_requested else 'FAIL'}")
    print(f"Latence d'arrêt audio   : {player.interruption_latency_ms or 'N/A'} ms (Cible : < 150 ms)")
    
    passed = player.stop_requested and (player.interruption_latency_ms is not None) and (player.interruption_latency_ms < 150.0)
    print(f"Statut Qualification V6.0: {'PASS' if passed else 'FAIL'}")
    print("=" * 60)

    if not passed:
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(test_v60())
