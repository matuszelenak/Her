import asyncio
import json
import logging
from datetime import datetime
from uuid import uuid4

import httpx
import starlette
from fastapi import FastAPI, WebSocket, Depends
from fastapi.encoders import jsonable_encoder
from ollama import AsyncClient
from sqlalchemy import select, desc, delete
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import load_only

from db.models import Chat
from db.session import get_db
from tasks.coordination import trigger_llm
from tasks.stt import stt_sender
from utils.configuration import get_previous_or_default_config
from utils.constants import OLLAMA_API_URL, XTTS2_API_URL
from utils.health import ollama_status, xtts_status, whisper_status
from utils.session import Session
from utils.validation import should_agent_respond

app = FastAPI()

logger = logging.getLogger(__name__)
logger.setLevel('INFO')


@app.get('/models')
async def get_models():
    models = (await AsyncClient(OLLAMA_API_URL).list())['models']

    return sorted(models, key=lambda m: m['model'])


@app.get('/xtts')
async def get_xtts():
    res = {}
    async with httpx.AsyncClient() as client:
        resp = await client.get(f'{XTTS2_API_URL}/api/voices')
        res['voices'] = sorted(resp.json()['voices'])

        return res


@app.get('/chats')
async def get_chats(db: AsyncSession = Depends(get_db)):
    query = select(Chat).options(load_only(Chat.id, Chat.started_at, Chat.header)).order_by(desc('started_at'))

    result = await db.execute(query)
    result = result.scalars()

    return jsonable_encoder(list(result))


@app.get('/chat/{chat_id}')
async def get_chat(chat_id: str, db: AsyncSession = Depends(get_db)):
    query = select(Chat).filter(Chat.id == chat_id)
    result = await db.execute(query)
    return jsonable_encoder(result.scalar())


@app.delete('/chat/{chat_id}')
async def get_chats(chat_id: str, db: AsyncSession = Depends(get_db)):
    query = delete(Chat).filter(Chat.id == chat_id)
    await db.execute(query)
    await db.commit()
    return {'id': chat_id}


@app.get('/tools')
async def get_tools():
    return ['get_ip_address_def', 'get_current_moon_phase']


@app.websocket("/ws/health")
async def health_endpoint(websocket: WebSocket):
    await websocket.accept()

    while True:
        await websocket.receive_json()
        await websocket.send_json({
            'ollama': ollama_status(),
            'xtts': xtts_status(),
            'whisper': whisper_status()
        })


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

            if data['event'] == 'free_space':
                session.free_samples = data["value"]

            elif data['event'] == 'resp_wait':
                logger.warning('Throttling!')

            # elif data['event'] == 'resp_ok':
            #     session.last_accepted_speech_id = data['id']

            elif data['event'] == 'samples':
                session.user_speaking_status = (True, datetime.now())
                if session.stt_task is None:
                    session.stt_task = asyncio.create_task(stt_sender(session, received_speech_queue))
                await received_speech_queue.put(data['data'])

            elif data['event'] == 'speech_end':
                logger.info('Speak end')
                session.user_speaking_status = (False, datetime.now())

                if session.stt_task is not None:
                    session.stt_task.cancel()
                    session.stt_task = None

            elif data['event'] == 'speech_prompt_end':
                if session.prompt:
                    warrants_response = await should_agent_respond(session)

                    if warrants_response:
                        trigger_llm(session, received_speech_queue)
                    else:
                        await session.client_socket.send_json({
                            'type': 'stt_output_invalidation'
                        })

            elif data['event'] == 'text_prompt':
                session.prompt = f'{session.prompt or ""}{data["prompt"]}'

                await session.client_socket.send_json({
                    'type': 'stt_output',
                    'text': data['prompt']
                })

                trigger_llm(session, received_speech_queue)

            elif data['event'] == 'speech_toggle':
                session.speech_enabled = data['value']
                logger.warning(f'Speech {session.speech_enabled}')

            elif data['event'] == 'config':
                await session.set_config_from_event(data['field'], data['value'])

    except starlette.websockets.WebSocketDisconnect:
        pass

    except Exception as e:
        logger.error('Exception in main', exc_info=True)
        logger.error(str(e))

    finally:
        logger.warning(f'Terminating client')
        session.terminate()
