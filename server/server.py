import asyncio
import json
import logging
import subprocess
from datetime import datetime
from typing import Dict
from urllib.parse import urlparse
from uuid import uuid4

import httpx
import requests
import starlette
from fastapi import FastAPI, WebSocket, Depends
from fastapi.encoders import jsonable_encoder
from ollama import AsyncClient, Client
from sqlalchemy import select, desc, delete
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import load_only

from db.models import Chat
from db.session import get_db
from tasks.coordination import trigger_llm
from tasks.stt import stt_sender
from utils.configuration import get_default_config, set_config_from_event
from utils.constants import OLLAMA_API_URL, XTTS2_API_URL, WHISPER_API_URL
from utils.session import Session
from utils.validation import should_agent_respond

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
async def get_chat(chat_id: str, db: AsyncSession = Depends(get_db)):
    query = select(Chat).filter(Chat.id == chat_id)
    result = await db.execute(query)
    return jsonable_encoder(result.scalar())


@app.delete('/chat/{chat_id}')
async def get_chats(chat_id: str, db: AsyncSession = Depends(get_db)):
    query = delete(Chat).filter(Chat.id == chat_id)
    await db.execute(query)
    await db.commit()
    return {}


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
                    warrants_response = await should_agent_respond(session)

                    if warrants_response:
                        trigger_llm(session, received_speech_queue)
                    else:
                        await session.client_socket.send_json({
                            'type': 'stt_output_invalidation'
                        })

                        session.stt_task.cancel()
                        session.stt_task = asyncio.create_task(stt_sender(session, received_speech_queue))

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

            elif data['event'] == 'config_request':
                await websocket.send_json({
                    'type': 'config',
                    'config': json.loads(session.config.model_dump_json())
                })

            elif data['event'] == 'config':
                set_config_from_event(session.config, data['field'], data['value'])
                logger.warning(f'Successfully set {data['field']} to {data['value']}')


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
