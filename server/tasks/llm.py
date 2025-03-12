import asyncio
import os
import re
from datetime import datetime
from typing import Tuple, Literal, Union, AsyncGenerator, Iterable

from bs4 import BeautifulSoup
from markdown import markdown
from openai import AsyncClient
from openai.types.chat import ChatCompletionChunk, ChatCompletionMessageParam
from openai.types.chat.chat_completion_chunk import Choice

from tasks.tts import tts_task
from utils.log import get_logger
from utils.session import Session

logger = get_logger(__name__)

TokenTuple = Tuple[Literal['token'], Choice]
SentenceTuple = Tuple[Literal['sentence'], str]


async def llm_query_task(session: Session, prompt: str):
    try:
        await session.append_message({
            'role': 'user',
            'content': prompt
        })

        llm_response_queue = asyncio.Queue()
        if session.speech_enabled:
            session.tts_task = asyncio.create_task(tts_task(session, llm_response_queue))

        printable_response = ""

        async for resp_type, content in generate_llm_response(session.chat.messages):
            if resp_type == 'token':
                content: Choice
                await session.client_socket.send_json({
                    'type': 'token',
                    'token': {
                        'message': {
                            'role': content.delta.role,
                            'content': content.delta.content
                        },
                        'done': content.finish_reason is not None
                    }
                })

            elif resp_type == 'sentence':
                cleaned = strip_markdown(content)

                logger.debug(f'Adding to TTS queue {cleaned}')
                if session.speech_enabled:
                    await llm_response_queue.put(cleaned)

                printable_response += content

        await session.append_message({
            'role': 'assistant',
            'content': ''.join(printable_response)
        })

        session.last_interaction = datetime.now()

        if session.speech_enabled:
            await llm_response_queue.put(None)

    except asyncio.CancelledError:
        logger.debug('LLM task cancelled')
    except Exception as e:
        logger.error('Error in LLM task', exc_info=True)
        logger.error(str(e))


async def generate_llm_response(messages: Iterable[ChatCompletionMessageParam]) -> AsyncGenerator[Union[TokenTuple, SentenceTuple], None]:
    sentence_buffer = ""

    open_api_url = os.environ.get('OPENAI_API_URL')
    client = AsyncClient(base_url=open_api_url, api_key='whatever')

    part: ChatCompletionChunk
    async for part in await client.chat.completions.create(
            model='anything',
            messages=messages,
            stream=True
    ):

        msg = part.choices[0].delta.content

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
