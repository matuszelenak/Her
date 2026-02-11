import asyncio
from asyncio import CancelledError

import logfire

from src.models.base import TranscriptionSegment
from src.models.sent_events import WsSendTranscriptionEvent
from src.models.session import Session
from src.providers import providers, SpeechToTextProvider
from src.tasks.coordination import trigger_agent_response
from src.utils.validation import should_agent_respond


async def stt_task(session: Session, received_speech_queue: asyncio.Queue):
    try:
        stt_provider: SpeechToTextProvider = providers['stt'][session.config.stt.provider]

        transcribed_segment: TranscriptionSegment
        async for transcribed_segment in stt_provider.continuous_transcription(received_speech_queue):
            if transcribed_segment.text == '':
                continue

            await session.send_event(WsSendTranscriptionEvent(
                text=transcribed_segment.text,
                is_final=transcribed_segment.is_final
            ))

            if session.llm_task and not session.llm_task.cancelled():
                session.llm_task.cancel()
            if session.tts_task and not session.tts_task.cancelled():
                session.tts_task.cancel()

            if transcribed_segment.is_final:
                logfire.info(f'Setting prompt to {transcribed_segment.text}')
                session.prompt = transcribed_segment.text

                warrants_response = await should_agent_respond(session)

                if warrants_response:
                    trigger_agent_response(session)
                else:
                    session.prompt = None
                    # await session.send_event({
                    #     'type': 'user_speech_transcription_invalidation'
                    # })


    except CancelledError:
        logfire.info('STT task cancelled')

    except Exception as e:
        logfire.error(f'Exception in STT task: {e}', _exc_info=True)
