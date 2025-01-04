import asyncio
import base64
import logging
from datetime import datetime
from urllib.parse import urlencode

import httpx
import numpy as np
import scipy

from utils.constants import XTTS2_API_URL, XTTS_OUTPUT_SAMPLING_RATE
from utils.health import xtts_status
from utils.session import Session

logger = logging.getLogger(__name__)

async def tts_task(session: Session, llm_response_queue: asyncio.Queue):
    try:
        while True:
            logger.info('Awaiting TTS queue')
            sentence = await llm_response_queue.get()
            if sentence is None:
                break

            sentence = sentence.strip()
            if not sentence:
                continue

            if not xtts_status():
                continue

            params = {
                'text': sentence,
                'voice': session.chat.config.xtts.voice,
                'language': session.chat.config.xtts.language,
                'output_file': 'whatever.wav'
            }
            logger.info(f'Submitting for TTS {sentence}')
            async with httpx.AsyncClient() as client:
                async with client.stream(
                        'GET',
                        f'{XTTS2_API_URL}/api/tts-generate-streaming?{urlencode(params)}'
                ) as resp:
                    buffer = []
                    async for chunk in resp.aiter_bytes(XTTS_OUTPUT_SAMPLING_RATE):
                        samples = np.frombuffer(chunk, dtype=np.int16)
                        samples = samples / np.iinfo(np.int16).max
                        samples = scipy.signal.resample(
                            samples,
                            round(samples.shape[0] * (48000 / XTTS_OUTPUT_SAMPLING_RATE))
                        )

                        for sample in samples:
                            if len(buffer) < 8192:
                                buffer.append(sample)
                            else:
                                buffer = np.array(buffer).astype(np.float32).tobytes()
                                b64_buffer = base64.b64encode(buffer).decode('ascii')
                                # _id = str(uuid.uuid4())

                                while True:
                                    if session.free_samples > 8192 * 8:
                                        await session.client_socket.send_json({
                                            'type': 'speech',
                                            'samples': b64_buffer
                                        })
                                        session.last_interaction = datetime.now()
                                        await asyncio.sleep(0.13)
                                        break

                                    await asyncio.sleep(0.15)

                                buffer = []
    except asyncio.CancelledError:
        logger.info('TTS task cancelled')

    except Exception as e:
        logger.error('Exception in TTS receiver', exc_info=True)
        logger.error(str(e))
