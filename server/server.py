import asyncio
import datetime
import json
import logging
from typing import Dict
from urllib.parse import urlencode

import httpx
import numpy as np
import scipy
import starlette
import websockets
from fastapi import FastAPI, WebSocket
from ollama import AsyncClient
from sortedcontainers import SortedDict

from utils.configuration import SessionConfig, get_default_config
from utils.constants import OLLAMA_API_URL, XTTS2_API_URL, XTTS_OUTPUT_SAMPLING_RATE, WHISPER_API_URL
from utils.llm_response import get_sentences
from utils.session import Session
from utils.tools import get_ip_address

app = FastAPI()

tools = {
    'get_ip_address': get_ip_address
}

logger = logging.getLogger(__name__)

sessions: Dict[str, Session] = dict()


@app.get('/models')
async def get_models():
    return await AsyncClient(OLLAMA_API_URL).list()


@app.post('/config')
async def set_config(payload: SessionConfig, client_id: str):
    sessions[client_id].config = payload

    return sessions[client_id].config


@app.websocket("/ws/{client_id}/output")
async def websocket_output_endpoint(websocket: WebSocket, client_id: str):
    await websocket.accept()

    try:
        while True:
            session = sessions.get(client_id, None)
            if session is not None:
                break
            else:
                await asyncio.sleep(0.5)

        buffer = []
        while True:
            samples = await session.response_speech_queue.get()
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

    session = Session(
        client_id,
        get_default_config(),
        websocket,
        None
    )
    sessions[client_id] = session

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

        session.terminate()
        del sessions[client_id]


async def stt_sender(session: Session):
    receiver_task = None
    try:
        async for stt_socket in websockets.connect(WHISPER_API_URL):
            try:
                await stt_socket.send(json.dumps(
                    {
                        "uid": session.id,
                        "language": "en",
                        "task": "transcribe",
                        "model": session.config.whisper.model,
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

                receiver_task = asyncio.create_task(stt_receiver(session, stt_socket))

                while True:
                    data = await session.client_socket.receive_bytes()
                    samples = np.frombuffer(data, dtype=np.float32)
                    samples = scipy.signal.resample(samples, round(samples.shape[0] * (16000 / 44100)))

                    await stt_socket.send(samples.tobytes())

            except websockets.ConnectionClosed:
                logging.warning('Connection to Whisper closed')
                continue

    except asyncio.CancelledError:
        logger.warning('STT Task cancelled')
    except Exception as e:
        logger.warning('STT task exception')
        logger.warning(e)
    finally:
        if receiver_task is not None:
            receiver_task.cancel()

async def stt_receiver(session: Session, socket):
    end_ts_to_segment_tree = SortedDict()
    memo = {}

    def calculate_prefix(curr_start):
        if curr_start in memo:
            return memo[curr_start]

        if curr_start == 0.0:
            return ""

        next_start = None

        logger.warning(f'Seeking for {curr_start}')
        if curr_start in end_ts_to_segment_tree:
            next_start, prev_text = end_ts_to_segment_tree[curr_start]
        else:
            p = end_ts_to_segment_tree.bisect_left(curr_start)

            if p > 0:
                logger.warning(f'Position {p}')
                best_score = 100000
                prev_text = None
                try:
                    closest_left, (seg_start, seg_text) = end_ts_to_segment_tree.peekitem(p - 1)
                    if closest_left > curr_start:
                        logger.warning('WTF')
                        logger.warning(str(end_ts_to_segment_tree))

                    if abs(closest_left - curr_start) < best_score:
                        logger.warning(f'CL {curr_start} -> {closest_left}')
                        best_score = abs(closest_left - curr_start)
                        next_start = seg_start
                        prev_text = seg_text
                except Exception as e:
                    logger.error(e)
                try:
                    closest_right, (seg_start, seg_text) = end_ts_to_segment_tree.peekitem(p)
                    if abs(closest_right - curr_start) < best_score and abs(closest_right - curr_start) < 0.3:
                        logger.warning(f'CR {curr_start} -> {closest_right}')
                        next_start = seg_start
                        prev_text = seg_text
                except Exception as e:
                    logger.error(e)

        if next_start is None:
            # logger.error(f'DIDNT FIND SHIT for {curr_start}')
            # logger.warning(str(memo))
            return ""

        elif next_start == curr_start:
            # logger.error(f'WHAT??? {curr_start} {next_start}')
            # logger.error(str(end_ts_to_segment_tree))
            return ""

        prefix = calculate_prefix(next_start)
        memo[next_start] = prefix

        return prefix + prev_text

    previous_start, previous_text = None, None

    last_cutoff = - 1

    async for message in socket:
        resp = json.loads(message)
        logger.warning(resp)
        try:
            segments = [x for x in resp['segments'] if float(x['start']) > last_cutoff]
            if len(segments) == 0:
                continue
            last_segment = sorted(segments, key=lambda segment: float(segment['start']))[-1]

            start_ts = float(last_segment['start'])
            end_ts = float(last_segment['end'])

            if last_segment['start'] != previous_start or last_segment['text'] != previous_text:
                end_ts_to_segment_tree[end_ts] = (start_ts, last_segment['text'])
                complete = calculate_prefix(start_ts) + last_segment['text']
                logger.warning(complete)
                session.prompt = (complete, datetime.datetime.now(), end_ts)

                await session.client_socket.send_json({
                    'type': 'stt_output',
                    'text': complete
                })

            previous_start = last_segment['start']
            previous_text = last_segment['text']
        except Exception as e:
            logger.error(str(e))


async def llm_submitter(session: Session):
    message_history = []
    while True:
        if session.prompt:
            prompt, prompt_time, cutoff = session.prompt
            if prompt_time < datetime.datetime.now() - datetime.timedelta(
                    milliseconds=session.config.app.speech_submit_delay_ms
            ):
                session.prompt = None
                session.stt_task.cancel()
                session.stt_task = asyncio.create_task(stt_sender(session))

                #
                # if session.config.app.prevalidate_prompt and not await is_prompt_valid(session, prompt, message_history):
                #     continue

                message_history.append({
                    'role': 'user',
                    'content': prompt
                })

                client = AsyncClient(OLLAMA_API_URL)

                async def send_token(token):
                    await session.client_socket.send_json({
                        'type': 'token',
                        'token': token
                    })

                while True:
                    tool_answers = []
                    printable_response = ""
                    async for sentence_type, content in get_sentences(
                            client.chat(
                                model=session.config.ollama.model,
                                messages=[{'role': 'system',
                                           'content': session.config.ollama.system_prompt}] + message_history,
                                stream=True,
                                # tools=[
                                #     get_ip_address_def
                                # ],
                            ),
                            token_handler=send_token
                    ):
                        if sentence_type == 'interactive':
                            logger.warning(f'Adding to TTS queue {content}')
                            await session.response_tokens_queue.put(content)
                            printable_response += content
                        else:
                            fn = tools.get(content['name'])
                            if fn:
                                parameters = content['parameters']
                                tool_answers.append(fn(**parameters))

                    if len(tool_answers) > 0:
                        for answer in tool_answers:
                            message_history.append({
                                'role': 'tool',
                                'content': str(answer)
                            })
                    else:
                        message_history.append({
                            'role': 'assistant',
                            'content': ''.join(printable_response)
                        })
                        break

        await asyncio.sleep(0.1)


async def tts_receiver(session: Session):
    while True:
        logger.warning('Awaiting TTS queue')
        sentence = await session.response_tokens_queue.get()
        sentence = sentence.strip()
        if not sentence:
            continue
        params = {
            'text': sentence,
            'voice': 'aloy.wav',
            'language': 'en',
            'output_file': 'whatever.wav'
        }
        logger.warning(f'Submitting for TTS {sentence}')
        async with httpx.AsyncClient() as client:
            async with client.stream(
                    'GET',
                    f'{XTTS2_API_URL}/api/tts-generate-streaming?{urlencode(params)}'
            ) as resp:
                async for chunk in resp.aiter_bytes(XTTS_OUTPUT_SAMPLING_RATE):
                    samples = np.frombuffer(chunk, dtype=np.int16)
                    samples = samples / np.iinfo(np.int16).max
                    samples = scipy.signal.resample(
                        samples,
                        round(samples.shape[0] * (48000 / XTTS_OUTPUT_SAMPLING_RATE))
                    )

                    await session.response_speech_queue.put(samples.tolist())
