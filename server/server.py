import asyncio
import logging
import subprocess
from datetime import datetime, timedelta
from typing import Optional, Dict
from urllib.parse import urlparse
from uuid import uuid4

import httpx
import requests
import starlette
from fastapi import FastAPI, WebSocket, Depends, HTTPException
from fastapi.encoders import jsonable_encoder
from ollama import AsyncClient, Client
from sqlalchemy import select, desc, delete
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import load_only

from db.models import Chat
from db.session import get_db
from tasks.coordination import trigger_llm
from tasks.stt import stt_sender
from utils.configuration import SessionConfig, get_default_config
from utils.constants import OLLAMA_API_URL, XTTS2_API_URL, WHISPER_API_URL
from utils.session import Session

app = FastAPI()

logger = logging.getLogger(__name__)
sessions: Dict[str, Session] = {}


@app.get('/models')
async def get_models():
    return (await AsyncClient(OLLAMA_API_URL).list())['models']


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
async def get_chats(chat_id: str, db: AsyncSession = Depends(get_db)):
    query = select(Chat).filter(Chat.id == chat_id)
    result = await db.execute(query)
    return jsonable_encoder(result.scalar())


@app.delete('/chat/{chat_id}')
async def get_chats(chat_id: str, db: AsyncSession = Depends(get_db)):
    query = delete(Chat).filter(Chat.id == chat_id)
    await db.execute(query)
    await db.commit()
    return {}

@app.get('/config')
async def get_config(session_id: str):
    global sessions

    if session_id not in sessions:
        return HTTPException(status_code=404)

    return sessions[session_id].config


@app.post('/config')
async def set_config(payload: SessionConfig, session_id: str):
    global sessions

    if session_id not in sessions:
        return HTTPException(status_code=404)


    sessions[session_id].config = payload

    return sessions[session_id].config


async def services_monitor_notify_task(websocket: WebSocket):
    while True:
        statuses = {}

        try:
            whisper_parsed_url = urlparse(WHISPER_API_URL)
            subprocess.check_output(['nc', '-zv', f'{whisper_parsed_url.hostname}', f'{whisper_parsed_url.port}'], stderr=subprocess.PIPE)
            statuses['whisper'] = True
        except subprocess.CalledProcessError:
            statuses['whisper'] = False

        try:
            requests.get(f'{XTTS2_API_URL}/api/ready', timeout=100)
            statuses['xtts'] = True
        except requests.ConnectionError:
            statuses['xtts'] = False

        try:
             ollama_status = Client(OLLAMA_API_URL).ps()

             statuses['ollama'] = [model['name'] for model in ollama_status['models']]
        except:
            statuses['ollama'] = None

        await websocket.send_json({
            'type': 'dependency_status',
            'status': statuses
        })

        await asyncio.sleep(2)


@app.websocket("/ws/{chat_id}")
@app.websocket("/ws")
async def websocket_input_endpoint(websocket: WebSocket, chat_id: str = None, db: AsyncSession = Depends(get_db)):
    global sessions
    await websocket.accept()

    logger.info(f"New client connected")

    session_id = str(uuid4())

    session = Session(
        session_id,
        get_default_config(),
        db
    )
    sessions[session_id] = session

    await websocket.send_json({
        'type': 'session_init',
        'id': session_id
    })

    session.client_socket = websocket
    if chat_id is not None:
        await session.load_chat(chat_id)


    status_notify_task = None
    try:
        received_speech_queue = asyncio.Queue()

        session.stt_task = asyncio.create_task(stt_sender(session, received_speech_queue))
        status_notify_task = asyncio.create_task(services_monitor_notify_task(websocket))

        while True:
            data = await websocket.receive_json()
            if data['event'] == 'free_space':
                session.free_samples = data["value"]
                # logger.warning(f'Free {data["value"]}')

            elif data['event'] == 'resp_wait':
                logger.warning('Throttling!')

            # elif data['event'] == 'resp_ok':
            #     session.last_accepted_speech_id = data['id']

            elif data['event'] == 'samples':
                session.user_speaking_status = (True, datetime.now())
                await received_speech_queue.put(data['data'])

            elif data['event'] == 'speech_end':
                logger.info('Speak end')
                session.user_speaking_status = (False, datetime.now())

            elif data['event'] == 'speech_prompt_end':
                if session.prompt:
                    trigger_llm(session, received_speech_queue)

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


    except starlette.websockets.WebSocketDisconnect:
        pass

    except Exception as e:
        logger.error('Exception in main')
        logger.error(str(e))

    finally:
        if status_notify_task is not None:
            status_notify_task.cancel()

        logger.warning(f'Terminating client')
        session.terminate()

        del sessions[session_id]
