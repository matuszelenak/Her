import asyncio
import logging

from ollama import AsyncClient

from tasks.tts import tts_task
from utils.constants import OLLAMA_API_URL
from utils.llm_response import get_sentences, strip_markdown
from utils.session import Session
from utils.tools import get_ip_address

logger = logging.getLogger(__name__)


tools = {
    'get_ip_address': get_ip_address
}


async def llm_query_task(session: Session, prompt: str):
    try:
        session.message_history.append({
            'role': 'user',
            'content': prompt
        })

        client = AsyncClient(OLLAMA_API_URL)

        async def send_token(token, token_id):
            await session.client_socket.send_json({
                'type': 'token',
                'token': token,
                'id': token_id
            })

        llm_response_queue = asyncio.Queue()
        if session.speech_enabled:
            session.tts_task = asyncio.create_task(tts_task(session, llm_response_queue))

        while True:
            tool_answers = []
            printable_response = ""
            async for sentence_type, content in get_sentences(
                    client.chat(
                        model=session.config.ollama.model,
                        messages=[{
                            'role': 'system',
                            'content': session.config.ollama.system_prompt
                        }] + session.message_history,
                        stream=True,
                        # tools=[
                        #     get_ip_address_def
                        # ],
                        options=dict(
                            num_ctx=session.config.ollama.ctx_length,
                            repeat_penalty=session.config.ollama.repeat_penalty,
                            temperature=session.config.ollama.temperature,
                        )
                    ),
                    token_handler=send_token
            ):
                logger.info(f'LLM Response: {content}')
                if sentence_type == 'interactive':
                    cleaned = await strip_markdown(content)

                    logger.info(f'Adding to TTS queue {cleaned}')
                    if session.speech_enabled:
                        await llm_response_queue.put(cleaned)

                    printable_response += content
                else:
                    fn = tools.get(content['name'])
                    if fn:
                        parameters = content['parameters']
                        tool_answers.append(fn(**parameters))

            if len(tool_answers) > 0:
                for answer in tool_answers:
                    session.message_history.append({
                        'role': 'tool',
                        'content': str(answer)
                    })
            else:
                session.message_history.append({
                    'role': 'assistant',
                    'content': ''.join(printable_response)
                })
                break

        if session.speech_enabled:
            await llm_response_queue.put(None)

    except asyncio.CancelledError:
        logger.warning('LLM task cancelled')
    except Exception as e:
        logger.error('Error in LLM task')
        logger.error(str(e))
