import asyncio
import base64
import logging
from urllib.parse import urlencode

import httpx
import numpy as np
import scipy

from utils.constants import XTTS2_API_URL, XTTS_OUTPUT_SAMPLING_RATE
from utils.queue import empty_queue
from utils.session import Session

logger = logging.getLogger(__name__)

async def tts_receiver(session: Session):
    sender_task = asyncio.create_task(speech_sender(session))
    try:
        while True:
            logger.warning('Awaiting TTS queue')
            sentence = await session.response_tokens_queue.get()
            sentence = sentence.strip()
            if not sentence:
                continue
            params = {
                'text': sentence,
                'voice': session.config.xtts.voice,
                'language': session.config.xtts.language,
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
    except asyncio.CancelledError:
        sender_task.cancel()

    except Exception as e:
        logger.error('Exception in TTS receiver')
        logger.error(str(e))


async def speech_sender(session: Session):
    _id = 0
    try:
        buffer = []
        while True:
            samples = await session.response_speech_queue.get()

            if session.user_speaking_status[0]:
                logger.warning('User started speaking')
                session.tts_task.cancel()

                await empty_queue(session.response_speech_queue)
                await empty_queue(session.response_tokens_queue)

                session.tts_task = asyncio.create_task(tts_receiver(session))
                continue

            for sample in samples:
                if len(buffer) < 8192:
                    buffer.append(sample)
                else:
                    buffer = np.array(buffer).astype(np.float32).tobytes()
                    b64_buffer = base64.b64encode(buffer).decode('ascii')
                    # _id = str(uuid.uuid4())
                    _id += 1

                    while True:
                        if session.free_samples > 8192 * 8:
                            await session.client_socket.send_json({
                                'type': 'speech',
                                'samples': b64_buffer,
                                'id': str(_id)
                            })
                            await asyncio.sleep(0.13)
                            break

                        await asyncio.sleep(0.15)

                    buffer = []
    except asyncio.CancelledError:
        logger.warning('Speech sender cancelled')
    except Exception as e:
        logger.error('Exception in Speech sender')
        logger.error(str(e))
