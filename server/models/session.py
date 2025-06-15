import asyncio
import datetime
import json
from dataclasses import dataclass
from typing import Optional, Any
from uuid import uuid4

import aiofiles
import logfire
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm.attributes import flag_modified
from starlette.websockets import WebSocket

from db.models import Chat
from models.configuration import SessionConfig
from models.sent_events import WsSendEvent


@dataclass
class Session:
    id: str
    db: AsyncSession
    chat: Chat
    config: SessionConfig

    client_socket: WebSocket = None
    stt_task: Optional[asyncio.Task] = None
    llm_task: Optional[asyncio.Task] = None
    tts_task: Optional[asyncio.Task] = None

    prompt: Optional[str] = None

    last_interaction: Optional[datetime.datetime] = None

    speech_sending_lock = asyncio.Lock()

    async def send_event(self, event: WsSendEvent):
        return await self.client_socket.send_json(event.model_dump())

    def terminate(self):
        if self.stt_task:
            self.stt_task.cancel()
        if self.tts_task:
            self.tts_task.cancel()
        if self.llm_task:
            self.llm_task.cancel()

    async def append_message(self, message):
        if self.chat.id is None:
            self.chat.id = self.chat._id or uuid4()
            self.chat.header = message['content'][:30]
            self.chat.started_at = datetime.datetime.now()

            self.db.add(self.chat)
            await self.db.commit()
            await self.db.refresh(self.chat)


        self.chat.messages.append(message | {
            'time': datetime.datetime.now().timestamp()
        })
        flag_modified(self.chat, 'messages')
        await self.db.commit()
        await self.db.refresh(self.chat)

    async def set_config_field_from_event(self, field: str, value: Any):
        cfg_json = self.config.model_dump()
        curr = cfg_json
        spl = field.split('.')
        for part in spl[:-1]:
            curr = curr[part]

        curr[spl[-1]] = value

        logfire.info(f'Changed config field {field} -> {value}')

        async with aiofiles.open('/config.json', 'w', encoding='utf-8') as f:
            await f.write(json.dumps(cfg_json))

        self.config = SessionConfig.model_validate(cfg_json)
