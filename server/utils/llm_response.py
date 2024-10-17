import asyncio
import json
import logging
import re

from bs4 import BeautifulSoup
from markdown import markdown

from utils.tools import tool_call_regex


logger = logging.getLogger(__name__)


async def get_sentences(token_generator, token_handler):
    llm_response = []

    sentence_buffer = ""
    token_id = 0
    async for part in await token_generator:
        msg = part['message']['content']

        # logger.warning(f'LLM: {msg}')

        await token_handler(part, token_id)

        llm_response.append(msg)

        msg = re.sub(r'\n+', '\n', msg)

        while '\n' in msg:
            split_msg = msg.split('\n')

            sentence = sentence_buffer + split_msg[0]

            if re.match(tool_call_regex, sentence):
                yield 'tool_call', json.loads(sentence)
            else:
                yield 'interactive', sentence

            sentence_buffer = ""
            msg = '\n'.join(split_msg[1:])

        sentence_buffer += msg

        token_id += 1

    if sentence_buffer:
        if re.match(tool_call_regex, sentence_buffer):
            yield 'tool_call', json.loads(sentence_buffer)
        else:
            yield 'interactive', sentence_buffer

    await asyncio.sleep(0.2)


async def strip_markdown(sentence):
    html = markdown(sentence)

    html = re.sub(r'<pre>(.*?)</pre>', ' ', html)
    html = re.sub(r'<code>(.*?)</code >', ' ', html)

    soup = BeautifulSoup(html, "html.parser")
    text = ''.join(soup.findAll(text=True))

    return text
