import asyncio
from asyncio import CancelledError

from models.sent_events import WsSendTranscriptionEvent
from providers import providers, WhisperProvider
from utils.log import get_logger
from utils.session import Session

logger = get_logger(__name__)


async def stt_task(session: Session, received_speech_queue: asyncio.Queue):
    try:
        stt_provider: WhisperProvider = providers['stt']

        prompt_words = []
        async for transcribed_segment in stt_provider.continuous_transcription(received_speech_queue):
            await session.send_event(WsSendTranscriptionEvent(segment=transcribed_segment))

            if transcribed_segment.complete:
                prompt_words.extend(transcribed_segment.words)

            if transcribed_segment.final:
                session.prompt = ' '.join(prompt_words)
                logger.debug(f'Setting prompt to {session.prompt}')

                prompt_words = []

    except CancelledError:
        logger.debug('STT task cancelled')

    except Exception as e:
        logger.error('Exception in STT task', exc_info=True)
