import asyncio
from datetime import datetime
from uuid import uuid4, UUID

import starlette
from fastapi import FastAPI, WebSocket, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.staticfiles import StaticFiles

from db.models import Chat
from db.session import get_db
from endpoints.audio import audio_router
from endpoints.chat import chat_router
from models.received_events import WsReceiveSamplesEvent, WsReceiveEvent, WsReceiveSpeechEndEvent, \
    WsReceiveTextPrompt, WsReceiveSpeechPromptEvent, WsReceiveAgentSpeechEnd
from models.sent_events import WsManualPromptEvent
from providers import providers
from tasks.coordination import trigger_agent_response
from tasks.stt import stt_task
from utils.configuration import get_previous_or_default_config
from utils.log import get_logger
from utils.session import Session
from utils.validation import should_agent_respond

app = FastAPI()

logger = get_logger(__name__)

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
                provider_name: await p.health_status() for provider_name, p in providers.items()
            })
    except starlette.websockets.WebSocketDisconnect:
        pass


@app.websocket("/ws/chat/{chat_id}")
async def chat_endpoint(chat_id: str, websocket: WebSocket, db: AsyncSession = Depends(get_db)):
    await websocket.accept()

    logger.debug(f"New client connected")

    session_id = str(uuid4())
    config = await get_previous_or_default_config(db)

    query = select(Chat).filter(Chat.id == chat_id)
    results = await db.execute(query)
    chat = results.scalar()

    if chat is None:
        chat = Chat(config_db=config)
        chat._id = UUID(chat_id)

    session = Session(
        session_id,
        db,
        chat
    )

    session.client_socket = websocket

    try:
        received_speech_queue = asyncio.Queue()

        while True:
            event_data = await websocket.receive_json()
            event = WsReceiveEvent.model_validate({'event': event_data}).event

            if isinstance(event, WsReceiveSamplesEvent):
                session.user_speaking_status = (True, datetime.now())
                if session.stt_task is None:
                    session.stt_task = asyncio.create_task(stt_task(session, received_speech_queue))
                await received_speech_queue.put(event.data)

            elif isinstance(event, WsReceiveSpeechEndEvent):
                logger.debug('Speak end')
                session.user_speaking_status = (False, datetime.now())
                await received_speech_queue.put(None)

            elif isinstance(event, WsReceiveTextPrompt):
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
                        pass
                        # await session.send_event({
                        #     'type': 'user_speech_transcription_invalidation'
                        # })

            elif isinstance(event, WsReceiveAgentSpeechEnd):
                session.last_interaction = datetime.now()

            # elif data['event'] == 'speech_toggle':
            #     session.speech_enabled = data['value']
            #     logger.debug(f'Speech {session.speech_enabled}')


    except starlette.websockets.WebSocketDisconnect:
        pass

    except Exception as e:
        logger.error('Exception in main', exc_info=True)
        logger.error(str(e))

    finally:
        logger.debug(f'Terminating client')
        session.terminate()
