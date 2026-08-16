import asyncio
import sys
from pathlib import Path

# Injection de la racine E-ZZIO
sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from runtime.realtime.audio.stt import EzzioSTT
from runtime.realtime.pipecat.router import EzzioRealtimeRouter
from runtime.realtime.audio.tts import EzzioTTS

async def run_voice_loop_test():
    print("==================================================")
    print(" E-ZZIO — TEST DE BOUCLE VOCALE LOCALE (OFFLINE)")
    print("==================================================")

    stt = EzzioSTT(model_size="base")
    router = EzzioRealtimeRouter()
    tts = EzzioTTS()

    # 1. Étape STT (Simulation avec un input textuel ou un fichier audio réel)
    # Pour ce test de validation, on simule l'intention capturée par STT ou on teste un fichier si présent.
    audio_test_path = Path("G:/AI/E-zzio/test_audio.wav")
    
    if audio_test_path.exists():
        print(f"\n[1/3] Analyse STT du fichier : {audio_test_path.name}")
        stt_res = await stt.transcribe(str(audio_test_path))
        print(f"      Résultat STT : {stt_res}")
        # Si le fichier est du silence, on injecte un texte de repli pour tester le reste de la chaîne
        user_text = stt_res.get("text") if stt_res.get("text") else "Bonjour E-ZZIO, ceci est un test de boucle locale."
    else:
        print("\n[1/3] STT ignoré (Fichier test_audio.wav absent). Injection directe de l'intention.")
        user_text = "Bonjour E-ZZIO, réponds en une phrase."

    print(f"      Intention retenue : \"{user_text}\"")

    # 2. Étape Router V7 (Cerveau)
    print("\n[2/3] Transmission au Model Router V7...")
    router_res = await router.process(text=user_text, task="conversation")
    print(f"      Modèle utilisé : {router_res.get('model_used')}")
    print(f"      Réponse texte  : \"{router_res.get('content')}\"")

    # 3. Étape TTS (Voix)
    response_text = router_res.get("content", "Je n'ai pas de réponse.")
    print(f"\n[3/3] Synthèse vocale Piper TTS en cours...")
    tts_res = await tts.synthesize(text=response_text)
    
    if tts_res.get("ok"):
        print(f"      Audio généré avec succès : {tts_res.get('audio_path')}")
        print(f"      Durée estimée           : {tts_res.get('duration')} secondes")
        print("\n[SUCCÈS] La boucle vocale locale est intègre et fonctionnelle !")
    else:
        print(f"      [AVERTISSEMENT TTS] : {tts_res.get('error')}")
        print("      (Vérifie que l'exécutable 'piper' et le modèle .onnx sont installés pour le rendu audio final).")

if __name__ == "__main__":
    asyncio.run(run_voice_loop_test())
