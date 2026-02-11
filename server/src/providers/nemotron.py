import asyncio
import json
from typing import AsyncGenerator

import httpx
import logfire
import websockets

from src.models.base import TranscriptionSegment
from src.providers.base import SpeechToTextProvider


class NemotronProvider(SpeechToTextProvider):
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
    async def sender_task(stt_socket, received_speech_queue: asyncio.Queue[str]):
        while True:
            b64_samples = await received_speech_queue.get()

            if b64_samples == '':
                # Pause
                await stt_socket.send(json.dumps({
                    'pause': True
                }))
            elif b64_samples is None:
                await stt_socket.send(json.dumps({
                    'stop': True
                }))
            else:
                await stt_socket.send(json.dumps({
                    'samples': b64_samples
                }))


    async def continuous_transcription(self, received_speech_queue: asyncio.Queue[str]) -> AsyncGenerator[TranscriptionSegment, None]:
        sender = None
        try:
            async for stt_socket in websockets.connect(f'ws://{self.base_url}/transcribe'):
                sender = asyncio.create_task(NemotronProvider.sender_task(stt_socket, received_speech_queue))

                try:
                    async for message in stt_socket:
                        msg_json = json.loads(message)
                        print(msg_json)
                        if msg_json['type'] == 'transcript':
                            yield TranscriptionSegment(
                                text=msg_json['text'],
                                is_final=msg_json.get('finalize', False)
                            )

                except websockets.exceptions.ConnectionClosedError:
                    sender.cancel()
        except asyncio.CancelledError:
            if sender is not None:
                sender.cancel()
        except Exception as e:
            logfire.error(str(e), _exc_info=True)
