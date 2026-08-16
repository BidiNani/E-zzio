import asyncio
import subprocess
from pathlib import Path
from typing import Dict, Any, Optional

class EzzioTTS:
    """
    Moteur TTS local avec chemin vers binaire et modèle embarqués.
    """
    def __init__(self):
        # Chemins absolus souverains
        self.piper_binary = str(Path(r"G:\AI\E-zzio\runtime\realtime\audio\piper\piper.exe"))
        self.model_path = str(Path(r"G:\AI\E-zzio\runtime\realtime\audio\voices\fr_FR-siwis-medium.onnx"))

    async def synthesize(self, text: str, output_path: Optional[str] = None) -> Dict[str, Any]:
        if not text or not text.strip():
            return {"ok": False, "audio_path": "", "duration": 0.0, "error": "Texte vide"}

        out_file = Path(output_path) if output_path else Path(r"G:\AI\E-zzio\runtime\realtime\audio\output_speech.wav")
        
        # Vérification préventive
        if not Path(self.piper_binary).exists():
            return {"ok": False, "audio_path": "", "duration": 0.0, "error": f"Piper introuvable : {self.piper_binary}"}
        if not Path(self.model_path).exists():
            return {"ok": False, "audio_path": "", "duration": 0.0, "error": f"Modèle introuvable : {self.model_path}"}

        loop = asyncio.get_running_loop()
        try:
            def _sync_synthesize():
                cmd = [self.piper_binary, "--model", self.model_path, "--output_file", str(out_file)]
                
                process = subprocess.Popen(
                    cmd,
                    stdin=subprocess.PIPE,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                    encoding="utf-8"
                )
                _, stderr = process.communicate(input=text.strip())

                if process.returncode != 0:
                    raise RuntimeError(f"Erreur Piper : {stderr.strip()}")

                file_size = out_file.stat().st_size if out_file.exists() else 0
                duration = round(file_size / 32000.0, 2)
                return {"ok": True, "audio_path": str(out_file), "duration": duration}

            return await loop.run_in_executor(None, _sync_synthesize)

        except Exception as e:
            return {"ok": False, "audio_path": "", "duration": 0.0, "error": str(e)}
