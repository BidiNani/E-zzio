import re
from typing import Optional
from pipecat.processors.frame_processor import FrameDirection, FrameProcessor
from pipecat.frames.frames import (
    Frame,
    AudioRawFrame,
    InputAudioRawFrame,
    OutputAudioRawFrame,
    TextFrame,
    ErrorFrame
)

from runtime.realtime.audio.stt import EzzioSTT
from runtime.realtime.pipecat.router import EzzioRealtimeRouter
from runtime.realtime.audio.tts import EzzioTTS

class EzzioSTTProcessor(FrameProcessor):
    """Processeur STT : Transcode l'audio en texte et transmet impérativement les frames de contrôle."""
    def __init__(self, stt_engine: Optional[EzzioSTT] = None, **kwargs):
        super().__init__(**kwargs)
        self.stt = stt_engine or EzzioSTT()

    async def process_frame(self, frame: Frame, direction: FrameDirection):
        await super().process_frame(frame, direction)

        if isinstance(frame, (AudioRawFrame, InputAudioRawFrame)):
            result = await self.stt.transcribe(frame.audio)
            if result.get("ok") and result.get("text"):
                await self.push_frame(TextFrame(result["text"]), direction)
        else:
            # Transfert OBLIGATOIRE des frames système/contrôle (StartFrame, EndFrame, CancelFrame, etc.)
            await self.push_frame(frame, direction)


class EzzioRouterProcessor(FrameProcessor):
    """Processeur Router V7 : Achemine l'intention textuelle et découpe la réponse."""
    def __init__(self, router: Optional[EzzioRealtimeRouter] = None, **kwargs):
        super().__init__(**kwargs)
        self.router = router or EzzioRealtimeRouter()
        self.punctuation_regex = re.compile(r'([.?!;:]\s+)')

    async def process_frame(self, frame: Frame, direction: FrameDirection):
        await super().process_frame(frame, direction)

        if isinstance(frame, TextFrame):
            res = await self.router.process(text=frame.text, task="conversation")
            if res.get("ok"):
                content = res.get("content", "")
                chunks = self.punctuation_regex.split(content)
                buffer = ""
                for part in chunks:
                    buffer += part
                    if self.punctuation_regex.search(part):
                        await self.push_frame(TextFrame(buffer.strip()), direction)
                        buffer = ""
                if buffer.strip():
                    await self.push_frame(TextFrame(buffer.strip()), direction)
            else:
                await self.push_frame(ErrorFrame(res.get("content", "Erreur routage")), direction)
        else:
            # Transfert OBLIGATOIRE des frames non-textuelles
            await self.push_frame(frame, direction)


class EzzioTTSProcessor(FrameProcessor):
    """Processeur TTS : Synthétise le texte en audio et transmet le reste."""
    def __init__(self, tts_engine: Optional[EzzioTTS] = None, **kwargs):
        super().__init__(**kwargs)
        self.tts = tts_engine or EzzioTTS()

    async def process_frame(self, frame: Frame, direction: FrameDirection):
        await super().process_frame(frame, direction)

        if isinstance(frame, TextFrame):
            res = await self.tts.synthesize(text=frame.text)
            if res.get("ok"):
                audio_path = res.get("audio_path")
                try:
                    with open(audio_path, "rb") as f:
                        pcm_data = f.read()
                    await self.push_frame(
                        OutputAudioRawFrame(audio=pcm_data, sample_rate=16000, num_channels=1),
                        direction
                    )
                except Exception as e:
                    await self.push_frame(ErrorFrame(f"Erreur lecture audio TTS: {str(e)}"), direction)
        else:
            # Transfert OBLIGATOIRE des frames non-textuelles
            await self.push_frame(frame, direction)
