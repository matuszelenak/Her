import logging
import re
from typing import Tuple, Literal, Union, AsyncGenerator

from bs4 import BeautifulSoup
from markdown import markdown
from ollama import AsyncClient, Message, ChatResponse

import utils.tools as tools
from utils.constants import OLLAMA_API_URL
from utils.session import Session

logger = logging.getLogger(__name__)


TokenTuple = Tuple[Literal['token'], ChatResponse]
SentenceTuple = Tuple[Literal['sentence'], str]
ToolCallTuple = Tuple[Literal['tool_call'], Message.ToolCall]


async def generate_llm_response(session: Session, prompt: str) -> AsyncGenerator[Union[TokenTuple, SentenceTuple, ToolCallTuple], None]:
    client = AsyncClient(OLLAMA_API_URL)

    llm_response = []
    sentence_buffer = ""

    part: ChatResponse
    async for part in await client.chat(
            model=session.chat.config.ollama.model,
            messages=[{
                'role': 'system',
                'content': session.chat.config.ollama.system_prompt
            }] + session.chat.messages,
            stream=True,
            options=dict(
                num_ctx=session.chat.config.ollama.ctx_length,
                repeat_penalty=session.chat.config.ollama.repeat_penalty,
                temperature=session.chat.config.ollama.temperature,
            )#,
            # tools=[
            #     getattr(tools, tool) for tool in session.chat.config.ollama.tools
            # ],
    ):
        msg = part.message.content
        llm_response.append(msg)

        if len(part.message.tool_calls or []) > 0:
            for call in part.message.tool_calls:
                logger.warning(f'{call}')
                yield 'tool_call', call

            break

        yield 'token', part

        msg = re.sub(r'\n+', '\n', msg)

        for char in msg:
            sentence_buffer += char
            if char in ('.', ':', '\n'):
                yield 'sentence', sentence_buffer.strip() + " "

                sentence_buffer = ""

    if sentence_buffer:
        yield 'sentence', sentence_buffer



async def strip_markdown(sentence):
    html = markdown(sentence)

    html = re.sub(r'<pre>(.*?)</pre>', ' ', html)
    html = re.sub(r'<code>(.*?)</code >', ' ', html)

    soup = BeautifulSoup(html, "html.parser")
    text = ''.join(soup.findAll(text=True))

    return text
