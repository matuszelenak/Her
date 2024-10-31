import json
import logging
import re

from bs4 import BeautifulSoup
from markdown import markdown
from ollama import AsyncClient

import utils.tools as tools
from utils.constants import OLLAMA_API_URL
from utils.session import Session

logger = logging.getLogger(__name__)


def parse_llama_tool_call(s):
    split_call = re.split(re.compile(r'}\s+\{'), s)

    if len(split_call) >= 2:
        split_call[0] = split_call[0] + '}'
        split_call[-1] = '{' + split_call[-1]

        for i in range(1, len(split_call) - 1):
            split_call[i] = '{' + split_call[i] + '}'

    return [json.loads(c) for c in split_call]


def parse_mistral_tool_call(s: str):
    calls = re.sub(r'^\[TOOL_CALLS]', '', s)
    calls = json.loads(calls)

    for call in calls:
        call['parameters'] = call['arguments']
        del call['arguments']

    return calls


TOOL_CALL_PATTERNS = [
    (re.compile(r'^\{.*'), parse_llama_tool_call),
    (re.compile(r'^\[TOOL_CALLS].*'), parse_mistral_tool_call)
]


async def generate_llm_response(session: Session, prompt: str):
    client = AsyncClient(OLLAMA_API_URL)

    is_tool_call = None
    tool_call_parser = None

    llm_response = []
    sentence_buffer = ""
    async for part in await client.chat(
            model=session.config.ollama.model,
            messages=[{
                'role': 'system',
                'content': session.config.ollama.system_prompt
            }] + session.chat.messages,
            stream=True,
            options=dict(
                num_ctx=session.config.ollama.ctx_length,
                repeat_penalty=session.config.ollama.repeat_penalty,
                temperature=session.config.ollama.temperature,
            ),
            tools=[
                getattr(tools, tool) for tool in session.config.ollama.tools
            ],
    ):
        msg = part['message']['content']
        llm_response.append(msg)

        if is_tool_call is None:
            for regex, parser in TOOL_CALL_PATTERNS:
                if re.match(regex, msg):
                    is_tool_call = True
                    tool_call_parser = parser
                    break
                else:
                    is_tool_call = False

        if not is_tool_call:
            yield 'token', part

            msg = re.sub(r'\n+', '\n', msg)

            while '\n' in msg:
                split_msg = msg.split('\n')

                sentence = sentence_buffer + split_msg[0]

                yield 'sentence', sentence

                sentence_buffer = ""
                msg = '\n'.join(split_msg[1:])

            sentence_buffer += msg

    if sentence_buffer:
        yield 'sentence', sentence_buffer

    if is_tool_call:
        llm_response = ''.join(llm_response)

        yield 'tool_call', tool_call_parser(llm_response)


async def strip_markdown(sentence):
    html = markdown(sentence)

    html = re.sub(r'<pre>(.*?)</pre>', ' ', html)
    html = re.sub(r'<code>(.*?)</code >', ' ', html)

    soup = BeautifulSoup(html, "html.parser")
    text = ''.join(soup.findAll(text=True))

    return text
