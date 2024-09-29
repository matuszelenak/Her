import asyncio
import datetime
import logging

from ollama import AsyncClient

from components.stt import stt_sender
from utils.constants import OLLAMA_API_URL
from utils.llm_response import get_sentences, strip_markdown
from utils.session import Session
from utils.tools import get_ip_address

logger = logging.getLogger(__name__)


tools = {
    'get_ip_address': get_ip_address
}



async def llm_submitter(session: Session):
    message_history = []
    while True:
        if session.prompt:
            prompt, prompt_time, cutoff = session.prompt
            if prompt_time < datetime.datetime.now() - datetime.timedelta(
                    milliseconds=session.config.app.speech_submit_delay_ms
            ):
                session.prompt = None
                session.stt_task.cancel()
                session.stt_task = asyncio.create_task(stt_sender(session))

                #
                # if session.config.app.prevalidate_prompt and not await is_prompt_valid(session, prompt, message_history):
                #     continue

                message_history.append({
                    'role': 'user',
                    'content': prompt
                })

                client = AsyncClient(OLLAMA_API_URL)

                async def send_token(token):
                    await session.client_socket.send_json({
                        'type': 'token',
                        'token': token
                    })

                while True:
                    tool_answers = []
                    printable_response = ""
                    async for sentence_type, content in get_sentences(
                            client.chat(
                                model=session.config.ollama.model,
                                messages=[{'role': 'system',
                                           'content': session.config.ollama.system_prompt}] + message_history,
                                stream=True,
                                # tools=[
                                #     get_ip_address_def
                                # ],
                            ),
                            token_handler=send_token
                    ):
                        if sentence_type == 'interactive':
                            cleaned = await strip_markdown(content)

                            logger.warning(f'Adding to TTS queue {cleaned}')
                            await session.response_tokens_queue.put(cleaned)
                            printable_response += content
                        else:
                            fn = tools.get(content['name'])
                            if fn:
                                parameters = content['parameters']
                                tool_answers.append(fn(**parameters))

                    if len(tool_answers) > 0:
                        for answer in tool_answers:
                            message_history.append({
                                'role': 'tool',
                                'content': str(answer)
                            })
                    else:
                        message_history.append({
                            'role': 'assistant',
                            'content': ''.join(printable_response)
                        })
                        break

        await asyncio.sleep(0.1)
