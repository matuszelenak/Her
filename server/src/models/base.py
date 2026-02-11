from typing import Literal, List, Optional

from pydantic import BaseModel


class Message(BaseModel):
    role: Literal['assistant']
    content: str


class Token(BaseModel):
    message: Message


class TranscriptionSegment(BaseModel):
    text: str
    is_final: bool = False
