from typing import Union, Literal, Any

from pydantic import BaseModel, Field


class WsReceiveSamplesEvent(BaseModel):
    type: Literal['samples']
    data: str


class WsReceiveSpeechEndEvent(BaseModel):
    type: Literal['speech_end']


class WsReceiveSpeechPromptEvent(BaseModel):
    type: Literal['speech_prompt_end']


class WsReceiveTextPrompt(BaseModel):
    type: Literal['text_prompt']
    prompt: str


class WsReceiveAgentSpeechEnd(BaseModel):
    type: Literal['finished_speaking']


class WsReceiveConfigChange(BaseModel):
    type: Literal['config_change']
    path: str
    value: Any


class WsReceiveEvent(BaseModel):
    event: Union[
        WsReceiveSamplesEvent,
        WsReceiveSpeechEndEvent,
        WsReceiveSpeechPromptEvent,
        WsReceiveTextPrompt,
        WsReceiveAgentSpeechEnd,
        WsReceiveConfigChange
    ] = Field(discriminator='type')
