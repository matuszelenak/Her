import datetime
import logging
from typing import List

import logfire
from fastapi import FastAPI
from openai.types import CompletionUsage
from openai.types.chat import ChatCompletion, ChatCompletionMessage
from openai.types.chat.chat_completion import Choice
from openai.types.chat.chat_completion_chunk import ChatCompletionChunk, Choice as ChunkChoice, ChoiceDelta
from pydantic import BaseModel
from pydantic_ai.messages import ModelRequest, UserPromptPart, ModelResponse, TextPart, \
    ModelMessage
from starlette.middleware.cors import CORSMiddleware
from starlette.responses import Response, StreamingResponse

from agents import supervisor_agent, gen
from utils import get_logger

logger = get_logger(__name__, logging.DEBUG)

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


async def streaming_response(prompt: str, message_history: List[ModelMessage]) -> StreamingResponse:
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
            model='whatever',
            object='chat.completion.chunk'
        )

    async def chunk_generator():
        async for token in gen(prompt):
            completion_chunk = construct_completion_chunk(token)
            yield f"data: {completion_chunk.model_dump_json()}\n\n"

        completion_chunk = construct_completion_chunk(' ')
        completion_chunk.choices[0].finish_reason = 'stop'

        yield f"data: {completion_chunk.model_dump_json()}\n\n"

    return StreamingResponse(
        chunk_generator(),
        media_type="text/event-stream"
    )


async def regular_response(prompt: str, message_history: List[ModelMessage]) -> Response:
    agent_response = await supervisor_agent.run(
        user_prompt=prompt,
        message_history=message_history
    )
    usage = agent_response.usage()

    completion = ChatCompletion(
        id="chatcmpl-4247",
        choices=[Choice(
            message=ChatCompletionMessage(
                content=agent_response.data,
                role='assistant'
            ),
            index=0,
            finish_reason="stop"
        )],
        created=int(datetime.datetime.now().timestamp()),
        model='whatever',
        object="chat.completion",
        usage=CompletionUsage(
            prompt_tokens=usage.request_tokens,
            completion_tokens=usage.response_tokens,
            total_tokens=usage.total_tokens
        )
    )

    return Response(content=completion.model_dump_json(), media_type='application/json')


@app.post("/v1/chat/completions", response_class=Response)
async def completions(request: CompletionRequest):
    message_history = [
        ModelRequest(parts=[UserPromptPart(content=msg.content)])
        if msg.role == 'user' else
        ModelResponse(parts=[TextPart(content=msg.content)])
        for msg in request.messages[:-1]
    ]

    with logfire.span('User request {msg=} at {ts=}', msg=request.messages[-1].content, ts=datetime.datetime.now()):
        if request.stream:
            return await streaming_response(request.messages[-1].content, message_history)
        else:
            return await regular_response(request.messages[-1].content, message_history)


@app.get('/v1/models')
async def get_models():
    return {
        "object": "list",
        "data": [
            {
                "id": "Qwen/Qwen2.5-32B-Instruct-AWQ",
                "object": "model",
                "created": 1741783912,
                "owned_by": "vllm",
                "root": "Qwen/Qwen2.5-32B-Instruct-AWQ",
                "parent": None,
                "max_model_len": 32768,
            }
        ]
    }
