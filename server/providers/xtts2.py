import logging
import uuid
from urllib.parse import urlencode

import httpx
import scipy
import numpy as np

from utils.constants import XTTS2_API_URL, XTTS_OUTPUT_SAMPLING_RATE

logger = logging.getLogger(__name__)


async def generate_audio(session, text):
    all_samples = np.array([], np.float32)

    _id = str(uuid.uuid4())

    params = {
        'text': text,
        'voice': session.chat.config.xtts.voice,
        'language': session.chat.config.xtts.language,
        'output_file': 'whatever.wav'
    }

    async with httpx.AsyncClient() as client:
        async with client.stream(
                'GET',
                f'{XTTS2_API_URL}/api/tts-generate-streaming?{urlencode(params)}'
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
