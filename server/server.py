import asyncio
import logging
import subprocess
from datetime import datetime
from typing import Optional
from urllib.parse import urlparse
from uuid import uuid4

import requests
import starlette
from fastapi import FastAPI, WebSocket
from ollama import AsyncClient, Client

from components.llm import llm_submitter
from components.stt import stt_sender
from components.tts import tts_receiver
from utils.configuration import SessionConfig, get_default_config
from utils.constants import OLLAMA_API_URL, XTTS2_API_URL, WHISPER_API_URL
from utils.session import get_session, terminate_session, Session

app = FastAPI()

logger = logging.getLogger(__name__)
session: Optional[Session] = None


@app.get('/models')
async def get_models():
    return (await AsyncClient(OLLAMA_API_URL).list())['models']


@app.get('/status')
async def get_status():
    statuses = {}

    try:
        whisper_parsed_url = urlparse(WHISPER_API_URL)
        subprocess.check_output(['nc', '-zv', f'{whisper_parsed_url.hostname}', f'{whisper_parsed_url.port}'])
        statuses['whisper'] = True
    except subprocess.CalledProcessError:
        statuses['whisper'] = False

    try:
        requests.get(f'{XTTS2_API_URL}/api/ready', timeout=100)
        statuses['xtts'] = True
    except requests.ConnectionError:
        statuses['xtts'] = False

    try:
        statuses['ollama'] = Client(OLLAMA_API_URL).ps()
    except:
        statuses['ollama'] = False

    return statuses


@app.get('/config')
async def get_config(client_id: str):
    global session
    return session.config


@app.post('/config')
async def set_config(payload: SessionConfig, client_id: str):
    global session
    session.config = payload

    return session.config


@app.websocket("/ws")
async def websocket_input_endpoint(websocket: WebSocket):
    global session
    await websocket.accept()

    logger.warning(f"New client connected")

    session = Session(
        str(uuid4()),
        get_default_config()
    )
    session.client_socket = websocket

    cl_receiver = None
    try:
        received_speech_queue = asyncio.Queue()

        session.stt_task = asyncio.create_task(stt_sender(session, received_speech_queue))
        session.llm_submit_task = asyncio.create_task(llm_submitter(session, received_speech_queue))
        session.tts_task = asyncio.create_task(tts_receiver(session))

        while True:
            data = await websocket.receive_json()
            if data['event'] == 'free_space':
                session.free_samples = data["value"]
                logger.warning(f'Free {data["value"]}')

            elif data['event'] == 'resp_wait':
                logger.warning('Throttling!')

            elif data['event'] == 'resp_ok':
                session.last_accepted_speech_id = data['id']

            elif data['event'] == 'samples':
                if session.user_speaking_status[0]:
                    await received_speech_queue.put(data['data'])

            elif data['event'] == 'speech_end':
                logger.warning('Speak end')
                session.user_speaking_status = (False, datetime.now())

            elif data['event'] == 'speech_start':
                logger.warning('Speak start')
                session.user_speaking_status = (True, datetime.now())

    except starlette.websockets.WebSocketDisconnect:
        pass

    except Exception as e:
        logger.error('Exception in main')
        logger.error(str(e))

    finally:
        if cl_receiver is not None:
            cl_receiver.cancel()

        logger.warning(f'Terminating client')
        session.terminate()
        session = None
