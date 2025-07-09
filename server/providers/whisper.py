import asyncio
import json
from typing import AsyncGenerator

import httpx
import websockets

from models.base import TranscriptionSegment
from providers.base import BaseProvider


class WhisperProvider(BaseProvider):
    def __init__(self, base_url):
        self.base_url = base_url

    async def health_status(self):
        try:
            async with httpx.AsyncClient() as client:
                resp = await client.get(f'http://{self.base_url}/health', timeout=500)
                return resp.json()['status']
        except httpx.ConnectError:
            return 'unhealthy'

    @staticmethod
    async def sender_task(stt_socket, received_speech_queue):
        while True:
            samples = await received_speech_queue.get()
            if samples is None:
                await stt_socket.send(json.dumps({
                    'commit': True
                }))
            else:
                await stt_socket.send(json.dumps({
                    'samples': samples
                }))


    async def continuous_transcription(self, received_speech_queue: asyncio.Queue) -> AsyncGenerator[TranscriptionSegment, None]:
        async for stt_socket in websockets.connect(f'ws://{self.base_url}/transcribe'):
            sender = asyncio.create_task(WhisperProvider.sender_task(stt_socket, received_speech_queue))

            try:
                async for message in stt_socket:
                    yield TranscriptionSegment.model_validate_json(message)

            except websockets.exceptions.ConnectionClosedError:
                sender.cancel()
