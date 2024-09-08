import asyncio
import datetime
import json
import os
from dataclasses import dataclass
from typing import Optional, Tuple
from urllib.parse import urlencode

import httpx
import numpy as np
import scipy
import starlette
import websockets
from fastapi import FastAPI, WebSocket
from ollama import AsyncClient

from utils.llm_response import get_sentences
from utils.tools import get_ip_address_def, get_current_moon_phase_def, tool_call_regex, get_ip_address

XTTS_OUTPUT_SAMPLING_RATE = 24000

app = FastAPI()

model = 'mistral-nemo:12b-instruct-2407-q8_0'
# model = 'llama3.1:8b-instruct-q8_0'

CLEANER_SYSTEM = """
You are a large language model. Your task is to validate and sanitize the transcription of speech to text before it reaches another AI assistant. 
You will be given the last few exchanges between the user and the assistant. The messages are going to be prefixed by either "USER:" or "ASSISTANT:". 
Your task is to determine, if the last user message fits into the ongoing conversation.
If the message fits, output TRUE. If it does not, output FALSE. 
Never output anything else than these two words.
The very first message is likely to just be a greeting, so accept any.
Remember, I am not talking to you, you are simply validating what I send you.
"""

tools = {
    'get_ip_address': get_ip_address
}

WHISPER_API_URL = os.environ.get('WHISPER_API_URL')
XTTS2_API_URL = os.environ.get('XTTS2_API_URL')
OLLAMA_API_URL = os.environ.get('OLLAMA_API_URL')


@dataclass
class Session:
    client_socket: WebSocket
    stt_socket: Optional[websockets.WebSocketClientProtocol]
    stt_task: Optional[asyncio.Task]
    tts_task: Optional[asyncio.Task]
    llm_submit_task: Optional[asyncio.Task]
    speech_send_task: Optional[asyncio.Task]
    prompt_segments_queue: Optional[asyncio.Queue]
    response_tokens_queue: Optional[asyncio.Queue]
    response_speech_queue: Optional[asyncio.Queue]

    prompt: Optional[Tuple[str, datetime.datetime]]

    def terminate(self):
        if self.stt_task:
            self.stt_task.cancel()
        if self.llm_submit_task:
            self.llm_submit_task.cancel()
        if self.speech_send_task:
            self.speech_send_task.cancel()
        if self.tts_task:
            self.tts_task.cancel()


@app.websocket("/ws/{client_id}")
async def websocket_endpoint(websocket: WebSocket, client_id: str):
    await websocket.accept()

    print(f"New client connected: {client_id}")

    session = Session(websocket, None, None, None, None, None, asyncio.Queue(), asyncio.Queue(), asyncio.Queue(), None)

    try:
        async with websockets.connect(WHISPER_API_URL) as stt_socket:
            session.stt_socket = stt_socket
            session.stt_task = asyncio.create_task(stt_receiver(session))
            session.llm_submit_task = asyncio.create_task(llm_submitter(session))
            session.tts_task = asyncio.create_task(tts_receiver(session))
            session.speech_send_task = asyncio.create_task(response_audio_sender(session))

            await stt_socket.send(json.dumps(
                {
                    "uid": client_id,
                    "language": "en",
                    "task": "transcribe",
                    "model": "medium.en",
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
                data = await websocket.receive_bytes()
                samples = np.frombuffer(data, dtype=np.float32)
                samples = scipy.signal.resample(samples, round(samples.shape[0] * (16000 / 44100)))

                await stt_socket.send(samples.tobytes())

    except starlette.websockets.WebSocketDisconnect:
        pass

    finally:
        print('Terminating')

        session.terminate()


async def stt_receiver(session: Session):
    previous_start, previous_text = None, None
    async for message in session.stt_socket:
        resp = json.loads(message)
        try:
            segments = resp['segments']
            last_segment = sorted(segments, key=lambda segment: float(segment['start']))[-1]
            if last_segment['start'] != previous_start or last_segment['text'] != previous_text:
                print(last_segment)
                session.prompt = (last_segment['text'], datetime.datetime.now())

            previous_start = last_segment['start']
            previous_text = last_segment['text']
        except KeyError:
            pass


async def llm_submitter(session: Session):
    message_history = []
    while True:
        if session.prompt:
            prompt, prompt_time = session.prompt
            if prompt_time < datetime.datetime.now() - datetime.timedelta(milliseconds=1000):
                session.prompt = None

                wtf = '\n'.join(
                    [f'{"USER: " if message["role"] == "user" else "ASSISTANT: "}{message["content"].replace("\n", "")}'
                     for message in message_history[-5:]]
                )
                wtf = f'{wtf}\nUSER: {prompt}'
                llm_response = await AsyncClient(OLLAMA_API_URL).chat(
                    model=model,
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
                passed_validation = llm_response['message']['content'].strip()
                if passed_validation == 'FALSE':
                    print('Did not pass validation')
                    continue

                print('Prompt detected and validated')

                message_history.append({
                    'role': 'user',
                    'content': prompt
                })

                client = AsyncClient(OLLAMA_API_URL)

                while True:
                    tool_answers = []
                    async for sentence_type, content in get_sentences(
                            client.chat(
                                model=model,
                                messages=[
                                             # {'role': 'system', 'content': ASSISTANT_SYSTEM}
                                         ] + message_history,
                                stream=True,
                                # tools=[
                                #     get_ip_address_def
                                # ],
                            )
                    ):
                        if sentence_type == 'interactive':
                            await session.response_tokens_queue.put(content)
                        else:
                            fn = tools.get(content['name'])
                            if fn:
                                parameters = content['parameters']
                                tool_answers.append(fn(**parameters))

                    print(tool_answers)
                    if len(tool_answers) > 0:
                        for answer in tool_answers:
                            message_history.append({
                                'role': 'tool',
                                'content': str(answer)
                            })
                    else:
                        break

                print('Done')

                message_history.append({
                    'role': 'assistant',
                    'content': ''.join(llm_response)
                })

        await asyncio.sleep(0.1)


async def tts_receiver(session: Session):
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
            async with client.stream('GET', f'{XTTS2_API_URL}/tts_stream?{urlencode(params)}') as resp:
                async for chunk in resp.aiter_bytes(XTTS_OUTPUT_SAMPLING_RATE):
                    samples = np.frombuffer(chunk, dtype=np.int16)
                    samples = samples / np.iinfo(np.int16).max
                    samples = scipy.signal.resample(samples,
                                                    round(samples.shape[0] * (48000 / XTTS_OUTPUT_SAMPLING_RATE)))

                    await session.response_speech_queue.put(samples)


async def response_audio_sender(session: Session):
    while True:
        samples = await session.response_speech_queue.get()
        await session.client_socket.send_json({
            'type': 'speech',
            'samples': samples.tolist()
        })
        await asyncio.sleep(samples.shape[0] / 48000 * 0.90)
