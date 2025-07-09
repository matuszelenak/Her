import datetime
from typing import List

import logfire
from fastapi import FastAPI
from openai.types.chat.chat_completion_chunk import ChatCompletionChunk, Choice as ChunkChoice, ChoiceDelta
from pydantic import BaseModel
from pydantic_ai.messages import ModelRequest, UserPromptPart, ModelResponse, TextPart
from starlette.middleware.cors import CORSMiddleware
from starlette.responses import StreamingResponse

from agents import gen

logfire.configure(send_to_logfire="if-token-present")
logfire.instrument_openai()

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get('/')
async def health():
    return {'status': 'healthy'}


class CompletionRequest(BaseModel):
    class Message(BaseModel):
        role: str
        content: str

    messages: List[Message]
    model: str
    stream: bool = False


def construct_completion_chunk(content):
    return ChatCompletionChunk(
        id="chatcmpl-4247",
        choices=[ChunkChoice(
            delta=ChoiceDelta(
                content=content,
                role='assistant'
            ),
            index=0
        )],
        created=int(datetime.datetime.now().timestamp()),
        model='default',
        object='chat.completion.chunk'
    )


@app.post('/v1/chat/completions')
async def chat(request: CompletionRequest):
    message_history = [
        ModelRequest(parts=[UserPromptPart(content=msg.content)])
        if msg.role == 'user' else
        ModelResponse(parts=[TextPart(content=msg.content)])
        for msg in request.messages[:-1]
    ]

    prompt = request.messages[-1].content

    async def chunk_generator():
        with logfire.span('User request {msg=} at {ts=}', msg=prompt, ts=datetime.datetime.now()):
            async for token in gen(prompt, message_history):
                completion_chunk = construct_completion_chunk(token)
                yield f"data: {completion_chunk.model_dump_json()}\n\n"

        completion_chunk = construct_completion_chunk(' ')
        completion_chunk.choices[0].finish_reason = 'stop'

        yield f"data: {completion_chunk.model_dump_json()}\n\n"


    return StreamingResponse(
        chunk_generator(),
        media_type="text/event-stream"
    )
