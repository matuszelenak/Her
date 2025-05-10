import asyncio
import os
import re
from datetime import datetime
from typing import Tuple, Literal, Union, AsyncGenerator, Iterable

from bs4 import BeautifulSoup
from markdown import markdown
from openai import AsyncClient
from openai.types.chat import ChatCompletionMessageParam
from openai.types.chat.chat_completion_chunk import Choice

from models.base import Token, Message
from models.sent_events import WsSendTokenEvent
from tasks.tts import tts_task
from utils.log import get_logger
from utils.sanitization import clean_text_for_tts
from models.session import Session

logger = get_logger(__name__)

TokenTuple = Tuple[Literal['token'], Choice]
SentenceTuple = Tuple[Literal['sentence'], str]


open_api_url = os.environ.get('OPENAI_API_URL')
client = AsyncClient(base_url=open_api_url, api_key='whatever')


async def llm_query_task(session: Session, prompt: str):
    try:
        await session.append_message({
            'role': 'user',
            'content': prompt
        })

        llm_response_queue = asyncio.Queue()
        session.tts_task = asyncio.create_task(tts_task(session, llm_response_queue))

        complete_response = ""

        async for resp_type, content in generate_llm_response(session.chat.messages):
            if resp_type == 'token':
                content: Choice

                complete_response += content.delta.content

                await session.send_event(WsSendTokenEvent(
                    token=Token(
                        message=Message(
                            role='assistant',
                            content=content.delta.content
                        )
                    )
                ))

            elif resp_type == 'sentence':
                content: str

                cleaned = clean_text_for_tts(content)

                if len(cleaned.strip()) > 2:
                    logger.debug(f'Adding to TTS queue {cleaned}')
                    await llm_response_queue.put(cleaned)

        await session.append_message({
            'role': 'assistant',
            'content': ''.join(complete_response)
        })

        # Notify frontend of the end of generation
        await session.send_event(WsSendTokenEvent(
            token=None
        ))

        session.last_interaction = datetime.now()

        await llm_response_queue.put(None)

    except asyncio.CancelledError:
        logger.debug('LLM task cancelled')
    except Exception as e:
        logger.error('Error in LLM task', exc_info=True)
        logger.error(str(e))


async def generate_llm_response(messages: Iterable[ChatCompletionMessageParam]) -> AsyncGenerator[Union[TokenTuple, SentenceTuple], None]:
    sentence_buffer = ""
    async for part in await client.chat.completions.create(
            model='anything',
            messages=messages,
            stream=True
    ):
        msg = part.choices[0].delta.content

        yield "token", part.choices[0]

        msg = re.sub(r'\n+', '\n', msg)

        for char in msg:
            sentence_buffer += char
            if char in ('.', ':', '\n', '?', '!'):
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
