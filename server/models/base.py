from typing import Literal, List, Optional

from pydantic import BaseModel


class Message(BaseModel):
    role: Literal['assistant']
    content: str


class Token(BaseModel):
    message: Message


class TranscriptionSegment(BaseModel):
    words: List[str]
    complete: bool
    final: Optional[bool] = False
    id: Optional[int] = None
    start: Optional[float] = None
    samples: Optional[int] = None
