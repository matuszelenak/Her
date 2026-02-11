import asyncio
import logging
import typing
from datetime import datetime
from uuid import uuid4, UUID

import logfire
import pydantic
import starlette
from dotenv import load_dotenv
from fastapi import FastAPI, WebSocket, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.middleware.cors import CORSMiddleware
from starlette.staticfiles import StaticFiles

from src.db.models import Chat
from src.db.session import get_db
from src.endpoints.audio import audio_router
from src.endpoints.chat import chat_router
from src.models.configuration import load_config
from src.models.received_events import WsReceiveSamplesEvent, WsReceiveEvent, WsReceiveSpeechPauseEvent, \
    WsReceiveTextPrompt, WsReceiveSpeechEndEvent, WsReceiveAgentSpeechEnd, WsReceiveConfigChange, \
    WsReceiveFlowControl
from src.models.sent_events import WsManualPromptEvent, WsSendConfigurationEvent
from src.models.session import Session
from src.providers import providers
from src.tasks.coordination import trigger_agent_response
from src.tasks.stt import stt_task
from src.utils.validation import should_agent_respond


load_dotenv()


app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

logfire.configure(send_to_logfire="if-token-present")

app.include_router(chat_router)
app.include_router(audio_router)

class EndpointFilter(logging.Filter):
    def __init__(self, path: str,*args: typing.Any, **kwargs: typing.Any):
        super().__init__(*args, **kwargs)
        self._path = path

    def filter(self, record: logging.LogRecord) -> bool:
        return record.getMessage().find(self._path) == -1


uvicorn_logger = logging.getLogger("uvicorn.access")
uvicorn_logger.addFilter(EndpointFilter(path="/health"))
logfire.instrument_fastapi(app, excluded_urls=['health'])

app.mount('/audio', StaticFiles(directory='/tts_output'), name='tts-output')


@app.get('/health')
async def health():
    return {}


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

                elif isinstance(event, WsReceiveSpeechPauseEvent):
                    await received_speech_queue.put('')

                elif isinstance(event, WsReceiveTextPrompt):
                    logging.debug('Received manual prompt')
                    session.prompt = f'{session.prompt or ""}{event.prompt}'

                    await session.send_event(
                        WsManualPromptEvent(
                            text=event.prompt
                        )
                    )

                    trigger_agent_response(session)

                elif isinstance(event, WsReceiveSpeechEndEvent):
                    print('Speech end received')
                    await received_speech_queue.put(None)

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
