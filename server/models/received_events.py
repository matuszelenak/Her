from typing import Union, Literal

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



WsReceiveEventUnion = Union[
    WsReceiveSamplesEvent,
    WsReceiveSpeechEndEvent,
    WsReceiveSpeechPromptEvent,
    WsReceiveTextPrompt,
    WsReceiveAgentSpeechEnd
]


class WsReceiveEvent(BaseModel):
    event: Union[
        WsReceiveSamplesEvent,
        WsReceiveSpeechEndEvent,
        WsReceiveSpeechPromptEvent,
        WsReceiveTextPrompt,
        WsReceiveAgentSpeechEnd
    ] = Field(discriminator='type')
