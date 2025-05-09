import argparse
import asyncio
import os
from typing import AsyncGenerator, List

from pydantic_ai.models.openai import OpenAIModel
from pydantic_ai.providers.openai import OpenAIProvider
from pydantic_ai import Agent, RunContext, Tool
from pydantic_ai.common_tools.tavily import TavilySearchTool
from pydantic_ai.messages import TextPartDelta, PartDeltaEvent, ModelMessage
from tavily import AsyncTavilyClient

from log_utils import get_logger
from tools.spotify import play_song, stop_playback, change_volume, next_song, previous_song

logger = get_logger(__name__)

gpt_model = OpenAIModel(
    'cognitivecomputations/Qwen3-30B-A3B-AWQ',
    provider=OpenAIProvider(api_key='none', base_url='http://10.0.0.2:11433/v1')
)

knowledge_agent = Agent(
    gpt_model,
    system_prompt="You are a conversational agent that answers questions about the world."
                  "For anything but the most obvious questions use the web search tool.",
    model_settings={
        'temperature': 0.5
    }
)


@knowledge_agent.tool_plain
async def web_search_tool(query: str):
    """Internet search tool that searches the web for the given query and returns the results.

    Args:
        query: The search query
    """

    logger.debug(f'Search {query}')
    api_key = os.environ.get('TAVILY_API_TOKEN')
    tool = TavilySearchTool(client=AsyncTavilyClient(api_key))

    result = await tool(query)
    return result


home_automation_agent = Agent(
    gpt_model,
    system_prompt="""
    You are a home assistant agent, capable of calling tools that manage the smart devices in the users home
    """,
    tools=[
        Tool(play_song, takes_ctx=False),
        Tool(previous_song, takes_ctx=False),
        Tool(next_song, takes_ctx=False),
        Tool(stop_playback, takes_ctx=False),
        Tool(change_volume, takes_ctx=False)
    ]
)

supervisor_agent = Agent(
    gpt_model,
    system_prompt="""
    You are a cheery conversation agent with the personality of a cute anime waifu.
    You have access to tools that you can call if you decide it is necessary for handling the user's request.
    For user queries regarding world knowledge, call the knowledge agent tool.
    To handle requests regarding house actions, like playing music, setting the temperature etc, call the home automation agent and then just confirm that the action has been performed.
    If there is not a need for a tool call, just converse with the user normally.
    Do not use emojis in your response.
    """
)


@supervisor_agent.tool
async def knowledge_agent_tool(ctx: RunContext[None], question: str) -> AsyncGenerator[str, None]:
    """
    A knowledge agent handling requests concerning general knowledge and searchable information

    Args:
        ctx: RunContext
        question: the users message
    """
    logger.debug(f'Knowledge {question}')
    result = await knowledge_agent.run(question)
    return result.data


@supervisor_agent.tool_plain
async def home_automation_agent_tool(request: str):
    """
    An agent for handling users request that trigger actions regarding the devices in his home.
    Currently supported is setting the temperature and playing music

    Args:
        request: users request
    """
    logger.debug(f'Automation {request}')
    result = await home_automation_agent.run(request)
    return result.output


@home_automation_agent.tool_plain
async def set_target_temperature(temperature: float):
    """
    A tool to set the thermostat target temperature

    Args:
        temperature: Temperature in degrees Celsius
    """
    logger.debug(f'Temperature {temperature}')
    return 'OK'


async def gen(prompt: str, message_history: List[ModelMessage]) -> AsyncGenerator[str, None]:
    async with supervisor_agent.iter(prompt, message_history=message_history) as run:
        async for node in run:
            if Agent.is_model_request_node(node):
                async with node.stream(run.ctx) as request_stream:
                    async for event in request_stream:
                        if isinstance(event, PartDeltaEvent) and isinstance(event.delta, TextPartDelta):
                            yield event.delta.content_delta


async def main(prompt):
    async for token in gen(prompt, []):
        print(token, end='', flush=True)
    print()


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Accept one command line argument string.")

    parser.add_argument("-p", type=str, help="Prompt")
    args = parser.parse_args()
    asyncio.run(main(args.p))
