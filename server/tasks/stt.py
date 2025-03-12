import asyncio

from providers import providers, WhisperProvider
from utils.log import get_logger
from utils.session import Session

logger = get_logger(__name__)


async def stt_task(session: Session, received_speech_queue: asyncio.Queue):
    stt_provider: WhisperProvider = providers['stt']

    prompt_words = []
    async for segment_message in stt_provider.continuous_transcription(received_speech_queue):
        await session.client_socket.send_json({
            'type': 'stt_output',
            'segment': segment_message
        })

        if segment_message.get('complete'):
            prompt_words.extend(segment_message['words'])

        if segment_message.get('final'):
            session.prompt = ' '.join(prompt_words)
            logger.debug(f'Setting prompt to {session.prompt}')

            prompt_words = []
