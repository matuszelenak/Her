import httpx

from providers.base import TextToSpeechProvider


class KokoroAudioProvider(TextToSpeechProvider):
    def __init__(self, base_url):
        self.base_url = base_url

    async def generate_audio(self, text: str, voice: str) -> bytearray:
        content = bytearray()

        async with httpx.AsyncClient() as client:
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
                chunk: bytes
                async for chunk in resp.aiter_bytes(chunk_size=512):
                    content.extend(chunk)

        return content


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
