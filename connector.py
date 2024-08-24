import asyncio
import datetime
import json
from dataclasses import dataclass
from typing import Optional, Tuple
from urllib.parse import urlencode

import httpx
import numpy as np
import websockets
from fastapi import FastAPI, WebSocket
from ollama import AsyncClient

XTTS_OUTPUT_SAMPLING_RATE = 24000

app = FastAPI()

ASSISTANT_SYSTEM = """
You are Scarlett, my personal AI assistant.
You are kind, understanding and compassionate.
Do not use emojis or other unpronounceable characters in your output as I intend to synthesize it to speech.
"""

CLEANER_SYSTEM = """
You are a large language model. Your task is to validate and sanitize the transcription of speech to text before it reaches another AI assistant. 
You will be given the last few exchanges between the user and the assistant. The messages are going to be prefixed by either "USER:" or "ASSISTANT:". 
Your task is to determine, if the last user message fits into the ongoing conversation.
If the message fits, output TRUE. If it does not, output FALSE. 
Never output anything else than these two words.
The very first message is likely to just be a greeting, so accept any.
Remember, I am not talking to you, you are simply validating what I send you.
"""


@dataclass
class Session:
    client_socket: WebSocket
    stt_socket: Optional[websockets.WebSocketClientProtocol]
    stt_task: Optional[asyncio.Task]
    llm_submit_task: Optional[asyncio.Task]
    speech_send_task: Optional[asyncio.Task]
    prompt_segments_queue: Optional[asyncio.Queue]
    response_tokens_queue: Optional[asyncio.Queue]
    prompt: Optional[Tuple[str, datetime.datetime]]

    def terminate(self):
        if self.stt_task:
            self.stt_task.cancel()
        if self.llm_submit_task:
            self.llm_submit_task.cancel()
        if self.speech_send_task:
            self.speech_send_task.cancel()


@app.websocket("/ws/{client_id}")
async def websocket_endpoint(websocket: WebSocket, client_id: str):
    await websocket.accept()

    print(f"New client connected: {client_id}")

    session = Session(websocket, None, None, None, None, asyncio.Queue(), asyncio.Queue(), None)

    try:
        async with websockets.connect('ws://10.0.0.2:9090') as stt_socket:
            await session.response_tokens_queue.put('Hello there!')
            session.stt_socket = stt_socket
            session.stt_task = asyncio.create_task(stt_receiver(session))
            session.llm_submit_task = asyncio.create_task(llm_submitter(session))
            session.speech_send_task = asyncio.create_task(response_audio_sender(session))

            await stt_socket.send(json.dumps(
                {
                    "uid": client_id,
                    "language": "en",
                    "task": "transcribe",
                    "model": "large-v3",
                    "use_vad": True,
                    "vad_options": {
                        "threshold": 0.5,
                        "min_speech_duration_ms": 400,
                        "max_speech_duration_s": "Infinity",
                        "min_silence_duration_ms": 1000,
                        "window_size_samples": 1536,
                        "speech_pad_ms": 300
                    }
                }
            ))

            while True:
                data = await websocket.receive()
                await stt_socket.send(data['bytes'])

    finally:
        session.terminate()


async def stt_receiver(session: Session):
    previous_start, previous_text = None, None
    async for message in session.stt_socket:
        resp = json.loads(message)
        try:
            segments = resp['segments']
            last_segment = sorted(segments, key=lambda segment: float(segment['start']))[-1]

            if last_segment['start'] != previous_start:
                print(last_segment)
                session.prompt = (last_segment['text'], datetime.datetime.now())
            previous_start = last_segment['start']
        except KeyError:
            pass


async def llm_submitter(session: Session):
    message_history = []
    while True:
        if session.prompt:
            prompt, prompt_time = session.prompt
            if prompt_time < datetime.datetime.now() - datetime.timedelta(milliseconds=600):
                session.prompt = None

                wtf = '\n'.join(
                    [f'{"USER: " if message["role"] == "user" else "ASSISTANT: "}{message["content"].replace("\n", "")}'
                     for message in message_history[-5:]]
                )
                wtf = f'{wtf}\nUSER: {prompt}'
                response = await AsyncClient('http://10.0.0.2:11434').chat(
                    model='mistral-nemo:12b-instruct-2407-q8_0',
                    messages=[
                        {
                            'role': 'system',
                            'content': CLEANER_SYSTEM
                        },
                        {
                            'role': 'user',
                            'content': wtf
                        }
                    ]
                )
                passed_validation = response['message']['content'].strip()
                if passed_validation == 'FALSE':
                    continue

                print('Prompt detected and validated')

                message_history.append({
                    'role': 'user',
                    'content': prompt
                })

                response = []
                sentence = []
                async for part in await AsyncClient('http://10.0.0.2:11434').chat(
                        model='mistral-nemo:12b-instruct-2407-q8_0',
                        messages=[{'role': 'system', 'content': ASSISTANT_SYSTEM}] + message_history,
                        stream=True
                ):
                    msg = part['message']['content']
                    sentence.append(msg)
                    response.append(msg)
                    print(msg, end='', flush=True)
                    if msg in ('.', '!', '?') and len(sentence) > 0:
                        sentence = ''.join(sentence)
                        await session.response_tokens_queue.put(sentence)
                        sentence = []

                if sentence:
                    sentence = ''.join(sentence)
                    await session.response_tokens_queue.put(sentence)

                message_history.append({
                    'role': 'assistant',
                    'content': ''.join(response)
                })

        await asyncio.sleep(0.1)


async def response_audio_sender(session: Session):
    async with httpx.AsyncClient() as client:
        while True:
            sentence = await session.response_tokens_queue.get()
            sentence = sentence.strip()
            if not sentence:
                continue
            params = {
                'text': sentence,
                'speaker_wav': 'aloy.wav',
                'language': 'en'
            }

            sample_count = 0
            async with client.stream('GET', f'http://10.0.0.2:8020/tts_stream?{urlencode(params)}') as resp:
                async for chunk in resp.aiter_bytes(XTTS_OUTPUT_SAMPLING_RATE):
                    samples = np.frombuffer(chunk, dtype=np.int16).tolist()
                    sample_count += len(samples)
                    await session.client_socket.send_json({
                        'type': 'speech',
                        'samples': np.frombuffer(chunk, dtype=np.int16).tolist()
                    })
                    if sample_count > 2 * XTTS_OUTPUT_SAMPLING_RATE:
                        await asyncio.sleep(sample_count / XTTS_OUTPUT_SAMPLING_RATE * 0.9)
                        sample_count = 0
