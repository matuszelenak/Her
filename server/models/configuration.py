from typing import Literal, Union

from pydantic import BaseModel
from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession

from providers.kokoro import KokoroConfig
from providers.orpheus import OrpheusConfig


class STTConfig(BaseModel):
    provider: Literal['whisper'] = 'whisper'
    model: Literal['medium.en', 'small.en', 'large-v3']
    language: Literal['en', 'cs']


class AppConfig(BaseModel):
    voice_input_enabled: bool = True
    voice_output_enabled: bool = True
    after_user_speech_confirmation_delay_ms: int = 1000
    prevalidate_prompt: bool = False
    inactivity_timeout_ms: int | None = None


class SessionConfig(BaseModel):
    stt: STTConfig
    tts: Union[KokoroConfig, OrpheusConfig]
    app: AppConfig


async def get_previous_or_default_config(db: AsyncSession):
    from db.models import Chat
    most_recent_chat = (await db.execute(select(Chat).order_by(desc(Chat.started_at)))).scalar()

    if most_recent_chat is not None:
        return most_recent_chat.config_db

    with open('./config.json', 'r') as f:
        return SessionConfig.model_validate_json(f.read()).model_dump()
