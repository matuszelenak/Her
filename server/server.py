import asyncio
import logging
from datetime import datetime
from uuid import uuid4, UUID

import logfire
import pydantic
import starlette
from fastapi import FastAPI, WebSocket, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.middleware.cors import CORSMiddleware
from starlette.staticfiles import StaticFiles

from db.models import Chat
from db.session import get_db
from endpoints.audio import audio_router
from endpoints.chat import chat_router
from models.configuration import load_config
from models.received_events import WsReceiveSamplesEvent, WsReceiveEvent, WsReceiveSpeechEndEvent, \
    WsReceiveTextPrompt, WsReceiveSpeechPromptEvent, WsReceiveAgentSpeechEnd, WsReceiveConfigChange, \
    WsReceiveFlowControl
from models.sent_events import WsManualPromptEvent, WsSendConfigurationEvent
from models.session import Session
from providers import providers
from tasks.coordination import trigger_agent_response
from tasks.stt import stt_task
from utils.validation import should_agent_respond


app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

logfire.configure(send_to_logfire="if-token-present")
logfire.instrument_fastapi(app)

app.include_router(chat_router)
app.include_router(audio_router)

app.mount('/audio', StaticFiles(directory='/tts_output'), name='tts-output')


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

    logfire.info(f"Client connected to chat {chat_id}")

    session_id = str(uuid4())

    query = select(Chat).filter(Chat.id == chat_id)
    results = await db.execute(query)
    chat = results.scalar()

    if chat is None:
        logfire.info(f"New chat initiated")
        chat = Chat()
        chat._id = UUID(chat_id)

    config = await load_config()
    session = Session(
        session_id,
        db,
        chat,
        config
    )

    session.client_socket = websocket

    await session.send_event(
        WsSendConfigurationEvent(configuration=session.config)
    )

    try:
        received_speech_queue = asyncio.Queue()

        while True:
            event_data = await websocket.receive_json()

            try:
                event = WsReceiveEvent.model_validate({'event': event_data}).event

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
                    await session.set_config_field_from_event(event.path, event.value)
                    await session.send_event(
                        WsSendConfigurationEvent(configuration=session.config)
                    )

                elif isinstance(event, WsReceiveFlowControl):
                    if event.command == 'pause_sending':
                        logfire.debug('Pausing sending')
                        await session.speech_sending_lock.acquire()
                    elif event.command == 'resume_sending':
                        logfire.debug('Resuming sending')
                        session.speech_sending_lock.release()

            except pydantic.ValidationError:
                logfire.warning(f'Received invalid socket event: {event_data}')
                continue

    except starlette.websockets.WebSocketDisconnect:
        pass

    except Exception as e:
        logfire.error(f'Exception in main {e}', _exc_info=True)

    finally:
        logfire.info(f'Terminating client')
        session.terminate()
