from typing import Literal, List

from pydantic import BaseModel
from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession


class WhisperConfig(BaseModel):
    model: Literal['medium.en', 'small.en', 'large-v3']
    language: Literal['en', 'cs']


class OllamaConfig(BaseModel):
    model: str
    ctx_length: int
    system_prompt: str
    repeat_penalty: float
    temperature: float
    tools: List[str]


class XTTSConfig(BaseModel):
    voice: str
    language: Literal['en', 'cs']


class AppConfig(BaseModel):
    prevalidate_prompt: bool
    inactivity_timeout_ms: int


class SessionConfig(BaseModel):
    ollama: OllamaConfig
    whisper: WhisperConfig
    xtts: XTTSConfig
    app: AppConfig


async def get_previous_or_default_config(db: AsyncSession):
    from db.models import Chat
    most_recent_chat = (await db.execute(select(Chat).order_by(desc(Chat.started_at)))).scalar()

    if most_recent_chat is not None:
        return most_recent_chat.config_db

    with open('./config.json', 'r') as f:
        return SessionConfig.model_validate_json(f.read()).model_dump()
