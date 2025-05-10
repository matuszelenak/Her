from typing import Literal

import httpx
from pydantic import BaseModel

from providers.base import TextToSpeechProvider


class KokoroConfig(BaseModel):
    provider: Literal['kokoro']
    voice: Literal[
        "af_alloy",
        "af_aoede",
        "af_bella",
        "af_heart",
        "af_jadzia",
        "af_jessica",
        "af_kore",
        "af_nicole",
        "af_nova",
        "af_river",
        "af_sarah",
        "af_sky",
        "af_v0",
        "af_v0bella",
        "af_v0irulan",
        "af_v0nicole",
        "af_v0sarah",
        "af_v0sky",
        "am_adam",
        "am_echo",
        "am_eric",
        "am_fenrir",
        "am_liam",
        "am_michael",
        "am_onyx",
        "am_puck",
        "am_santa",
        "am_v0adam",
        "am_v0gurney",
        "am_v0michael",
        "bf_alice",
        "bf_emma",
        "bf_lily",
        "bf_v0emma",
        "bf_v0isabella",
        "bm_daniel",
        "bm_fable",
        "bm_george",
        "bm_lewis",
        "bm_v0george",
        "bm_v0lewis",
        "ef_dora",
        "em_alex",
        "em_santa",
        "ff_siwis",
        "hf_alpha",
        "hf_beta",
        "hm_omega",
        "hm_psi",
        "if_sara",
        "im_nicola",
        "jf_alpha",
        "jf_gongitsune",
        "jf_nezumi",
        "jf_tebukuro",
        "jm_kumo",
        "pf_dora",
        "pm_alex",
        "pm_santa",
        "zf_xiaobei",
        "zf_xiaoni",
        "zf_xiaoxiao",
        "zf_xiaoyi",
        "zm_yunjian",
        "zm_yunxi",
        "zm_yunxia",
        "zm_yunyang"
    ] = 'bf_emma'


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
