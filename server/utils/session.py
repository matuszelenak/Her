import asyncio
import datetime
import logging
from dataclasses import dataclass
from typing import Optional, Tuple, Dict

from starlette.websockets import WebSocket

from utils.configuration import SessionConfig, get_default_config

logger = logging.getLogger(__name__)


@dataclass
class Session:
    id: str
    config: SessionConfig
    client_socket: WebSocket = None
    stt_task: Optional[asyncio.Task] = None
    tts_task: Optional[asyncio.Task] = None
    llm_submit_task: Optional[asyncio.Task] = None
    prompt_segments_queue: Optional[asyncio.Queue] = asyncio.Queue()
    response_tokens_queue: Optional[asyncio.Queue] = asyncio.Queue()
    response_speech_queue: Optional[asyncio.Queue] = asyncio.Queue()

    user_speaking_status: Tuple[bool, datetime.datetime] = (False, None)
    prompt: Optional[str] = None
    last_accepted_speech_id: Optional[str] = None
    free_samples: int = 0

    def terminate(self):
        if self.stt_task:
            self.stt_task.cancel()
        if self.llm_submit_task:
            self.llm_submit_task.cancel()
        if self.tts_task:
            self.tts_task.cancel()


session_store: Dict[str, Session] = dict()


def get_session(client_id):
    if client_id not in session_store:
        logger.warning(f'Creating new session for {client_id}')
        session_store[client_id] = Session(
            client_id,
            get_default_config()
        )

    return session_store[client_id]


def terminate_session(client_id):
    if client_id in session_store:
        session_store[client_id].terminate()
        del session_store[client_id]
