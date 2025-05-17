import asyncio
import base64
import logging
from datetime import datetime
from uuid import uuid4, UUID

import pydantic
import starlette
from fastapi import FastAPI, WebSocket, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.staticfiles import StaticFiles
import scipy.io.wavfile as wav

from db.models import Chat
from db.session import get_db
from endpoints.audio import audio_router
from endpoints.chat import chat_router
from models.configuration import get_previous_or_default_config
from models.received_events import WsReceiveSamplesEvent, WsReceiveEvent, WsReceiveSpeechEndEvent, \
    WsReceiveTextPrompt, WsReceiveSpeechPromptEvent, WsReceiveAgentSpeechEnd, WsReceiveConfigChange, \
    WsReceiveFlowControl
from models.sent_events import WsManualPromptEvent, WsSendConfigurationEvent, WsSendSpeechSamplesEvent
from models.session import Session
from providers import providers
from tasks.coordination import trigger_agent_response
from tasks.stt import stt_task
from utils.log import get_logger
from utils.sound import resample_chunk
from utils.validation import should_agent_respond

app = FastAPI()

logger = get_logger(__name__)

app.include_router(chat_router)
app.include_router(audio_router)

app.mount('/audio', StaticFiles(directory='/tts_output'), name='tts-output')


async def samples_sender_task(socket, lock):
    try:
        sample_rate, audio_data = wav.read('utils/please_streamed.wav')
        total_samples = audio_data.shape[0]

        for prefix_len in range(0, total_samples, 8192):
            samples = audio_data[prefix_len:prefix_len + 8192] / 32768.0
            if samples is None:
                logger.debug('Sent all the samples, exiting...')
                break

            async with lock:
                resampled = resample_chunk(samples, 24000, 48000)
                await socket.send_json(WsSendSpeechSamplesEvent(
                    samples=base64.b64encode(resampled.tobytes()).decode('ascii')
                ).model_dump())
                await asyncio.sleep(1 / 5)

    except Exception as e:
        logger.error(e)
        logger.debug(str(e), exc_info=True, stack_info=True)


@app.websocket('/ws/audio')
async def audio_endpoint(websocket: WebSocket):
    await websocket.accept()

    lock = asyncio.Lock()

    sender_task = asyncio.create_task(samples_sender_task(websocket, lock))

    try:
        while True:
            event_data = await websocket.receive_json()

            try:
                event = WsReceiveEvent.model_validate({'event': event_data}).event
            except pydantic.ValidationError:
                logger.debug(f'Received invalid socket event: {event_data}')
                continue

            if isinstance(event, WsReceiveFlowControl):
                if event.command == 'pause_sending':
                    logger.debug('Pausing sending')
                    await lock.acquire()
                elif event.command == 'resume_sending':
                    logger.debug('Resuming sending')
                    lock.release()
    except starlette.websockets.WebSocketDisconnect:
        pass
    finally:
        sender_task.cancel()


@app.websocket("/ws/health")
async def health_endpoint(websocket: WebSocket):
    await websocket.accept()

    try:
        while True:
            await websocket.receive_json()
            await websocket.send_json({
                provider_name: await provider.health_status()
                for provider_type, providers_of_type in providers.items()
                for provider_name, provider in providers_of_type.items()
            })
    except starlette.websockets.WebSocketDisconnect:
        pass


@app.websocket("/ws/chat/{chat_id}")
async def chat_endpoint(chat_id: str, websocket: WebSocket, db: AsyncSession = Depends(get_db)):
    await websocket.accept()

    logger.debug(f"Client connected to chat {chat_id}")

    session_id = str(uuid4())

    query = select(Chat).filter(Chat.id == chat_id)
    results = await db.execute(query)
    chat = results.scalar()

    if chat is None:
        logger.debug(f"New chat initiated")
        config = await get_previous_or_default_config(db)
        chat = Chat(config_db=config)
        chat._id = UUID(chat_id)

    session = Session(
        session_id,
        db,
        chat
    )

    session.client_socket = websocket

    await session.send_event(
        WsSendConfigurationEvent(configuration=session.chat.config)
    )

    try:
        received_speech_queue = asyncio.Queue()

        while True:
            event_data = await websocket.receive_json()

            try:
                event = WsReceiveEvent.model_validate({'event': event_data}).event
            except pydantic.ValidationError:
                logger.debug(f'Received invalid socket event: {event_data}')
                continue

            if isinstance(event, WsReceiveSamplesEvent):
                if session.stt_task is None:
                    session.stt_task = asyncio.create_task(stt_task(session, received_speech_queue))
                await received_speech_queue.put(event.data)

            elif isinstance(event, WsReceiveSpeechEndEvent):
                await received_speech_queue.put(None)

            elif isinstance(event, WsReceiveTextPrompt):
                logging.debug('Received manual prompt')
                session.prompt = f'{session.prompt or ""}{event.prompt}'

                await session.send_event(
                    WsManualPromptEvent(
                        text=event.prompt
                    )
                )

                trigger_agent_response(session)

            elif isinstance(event, WsReceiveSpeechPromptEvent):
                if session.prompt:
                    warrants_response = await should_agent_respond(session)

                    if warrants_response:
                        trigger_agent_response(session)
                    else:
                        session.prompt = None
                        # await session.send_event({
                        #     'type': 'user_speech_transcription_invalidation'
                        # })

            elif isinstance(event, WsReceiveAgentSpeechEnd):
                session.last_interaction = datetime.now()

            elif isinstance(event, WsReceiveConfigChange):
                await session.set_config_from_event(event.path, event.value)
                await session.send_event(
                    WsSendConfigurationEvent(configuration=session.chat.config)
                )

            elif isinstance(event, WsReceiveFlowControl):
                if event.command == 'pause_sending':
                    logger.debug('Pausing sending')
                    await session.speech_sending_lock.acquire()
                elif event.command == 'resume_sending':
                    logger.debug('Resuming sending')
                    session.speech_sending_lock.release()


    except starlette.websockets.WebSocketDisconnect:
        pass

    except Exception as e:
        logger.error('Exception in main', exc_info=True)
        logger.error(str(e))

    finally:
        logger.debug(f'Terminating client')
        session.terminate()
