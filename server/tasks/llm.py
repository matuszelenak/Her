import asyncio
import logging
from datetime import datetime

from openai.types.chat.chat_completion_chunk import Choice, ChoiceDeltaToolCall

from tasks.tts import tts_task
from utils.llm_response import generate_llm_response, strip_markdown
from utils.session import Session
from utils.tools import get_ip_address, get_current_moon_phase

logger = logging.getLogger(__name__)
logger.setLevel('INFO')


tools = {
    'get_ip_address': get_ip_address,
    'get_current_moon_phase': get_current_moon_phase
}


async def llm_query_task(session: Session, prompt: str):
    try:

        await session.append_message({
            'role': 'user',
            'content': prompt
        })

        llm_response_queue = asyncio.Queue()
        if session.speech_enabled:
            session.tts_task = asyncio.create_task(tts_task(session, llm_response_queue))

        while True:
            tool_answers = []
            printable_response = ""

            async for resp_type, content in generate_llm_response(session, prompt):
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
                    cleaned = await strip_markdown(content)

                    logger.info(f'Adding to TTS queue {cleaned}')
                    if session.speech_enabled:
                        await llm_response_queue.put(cleaned)

                    printable_response += content

                elif resp_type == 'tool_call':
                    content: ChoiceDeltaToolCall
                    fn = tools.get(content.function.name)
                    if fn:
                        tool_answers.append(fn(**content.function.arguments))

            if len(tool_answers) > 0:
                for answer in tool_answers:
                    await session.append_message({
                        'role': 'tool',
                        'content': str(answer)
                    })
            else:
                await session.append_message({
                    'role': 'assistant',
                    'content': ''.join(printable_response)
                })
                break

        session.last_interaction = datetime.now()

        if session.speech_enabled:
            await llm_response_queue.put(None)

    except asyncio.CancelledError:
        logger.warning('LLM task cancelled')
    except Exception as e:
        logger.error('Error in LLM task', exc_info=True)
        logger.error(str(e))
