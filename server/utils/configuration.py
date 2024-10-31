from typing import Literal, List

from pydantic import BaseModel


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
    speech_submit_delay_ms: int


class SessionConfig(BaseModel):
    ollama: OllamaConfig
    whisper: WhisperConfig
    xtts: XTTSConfig
    app: AppConfig


def get_default_config() -> SessionConfig:
    with open('./config.json', 'r') as f:
        return SessionConfig.model_validate_json(f.read())


def set_config_from_event(config, field, value):
    curr = config
    spl = field.split('.')
    for part in spl[:-1]:
        curr = getattr(curr, part)

    setattr(curr, spl[-1], value)
