import asyncio
import logging
from urllib.parse import urlencode

import httpx
import numpy as np
import scipy

from utils.constants import XTTS2_API_URL, XTTS_OUTPUT_SAMPLING_RATE
from utils.session import Session

logger = logging.getLogger(__name__)

async def tts_receiver(session: Session):
    while True:
        logger.warning('Awaiting TTS queue')
        sentence = await session.response_tokens_queue.get()
        sentence = sentence.strip()
        if not sentence:
            continue
        params = {
            'text': sentence,
            'voice': 'aloy.wav',
            'language': 'en',
            'output_file': 'whatever.wav'
        }
        logger.warning(f'Submitting for TTS {sentence}')
        async with httpx.AsyncClient() as client:
            async with client.stream(
                    'GET',
                    f'{XTTS2_API_URL}/api/tts-generate-streaming?{urlencode(params)}'
            ) as resp:
                async for chunk in resp.aiter_bytes(XTTS_OUTPUT_SAMPLING_RATE):
                    samples = np.frombuffer(chunk, dtype=np.int16)
                    samples = samples / np.iinfo(np.int16).max
                    samples = scipy.signal.resample(
                        samples,
                        round(samples.shape[0] * (48000 / XTTS_OUTPUT_SAMPLING_RATE))
                    )

                    while session.response_speech_queue.qsize() > 5:
                        await asyncio.sleep(0.5)

                    await session.response_speech_queue.put(samples.tolist())
