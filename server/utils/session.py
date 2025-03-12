import asyncio
import datetime
from dataclasses import dataclass
from typing import Optional, Tuple
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm.attributes import flag_modified
from starlette.websockets import WebSocket

from db.models import Chat
from utils.log import get_logger

logger = get_logger(__name__)


@dataclass
class Session:
    id: str
    db: AsyncSession
    chat: Chat
    client_socket: WebSocket = None
    stt_task: Optional[asyncio.Task] = None
    llm_task: Optional[asyncio.Task] = None
    tts_task: Optional[asyncio.Task] = None

    user_speaking_status: Tuple[bool, datetime.datetime] = (False, None)
    prompt: Optional[str] = None

    speech_enabled: bool = True

    last_interaction: Optional[datetime.datetime] = None

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
        if self.chat.id is None:
            self.chat.id = uuid4()
            self.chat.header = message['content'][:30]
            self.chat.started_at = datetime.datetime.now()

            self.db.add(self.chat)
            await self.db.commit()
            await self.db.refresh(self.chat)

            await self.client_socket.send_json({
                'type': 'new_chat',
                'chat_id': str(self.chat.id)
            })

        self.chat.messages.append(message | {
            'time': datetime.datetime.now().timestamp()
        })
        flag_modified(self.chat, 'messages')
        await self.db.commit()
        await self.db.refresh(self.chat)

    async def set_config_from_event(self, field, value):
        curr = self.chat.config_db
        spl = field.split('.')
        for part in spl[:-1]:
            curr = curr[part]

        curr[spl[-1]] = value

        if self.chat.id is not None:
            flag_modified(self.chat, 'config_db')
            await self.db.commit()
            await self.db.refresh(self.chat)

        logger.debug(f'Changed config field {field} -> {value}')
