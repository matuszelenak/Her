import os.path
import shutil
from typing import Literal, Union

import aiofiles
from pydantic import BaseModel

from providers.chatterbox import ChatterBoxConfig
from providers.kokoro import KokoroConfig
from providers.orpheus import OrpheusConfig


class STTConfig(BaseModel):
    provider: Literal['whisper'] = 'whisper'
    model: Literal['medium.en', 'small.en', 'large-v3']
    language: Literal['en', 'cs']


class AppConfig(BaseModel):
    voice_input_enabled: bool = True
    voice_output_enabled: bool = True
    after_user_speech_confirmation_delay_ms: int = 500
    prevalidate_prompt: bool = False
    inactivity_timeout_ms: int | None = None


class SessionConfig(BaseModel):
    stt: STTConfig
    tts: Union[KokoroConfig, OrpheusConfig, ChatterBoxConfig]
    app: AppConfig


async def load_config():
    if not os.path.exists('/config.json'):
        shutil.copy('config.template.json', '/config.json')

    async with aiofiles.open('/config.json', mode='r', encoding='utf-8') as file:
        return SessionConfig.model_validate_json(await file.read())
