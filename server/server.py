import asyncio
import json
import logging
from datetime import datetime
from uuid import uuid4

import starlette
from fastapi import FastAPI, WebSocket, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from db.models import Chat
from db.session import get_db
from endpoints.audio import audio_router
from endpoints.chat import chat_router
from endpoints.settings import settings_router
from providers import providers
from tasks.coordination import trigger_llm
from tasks.stt import stt_task
from utils.configuration import get_previous_or_default_config
from utils.session import Session
from utils.validation import should_agent_respond


app = FastAPI()

logger = logging.getLogger(__name__)
logger.setLevel('INFO')

app.include_router(chat_router)
app.include_router(settings_router)
app.include_router(audio_router)


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


@app.websocket("/ws/chat")
async def chat_endpoint(websocket: WebSocket, db: AsyncSession = Depends(get_db)):
    await websocket.accept()

    logger.warning(f"New client connected")

    session_id = str(uuid4())
    config = await get_previous_or_default_config(db)
    chat = Chat(config_db=config)
    session = Session(
        session_id,
        db,
        chat
    )

    session.client_socket = websocket

    try:
        received_speech_queue = asyncio.Queue()

        while True:
            data = await websocket.receive_json()
            # logger.warning(f'Received ws {data}')
            if data['event'] == 'load_chat':
                if data["chat_id"] is not None:
                    await session.load_chat(data["chat_id"])
                else:
                    session.chat = Chat(config_db=config)

                await websocket.send_json({
                    'type': 'config',
                    'config': json.loads(session.chat.config.model_dump_json())
                })

            elif data['event'] == 'samples':
                session.user_speaking_status = (True, datetime.now())
                if session.stt_task is None:
                    session.stt_task = asyncio.create_task(stt_task(session, received_speech_queue))
                await received_speech_queue.put(data['data'])

            elif data['event'] == 'speech_end':
                logger.info('Speak end')
                session.user_speaking_status = (False, datetime.now())
                await received_speech_queue.put(None)

            elif data['event'] == 'speech_prompt_end':
                if session.prompt:
                    warrants_response = await should_agent_respond(session)

                    if warrants_response:
                        trigger_llm(session)
                    else:
                        await session.client_socket.send_json({
                            'type': 'stt_output_invalidation'
                        })

            elif data['event'] == 'text_prompt':
                session.prompt = f'{session.prompt or ""}{data["prompt"]}'

                await session.client_socket.send_json({
                    'type': 'manual_prompt',
                    'text': data['prompt']
                })

                trigger_llm(session)

            elif data['event'] == 'speech_toggle':
                session.speech_enabled = data['value']
                logger.warning(f'Speech {session.speech_enabled}')

            elif data['event'] == 'config':
                await session.set_config_from_event(data['field'], data['value'])

            elif data['event'] == 'finished_speaking':
                session.last_interaction = datetime.now()

    except starlette.websockets.WebSocketDisconnect:
        pass

    except Exception as e:
        logger.error('Exception in main', exc_info=True)
        logger.error(str(e))

    finally:
        logger.warning(f'Terminating client')
        session.terminate()
