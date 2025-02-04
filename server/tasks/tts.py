import asyncio
import logging

from providers import providers
from utils.session import Session

logger = logging.getLogger(__name__)

async def tts_task(session: Session, llm_response_queue: asyncio.Queue):
    kokoro = providers['tts']
    try:
        while True:
            logger.info('Awaiting TTS queue')
            sentence = await llm_response_queue.get()
            if sentence is None:
                break

            sentence = sentence.strip()
            if not sentence:
                continue

            if not session.speech_enabled:
                continue


            logger.warning(f'Submitting for TTS {sentence}')

            audio_filename = await kokoro.generate_audio(sentence, session.chat.config.tts.voice)

            await session.client_socket.send_json({
                'type': 'speech_id',
                'filename': audio_filename
            })
    except asyncio.CancelledError:
        logger.info('TTS task cancelled')

    except Exception as e:
        logger.error('Exception in TTS receiver', exc_info=True)
        logger.error(str(e))
