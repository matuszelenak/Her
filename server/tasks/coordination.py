import asyncio
import datetime
import logging

from tasks.llm import llm_query_task
from tasks.stt import stt_sender
from utils.session import Session

logger = logging.getLogger(__name__)


async def coordination_task(session: Session, received_speech_queue: asyncio.Queue):
    llm_task = None
    while True:
        if session.prompt:
            if session.tts_task is not None and not session.tts_task.done():
                session.tts_task.cancel()
                session.tts_task = None

            if llm_task is not None and not llm_task.done():
                llm_task.cancel()
                llm_task = None

            prompt = session.prompt
            if (session.user_speaking_status[0] == False
                    and session.user_speaking_status[1] < datetime.datetime.now() - datetime.timedelta(
                        milliseconds=session.config.app.speech_submit_delay_ms
                    )
            ):
                logger.info(f'Accepted prompt {prompt}')

                llm_task = asyncio.create_task(llm_query_task(session, prompt))
                session.prompt = None
                session.stt_task.cancel()
                session.stt_task = asyncio.create_task(stt_sender(session, received_speech_queue))

        await asyncio.sleep(0.1)
