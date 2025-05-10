import asyncio
from pathlib import Path
from uuid import uuid4

from models.sent_events import WsSendSpeechEvent, WsSendAssistantSpeechStartEvent
from providers import providers
from providers.base import TextToSpeechProvider
from utils.log import get_logger
from utils.perf import ElapsedTime
from models.session import Session

logger = get_logger(__name__)


async def tts_task(session: Session, llm_response_queue: asyncio.Queue):
    tts_provider: TextToSpeechProvider = providers['tts'][session.chat.config.tts.provider]
    try:
        if session.chat.config.app.voice_output_enabled:
            await session.send_event(WsSendAssistantSpeechStartEvent())

        order = 0
        while True:
            sentence = await llm_response_queue.get()
            if sentence is None:
                break

            sentence = sentence.strip()
            if not sentence:
                continue

            if not session.chat.config.app.voice_output_enabled:
                continue

            with ElapsedTime(f'TTS for "{sentence}"'):
                audio_bytearray = await tts_provider.generate_audio(sentence, session.chat.config.tts.voice)

            folder_path = Path(f'/tts_output/{session.chat.id}/{len(session.chat)}')
            folder_path.mkdir(parents=True, exist_ok=True)
            file_path = folder_path / f'{order}_{uuid4()}.mp3'

            with open(file_path, 'wb') as f:
                f.write(bytes(audio_bytearray))

            await session.send_event(
                WsSendSpeechEvent(
                    filename=str(file_path.relative_to('/tts_output')),
                    order=order,
                    text=sentence
                )
            )

            order += 1
    except asyncio.CancelledError:
        logger.debug('TTS task cancelled')

    except Exception as e:
        logger.error('Exception in TTS task', exc_info=True)
        logger.error(str(e))
