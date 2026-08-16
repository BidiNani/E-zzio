import asyncio
from pathlib import Path
from typing import Dict, Any, Optional
from faster_whisper import WhisperModel

class EzzioSTT:
    """
    Moteur STT (Speech-to-Text) local basé sur faster-whisper.
    """
    def __init__(self, model_size: str = "base", device: str = "cpu", compute_type: str = "int8"):
        self.model_size = model_size
        self.device = device
        self.compute_type = compute_type
        self._model: Optional[WhisperModel] = None

    def _load_model(self) -> WhisperModel:
        if self._model is None:
            self._model = WhisperModel(self.model_size, device=self.device, compute_type=self.compute_type)
        return self._model

    async def transcribe(self, audio_path: str) -> Dict[str, Any]:
        path = Path(audio_path)
        if not path.exists():
            return {
                "ok": False,
                "text": "",
                "language": "unknown",
                "confidence": 0.0,
                "error": f"Fichier audio introuvable : {audio_path}"
            }

        loop = asyncio.get_running_loop()
        try:
            def _sync_transcribe():
                model = self._load_model()
                segments, info = model.transcribe(str(path), beam_size=5)
                text_list = [segment.text for segment in segments]
                full_text = " ".join(text_list).strip()
                
                # Utilisation de la vraie métrique de probabilité Whisper
                confidence = round(getattr(info, "language_probability", 0.95), 3) if full_text else 0.0
                
                return {
                    "ok": True,
                    "text": full_text,
                    "language": info.language,
                    "confidence": confidence
                }

            return await loop.run_in_executor(None, _sync_transcribe)
            
        except Exception as e:
            return {
                "ok": False,
                "text": "",
                "language": "unknown",
                "confidence": 0.0,
                "error": str(e)
            }
