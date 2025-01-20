import logging
from datetime import datetime, timedelta

from utils.constants import OLLAMA_API_URL
from ollama import AsyncClient

CLEANER_SYSTEM = """
You are a large language model. Your task is to validate and sanitize the transcription of speech to text before it reaches another AI assistant. 
You will be given the last few exchanges between the user and the assistant. The messages are going to be prefixed by either "USER:" or "ASSISTANT:". 
Your task is to determine, if the last user message fits into the ongoing conversation.
If the message fits, output TRUE. If it does not, output FALSE. 
Never output anything else than these two words.
The very first message is likely to just be a greeting, so accept any.
Remember, I am not talking to you, you are simply validating what I send you.
"""

logger = logging.getLogger(__name__)


async def is_prompt_valid(session, prompt, message_history):
    wtf = '\n'.join(
        [f'{"USER: " if message["role"] == "user" else "ASSISTANT: "}{message["content"].replace("\n", "")}'
         for message in message_history[-5:]]
    )
    wtf = f'{wtf}\nUSER: {prompt}'
    llm_response = await AsyncClient(OLLAMA_API_URL).chat(
        model=session.chat.config.ollama.model,
        messages=[
            {
                'role': 'system',
                'content': CLEANER_SYSTEM
            },
            {
                'role': 'user',
                'content': wtf
            }
        ]
    )
    passed_validation = llm_response['message']['content'].strip()
    return passed_validation == 'TRUE'


async def should_agent_respond(session):
    if session.last_interaction is not None and (datetime.now() - session.last_interaction) < timedelta(
            milliseconds=session.chat.config.app.inactivity_timeout_ms):
        return True

    client = AsyncClient(OLLAMA_API_URL)

    response = await client.chat(
        model='qwen2.5:1.5b-instruct-q8_0',
        messages=[{
            'role': 'user',
            'content': f'Output YES if the following text is addressed to a person called Aloy and NO if it is not. The text is: {session.prompt}'
        }],
        options=dict(
            temperature=0,
        )
    )

    logger.warning(f'Validator says {response['message']['content']}')

    return response['message']['content'].strip() == 'YES'
