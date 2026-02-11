import asyncio
from typing import AsyncGenerator

import numpy as np
from pydantic import BaseModel

from src.models.base import TranscriptionSegment


class ProviderConfig(BaseModel):
    provider: str


class BaseProvider:
    async def health_status(self):
        raise NotImplementedError


class SpeechToTextProvider(BaseProvider):
    async def continuous_transcription(self, received_speech_queue: asyncio.Queue) -> AsyncGenerator[TranscriptionSegment, None]:
        raise NotImplementedError



class TextToSpeechProvider(BaseProvider):
    async def get_voices(self):
        raise NotImplementedError

    async def generate_audio(self, text: str, voice: str) -> bytearray:
        raise NotImplementedError

    async def generate_audio_stream(self, text: str, voice: str) -> AsyncGenerator[np.ndarray, None]:
        raise NotImplementedError
