import asyncio
import base64
import json
import logging

import numpy as np
import websockets
from sortedcontainers import SortedDict

from utils.constants import WHISPER_API_URL
from utils.session import Session

logger = logging.getLogger(__name__)



async def stt_sender(session: Session, received_speech_queue: asyncio.Queue):
    receiver_task = None
    try:
        async with websockets.connect(WHISPER_API_URL) as stt_socket:
            await stt_socket.send(json.dumps(
                {
                    "uid": session.id,
                    "language": "en",
                    "task": "transcribe",
                    "model": session.chat.config.whisper.model,
                    "use_vad": False
                }
            ))

            receiver_task = asyncio.create_task(stt_receiver(session, stt_socket))

            while True:
                samples = await received_speech_queue.get()
                samples = base64.b64decode(samples)
                # logger.warning(f'Received {len(samples)} samples')
                samples = np.frombuffer(samples, dtype=np.float32)
                # samples = scipy.signal.resample(samples, round(samples.shape[0] * (16000 / 44100)))
                logger.warning(f'Sending {samples.shape} samples')
                await stt_socket.send(samples.tobytes())

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
                complete = (calculate_prefix(start_ts) + last_segment['text']).strip()
                # logger.warning(complete)
                session.prompt = complete

                await session.client_socket.send_json({
                    'type': 'stt_output',
                    'text': complete
                })

            previous_start = last_segment['start']
            previous_text = last_segment['text']
        except Exception as e:
            logger.error(str(e))
