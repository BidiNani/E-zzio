import asyncio
import numpy as np
import sounddevice as sd

class AsyncAudioPlayer:
    def __init__(self, sample_rate: int = 24000, channels: int = 1):
        self.sample_rate = sample_rate
        self.channels = channels
        self.queue = asyncio.Queue()
        self._stream = None
        self._playback_task = None
        self._is_playing = False

    def _callback(self, outdata, frames, time, status):
        """Callback C++ exécuté par PortAudio dans un thread séparé."""
        if status:
            print(f"Audio Output Status: {status}")
            
        try:
            # Récupère le chunk de manière synchrone, non bloquante
            data = self.queue.get_nowait()
            if len(data) < frames:
                outdata[:len(data)] = data.reshape(-1, self.channels)
                outdata[len(data):] = 0
            else:
                outdata[:] = data[:frames].reshape(-1, self.channels)
        except asyncio.QueueEmpty:
            outdata.fill(0)

    async def start(self):
        if self._is_playing:
            return
        
        self._stream = sd.OutputStream(
            samplerate=self.sample_rate,
            channels=self.channels,
            dtype='float32',
            callback=self._callback
        )
        self._stream.start()
        self._is_playing = True

    async def push_chunk(self, audio_data: np.ndarray):
        await self.queue.put(audio_data)

    async def stop(self):
        self._is_playing = False
        if self._stream:
            self._stream.stop()
            self._stream.close()
        
        # Flush queue
        while not self.queue.empty():
            self.queue.get_nowait()
            self.queue.task_done()
