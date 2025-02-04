import uuid

import httpx

from providers.base import TextToSpeechProvider


class KokoroAudioProvider(TextToSpeechProvider):
    def __init__(self, base_url):
        self.base_url = base_url

    async def generate_audio(self, text: str, voice: str):
        _id = str(uuid.uuid4())
        filename = f'/tts_output/{_id}.mp3'

        async with httpx.AsyncClient() as client:
            with open(filename, 'wb') as f:
                async with client.stream(
                        'POST',
                        f'{self.base_url}/v1/audio/speech',
                        json={
                            "model": "kokoro",
                            "input": text,
                            "voice": voice,
                            "response_format": "mp3",
                            "stream": True,
                        }
                ) as resp:
                    async for chunk in resp.aiter_bytes(chunk_size=512):
                        f.write(chunk)

        return f'{_id}.mp3'


    async def get_voices(self):
        async with httpx.AsyncClient() as client:
            resp = await client.get(f'{self.base_url}/v1/audio/voices')
            return sorted(resp.json()['voices'])


    async def health_status(self):
        async with httpx.AsyncClient() as client:
            resp = await client.get(f'{self.base_url}/health', timeout=500)
            return resp.json()['status']
