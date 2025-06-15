import io
import os
from functools import lru_cache
from typing import Literal

import aiofiles
import httpx
import numpy as np
import scipy.io.wavfile as wav
from pydantic import BaseModel

from providers.base import TextToSpeechProvider


class ChatterBoxConfig(BaseModel):
    provider: Literal['chatterbox']
    voice: str
    exaggeration: float = 0.6
    cfg_weight: float = 0.5
    temperature: float = 0.7


class ChatterBoxAudioProvider(TextToSpeechProvider):
    SAMPLE_RATE = 24000

    def __init__(self, base_url):
        self.base_url = base_url
        self.voice_file_cache = {}

    async def get_voice_content(self, voice: str) -> bytes:
        if voice not in self.voice_file_cache:
            async with aiofiles.open(f'/voices/{voice}.wav', mode='rb') as f:
                contents = await f.read()

            self.voice_file_cache[voice] = contents

        return self.voice_file_cache[voice]

    async def generate_audio(self, text: str, voice: str) -> bytearray:
        voice_bytes = await self.get_voice_content(voice)
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f'{self.base_url}/v1/audio/speech/upload',
                data=dict(
                    input=text,
                    exaggeration=0.6,
                    speed=0.5,
                    cfg_weight=0.5,
                    temperature=0.7,
                    response_format='wav'
                ),
                files={
                    'voice_file': (f'{voice}.wav', voice_bytes, 'audio/wav')
                },
                timeout=10000
            )
            response.raise_for_status()
            return bytearray(response.content)

    async def generate_audio_stream(self, text: str, voice: str):
        voice_bytes = await self.get_voice_content(voice)
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                f'{self.base_url}/v1/audio/speech/upload',
                data=dict(
                    input=text,
                    exaggeration=0.6,
                    speed=0.5,
                    cfg_weight=0.5,
                    temperature=0.7,
                    response_format='wav'
                ),
                files={
                    'voice_file': (f'{voice}.wav', voice_bytes, 'audio/wav')
                },
                timeout=10000
            )
            sample_rate, audio_data = wav.read(io.BytesIO(resp.content))
            total_samples = audio_data.shape[0]

            chunk_size = 4000
            for prefix_len in range(0, total_samples, chunk_size):
                samples: np.ndarray = audio_data[prefix_len:prefix_len + chunk_size]

                yield samples  / 32768.0

    @lru_cache
    async def get_voices(self):
        return [os.path.splitext(voice)[0] for voice in os.listdir('/voices') if voice.endswith('.wav')]

    async def health_status(self):
        async with httpx.AsyncClient() as client:
            try:
                resp = await client.get(f'{self.base_url}/health', timeout=500)
                return resp.json()['status']
            except httpx.ConnectError:
                return 'unhealthy'
