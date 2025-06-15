import asyncio
import base64

import numpy as np

from models.sent_events import WsSendSpeechSamplesEvent
from models.session import Session
from providers import providers
from providers.base import TextToSpeechProvider
from utils.log import get_logger

logger = get_logger(__name__)


async def samples_sender_task(session: Session, outgoing_samples_queue: asyncio.Queue):
    try:
        while True:
            samples = await outgoing_samples_queue.get()
            if samples is None:
                logger.debug('Sent all the samples, exiting...')
                break

            async with session.speech_sending_lock:
                resampled = [0.0 for _ in range(len(samples) * 2)]
                for i in range(len(samples)):
                    resampled[i * 2] = samples[i]
                    resampled[i * 2 + 1] = samples[i]

                logger.debug(f'Sent {len(samples)} samples')

                await session.send_event(
                    WsSendSpeechSamplesEvent(
                        samples=base64.b64encode(np.array(resampled, dtype=np.float32).tobytes()).decode('ascii')
                    )
                )
                await asyncio.sleep(len(resampled) / 48000 * 2 / 3)
    except Exception as e:
        logger.error(e)
        logger.debug(str(e), exc_info=True, stack_info=True)


async def tts_task(session: Session, llm_response_queue: asyncio.Queue):
    tts_provider: TextToSpeechProvider = providers['tts'][session.chat.config.tts.provider]

    sender_task = None
    try:
        voice = session.chat.config.tts.voice

        outgoing_samples_queue = asyncio.Queue()
        sender_task = asyncio.create_task(samples_sender_task(session, outgoing_samples_queue))

        while True:
            sentence = await llm_response_queue.get()
            if sentence is None:
                await outgoing_samples_queue.put(None)
                break

            sentence = sentence.strip()
            if not sentence:
                continue

            async for samples in tts_provider.generate_audio_stream(sentence, voice):
                await outgoing_samples_queue.put(samples)

    except asyncio.CancelledError:
        if sender_task:
            sender_task.cancel()
        logger.debug('TTS task cancelled')
    except Exception as e:
        logger.error('Exception in TTS task', exc_info=True)
        logger.error(str(e))
