import uuid
from urllib.parse import urlencode

import httpx
import numpy as np
import scipy

from providers.base import TextToSpeechProvider


XTTS_OUTPUT_SAMPLING_RATE = 24000


class XTTSProvider(TextToSpeechProvider):
    def __init__(self, base_url):
        self.base_url = base_url

    async def generate_audio(self, text, voice) -> bytearray:
        all_samples = np.array([], np.float32)

        _id = str(uuid.uuid4())

        params = {
            'text': text,
            'voice': voice,
            'language': 'en',
            'output_file': 'whatever.wav'
        }

        async with httpx.AsyncClient() as client:
            async with client.stream(
                    'GET',
                    f'{self.base_url}/api/tts-generate-streaming?{urlencode(params)}'
            ) as resp:
                # buffer = []
                async for chunk in resp.aiter_bytes(XTTS_OUTPUT_SAMPLING_RATE):
                    samples = np.frombuffer(chunk, dtype=np.int16)
                    samples = samples / np.iinfo(np.int16).max
                    samples = scipy.signal.resample(
                        samples,
                        round(samples.shape[0] * (48000 / XTTS_OUTPUT_SAMPLING_RATE))
                    )
                    all_samples = np.concatenate((all_samples, samples), axis=0)

        filename = f'/tts_output/{_id}.wav'
        scipy.io.wavfile.write(filename, 48000, all_samples.astype(np.float32))

        return f'{_id}.wav'

    async def health_status(self):
        async with httpx.AsyncClient() as client:
            resp = await client.get(f'{self.base_url}/api/health', timeout=500)
            return sorted(resp.json()['voices'])


    async def get_voices(self):
        async with httpx.AsyncClient() as client:
            resp = await client.get(f'{self.base_url}/api/voices')
            return sorted(resp.json()['voices'])
