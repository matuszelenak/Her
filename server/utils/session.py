import asyncio
import datetime
import logging
from dataclasses import dataclass
from typing import Optional, Tuple, Dict, List

from sqlalchemy import insert, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm.attributes import flag_modified
from starlette.websockets import WebSocket

from db.models import Chat
from utils.configuration import SessionConfig, get_default_config

logger = logging.getLogger(__name__)


@dataclass
class Session:
    id: str
    config: SessionConfig
    db: AsyncSession
    client_socket: WebSocket = None
    stt_task: Optional[asyncio.Task] = None
    llm_task: Optional[asyncio.Task] = None
    tts_task: Optional[asyncio.Task] = None

    chat: Chat = None

    user_speaking_status: Tuple[bool, datetime.datetime] = (False, None)
    prompt: Optional[str] = None
    last_accepted_speech_id: Optional[str] = None
    free_samples: int = 0

    speech_enabled: bool = True

    def terminate(self):
        if self.stt_task:
            self.stt_task.cancel()
        if self.tts_task:
            self.tts_task.cancel()

    async def load_chat(self, chat_id):
        query = select(Chat).filter(Chat.id == chat_id)
        results = await self.db.execute(query)
        result = results.scalar()
        self.chat = result

    async def append_message(self, message):
        if self.chat is None:
            chat = Chat(
                messages=[],
                header=message['content'][:30],
                started_at=datetime.datetime.now()
            )

            self.db.add(chat)
            await self.db.commit()
            await self.db.refresh(chat)

            self.chat = chat
            logger.warning(str(self.chat))

            await self.client_socket.send_json({
                'type': 'new_chat'
            })

        self.chat.messages.append(message | {'time': datetime.datetime.now().timestamp()})
        flag_modified(self.chat, 'messages')
        await self.db.commit()
        await self.db.refresh(self.chat)
        logger.warning(str(self.chat))

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
