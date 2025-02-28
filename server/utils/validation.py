import logging
from datetime import datetime, timedelta

from providers import providers, OpenAIProvider

logger = logging.getLogger(__name__)


async def should_agent_respond(session):
    llm: OpenAIProvider = providers['llm']
    if session.last_interaction is not None and (datetime.now() - session.last_interaction) < timedelta(
            milliseconds=session.chat.config.app.inactivity_timeout_ms):
        return True
    response = await llm.chat.completions.create(
        model='qwen2.5:1.5b-instruct-q8_0',
        messages=[{
            'role': 'user',
            'content': f'Output YES if the following text is addressed to a person called Lucy and NO if it is not. The text is: {session.prompt}'
        }],
        temperature=0
    )

    logger.warning(f'Validator says {response.choices[0].message.content}')

    return response.choices[0].message.content.strip() == 'YES'
