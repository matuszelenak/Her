from typing import Literal

import httpx
import numpy as np
from pydantic import BaseModel

from providers.base import TextToSpeechProvider


class OrpheusConfig(BaseModel):
    provider: Literal['orpheus']
    voice: Literal["dan", "jess", "leah", "leo", "mia", "tara", "zac", "zoe"] = 'tara'


class OrpheusAudioProvider(TextToSpeechProvider):
    def __init__(self, base_url):
        self.base_url = base_url

    async def generate_audio(self, text: str, voice: str) -> bytearray:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f'{self.base_url}/v1/audio/speech',
                json={
                    "model": "orpheus",
                    "input": text,
                    "voice": voice,
                    "response_format": "wav",
                    "stream": False,
                },
                timeout=10000
            )
            response.raise_for_status()
            return bytearray(response.content)

    async def generate_audio_stream(self, text: str, voice: str):
        async with httpx.AsyncClient() as client:
            async with client.stream(
                'POST',
                f'{self.base_url}/v1/audio/speech/stream',
                json={
                    "model": "orpheus",
                    "input": text,
                    "voice": "leah",
                    "response_format": "wav",
                    "stream": True,
                    "include_header": False
                },
                timeout=30000
            ) as resp:
                chunk: bytes
                async for chunk in resp.aiter_bytes(chunk_size=4096):
                    yield np.frombuffer(chunk, dtype=np.int16) / 32768.0

    async def get_voices(self):
        async with httpx.AsyncClient() as client:
            resp = await client.get(f'{self.base_url}/v1/audio/voices')
            return sorted(resp.json()['voices'])

    async def health_status(self):
        async with httpx.AsyncClient() as client:
            try:
                resp = await client.get(f'{self.base_url}/health', timeout=500)
                return resp.json()['status']
            except httpx.ConnectError:
                return 'unhealthy'
