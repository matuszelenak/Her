import logging
import re
from typing import Tuple, Literal, Union, AsyncGenerator

from bs4 import BeautifulSoup
from markdown import markdown
from openai.types.chat import ChatCompletionChunk
from openai.types.chat.chat_completion_chunk import Choice, ChoiceDeltaToolCall

from providers import providers
from utils.session import Session

logger = logging.getLogger(__name__)


TokenTuple = Tuple[Literal['token'], Choice]
SentenceTuple = Tuple[Literal['sentence'], str]
ToolCallTuple = Tuple[Literal['tool_call'], ChoiceDeltaToolCall]


async def generate_llm_response(session: Session, prompt: str) -> AsyncGenerator[Union[TokenTuple, SentenceTuple, ToolCallTuple], None]:
    llm = providers['llm']

    sentence_buffer = ""

    part: ChatCompletionChunk
    async for part in await llm.chat.completions.create(
        model=session.chat.config.llm.model,
        messages=[{
            'role': 'system',
            'content': session.chat.config.llm.system_prompt
        }] + session.chat.messages,
        stream=True,
        temperature=session.chat.config.llm.temperature
    ):

        msg = part.choices[0].delta.content

        if len(part.choices[0].delta.tool_calls or []) > 0:
            for call in part.choices[0].delta.tool_calls:
                logger.warning(f'{call}')
                yield 'tool_call', call

            break

        yield 'token', part.choices[0]

        msg = re.sub(r'\n+', '\n', msg)

        for char in msg:
            sentence_buffer += char
            if char in ('.', ':', '\n'):
                yield 'sentence', sentence_buffer.strip() + " "

                sentence_buffer = ""

    if sentence_buffer:
        yield 'sentence', sentence_buffer



def strip_markdown(sentence: str):
    html = markdown(sentence)

    html = re.sub(r'<pre>(.*?)</pre>', ' ', html)
    html = re.sub(r'<code>(.*?)</code >', ' ', html)

    soup = BeautifulSoup(html, "html.parser")
    text = ''.join(soup.findAll(text=True))

    return text
