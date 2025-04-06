import httpx

from providers.base import TextToSpeechProvider


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
                }
            )
            response.raise_for_status()
            return bytearray(response.content)


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
