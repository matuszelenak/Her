import asyncio
import logging
import os.path
from uuid import uuid4

from providers import providers
from providers.base import TextToSpeechProvider
from utils.session import Session

logger = logging.getLogger(__name__)

async def tts_task(session: Session, llm_response_queue: asyncio.Queue):
    kokoro: TextToSpeechProvider = providers['tts']
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

            audio_bytearray = await kokoro.generate_audio(sentence, session.chat.config.tts.voice)

            _id = uuid4()
            if not os.path.exists(f'/tts_output/{session.chat.id}'):
                os.mkdir(f'/tts_output/{session.chat.id}')

            filename = f'/tts_output/{session.chat.id}/{_id}'
            with open(filename, 'wb') as f:
                f.write(bytes(audio_bytearray))

            await session.client_socket.send_json({
                'type': 'speech_id',
                'filename': f'{session.chat.id}/{_id}',
                'text': sentence
            })
    except asyncio.CancelledError:
        logger.info('TTS task cancelled')

    except Exception as e:
        logger.error('Exception in TTS receiver', exc_info=True)
        logger.error(str(e))
