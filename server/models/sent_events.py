from typing import Literal, Union

from pydantic import BaseModel

from models.base import Token, TranscriptionSegment
from models.configuration import SessionConfig


class WsManualPromptEvent(BaseModel):
    text: str
    type: Literal['manual_prompt'] = 'manual_prompt'


class WsSendTokenEvent(BaseModel):
    token: Token | None
    type: Literal['token'] = 'token'


class WsSendTranscriptionEvent(BaseModel):
    segment: TranscriptionSegment
    type: Literal['user_speech_transcription'] = 'user_speech_transcription'


class WsSendAssistantSpeechStartEvent(BaseModel):
    type: Literal['assistant_speech_start'] = 'assistant_speech_start'


class WsSendSpeechEvent(BaseModel):
    filename: str
    order: int
    text: str
    type: Literal['speech_id'] = 'speech_id'


class WsSendSpeechSamplesEvent(BaseModel):
    samples: str
    type: Literal['speech_samples'] = 'speech_samples'


class WsSendConfigurationEvent(BaseModel):
    configuration: SessionConfig
    type: Literal['configuration'] = 'configuration'

    model_config = dict(arbitrary_types_allowed=True)


WsSendEvent = Union[
    WsManualPromptEvent,
    WsSendTokenEvent,
    WsSendTranscriptionEvent,
    WsSendAssistantSpeechStartEvent,
    WsSendSpeechEvent,
    WsSendSpeechSamplesEvent,
    WsSendConfigurationEvent
]
