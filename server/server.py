import asyncio
import logging
import subprocess
from urllib.parse import urlparse

import requests
import starlette
from fastapi import FastAPI, WebSocket
from ollama import AsyncClient, Client

from components.llm import llm_submitter
from components.stt import stt_sender
from components.tts import tts_receiver
from utils.configuration import SessionConfig
from utils.constants import OLLAMA_API_URL, XTTS2_API_URL, WHISPER_API_URL
from utils.queue import empty_queue
from utils.session import get_session, terminate_session

app = FastAPI()

logger = logging.getLogger(__name__)


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


@app.get('/config/{client_id}')
async def get_config(client_id: str):
    return get_session(client_id).config

@app.post('/config/{client_id}')
async def set_config(payload: SessionConfig, client_id: str):
    session = get_session(client_id)
    print(payload)
    session.config = payload

    return session.config


@app.websocket("/ws/{client_id}/output")
async def websocket_output_endpoint(websocket: WebSocket, client_id: str):
    await websocket.accept()

    try:
        session = get_session(client_id)

        buffer = []
        while True:
            samples = await session.response_speech_queue.get()

            if session.user_speaking_status[0] == True:
                logger.warning('User started speaking')
                session.tts_task.cancel()

                await empty_queue(session.response_speech_queue)
                await empty_queue(session.response_tokens_queue)

                session.tts_task = asyncio.create_task(tts_receiver(session))
                continue

            for sample in samples:
                if len(buffer) < 4096:
                    buffer.append(sample)
                else:
                    while True:
                        await websocket.send_json({
                            'type': 'speech',
                            'samples': buffer
                        })
                        resp = await websocket.receive_json()
                        if resp == {}:
                            buffer = []
                            break
                        else:
                            await asyncio.sleep(0.1)


    except starlette.websockets.WebSocketDisconnect:
        pass


@app.websocket("/ws/{client_id}/input")
async def websocket_input_endpoint(websocket: WebSocket, client_id: str):
    await websocket.accept()

    print(f"New client connected: {client_id}")

    session = get_session(client_id)
    session.client_socket = websocket

    try:
        session.stt_task = asyncio.create_task(stt_sender(session))
        session.llm_submit_task = asyncio.create_task(llm_submitter(session))
        session.tts_task = asyncio.create_task(tts_receiver(session))

        while True:
            await asyncio.sleep(1)

    except starlette.websockets.WebSocketDisconnect:
        pass

    finally:
        print(f'Terminating client {client_id}')
        terminate_session(client_id)
