import json
import re

from utils.tools import tool_call_regex


async def get_sentences(token_generator, token_handler):
    llm_response = []

    sentence_buffer = ""
    async for part in await token_generator:
        msg = part['message']['content']

        await token_handler(msg)

        llm_response.append(msg)

        msg = re.sub(r'\n+', '\n', msg)

        while '\n' in msg:
            split_msg = msg.split('\n')

            sentence = sentence_buffer + split_msg[0]
            print(sentence)

            if re.match(tool_call_regex, sentence):
                yield 'tool_call', json.loads(sentence)
            else:
                yield 'interactive', sentence

            sentence_buffer = ""
            msg = '\n'.join(split_msg[1:])

        sentence_buffer += msg

    if sentence_buffer:
        print(sentence_buffer)
        if re.match(tool_call_regex, sentence_buffer):
            yield 'tool_call', json.loads(sentence_buffer)
        else:
            yield 'interactive', sentence_buffer

    await token_handler(None)