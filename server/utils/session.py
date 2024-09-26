import asyncio
import datetime
from dataclasses import dataclass
from typing import Optional, Tuple

import websockets
from starlette.websockets import WebSocket

from utils.configuration import SessionConfig


@dataclass
class Session:
    config: SessionConfig
    client_socket: WebSocket
    stt_socket: Optional[websockets.WebSocketClientProtocol]
    stt_task: Optional[asyncio.Task] = None
    tts_task: Optional[asyncio.Task] = None
    llm_submit_task: Optional[asyncio.Task] = None
    speech_send_task: Optional[asyncio.Task] = None
    prompt_segments_queue: Optional[asyncio.Queue] = asyncio.Queue()
    response_tokens_queue: Optional[asyncio.Queue] = asyncio.Queue()
    response_speech_queue: Optional[asyncio.Queue] = asyncio.Queue()

    prompt: Optional[Tuple[str, datetime.datetime, float]] = None

    def terminate(self):
        if self.stt_task:
            self.stt_task.cancel()
        if self.llm_submit_task:
            self.llm_submit_task.cancel()
        if self.speech_send_task:
            self.speech_send_task.cancel()
        if self.tts_task:
            self.tts_task.cancel()
