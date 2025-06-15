import asyncio
from asyncio import CancelledError

import logfire

from models.sent_events import WsSendTranscriptionEvent
from models.session import Session
from providers import providers, WhisperProvider


async def stt_task(session: Session, received_speech_queue: asyncio.Queue):
    try:
        stt_provider: WhisperProvider = providers['stt']['whisper']

        prompt_words = []
        async for transcribed_segment in stt_provider.continuous_transcription(received_speech_queue):
            await session.send_event(WsSendTranscriptionEvent(segment=transcribed_segment))

            if transcribed_segment.complete:
                prompt_words.extend(transcribed_segment.words)

            if transcribed_segment.final:
                session.prompt = ' '.join(prompt_words)
                logfire.info(f'Setting prompt to {session.prompt}')

                prompt_words = []

    except CancelledError:
        logfire.info('STT task cancelled')

    except Exception as e:
        logfire.error(f'Exception in STT task: {e}', _exc_info=True)
