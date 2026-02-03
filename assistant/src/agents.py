import argparse
import asyncio
from typing import AsyncGenerator, List, Union

import logfire
from dotenv import load_dotenv
from pydantic_ai import Agent, RunContext
from pydantic_ai.common_tools.tavily import TavilySearchTool

from pydantic_ai.models.openai import OpenAIModel
from pydantic_ai.providers.openai import OpenAIProvider
from pydantic_ai import Agent, RunContext, Tool
from pydantic_ai.common_tools.tavily import TavilySearchTool
from pydantic_ai.messages import TextPartDelta, PartDeltaEvent, ThinkingPartDelta, ModelMessage, FunctionToolCallEvent, \
    PartStartEvent, \
    ToolCallPartDelta, FinalResultEvent, FunctionToolResultEvent, ToolCallPart, ToolReturnPart, TextPart, \
    ModelRequestPart, ModelResponsePart
from pydantic_ai.models.openai import OpenAIModel
from pydantic_ai.providers.openai import OpenAIProvider

from src.settings import config

load_dotenv()

if __name__ == '__main__':
    logfire.configure(send_to_logfire="if-token-present")
    logfire.instrument_openai()

gpt_model = OpenAIModel(
    config.OPENAI_MODEL,
    provider=OpenAIProvider(api_key='none', base_url=config.OPENAI_API_URL),
)

# knowledge_agent = Agent(
#     gpt_model,
#     instructions="You are a conversational agent that answers questions about the world."
#                   "For anything but the most obvious questions use the web search tool./no_think",
# )
#
#
# @knowledge_agent.tool_plain
# async def web_search_tool(query: str):
#     """Internet search tool that searches the web for the given query and returns the results.
#
#     Args:
#         query: The search query
#     """
#
#     logfire.debug(f'Search {query}')
#     tool = TavilySearchTool(client=AsyncTavilyClient(config.TAVILY_API_TOKEN))
#
#     result = await tool(query)
#     return result


supervisor_agent = Agent(
    gpt_model,
    instructions="""
    You are a helpful AI assistant used for voice conversations with a user.
    
    You have access to tools that you can call if you decide it is necessary for handling the user's request.
    If there is not a need for a tool call, just converse with the user normally.
    
    Keep your response concise and in a casual, conversational tone.
    Format your response so that it can be directly fed to a text-to-speech software: meaning there should be no markdown or other formatting, the numbers should be written out in word form (not as digits) and do not use emojis!
    /no_think
    """,
    # mcp_servers=[MCPServerStreamableHTTP(url='http://192.168.1.87:8080/mcp/')]
)


# @supervisor_agent.tool
# async def knowledge_agent_tool(ctx: RunContext[None], question: str) -> AsyncGenerator[str, None]:
#     """
#     A knowledge agent handling requests concerning general knowledge and searchable information
#
#     Args:
#         ctx: RunContext
#         question: the users message
#     """
#     logfire.debug(f'Knowledge {question}')
#     result = await knowledge_agent.run(question)
#     return result.data


async def gen(prompt: str, message_history: List[ModelMessage]) -> AsyncGenerator[Union[ModelRequestPart, ModelResponsePart], None]:
    output_messages: list[str] = []
    async with supervisor_agent.run_mcp_servers():
        async with supervisor_agent.iter(prompt, message_history=message_history) as run:
            async for node in run:
                if Agent.is_user_prompt_node(node):
                    # A user prompt node => The user has provided input
                    output_messages.append(f'=== UserPromptNode: {node.user_prompt} ===')
                elif Agent.is_model_request_node(node):
                    # A model request node => We can stream tokens from the model's request
                    output_messages.append('=== ModelRequestNode: streaming partial request tokens ===')
                    async with node.stream(run.ctx) as request_stream:
                        final_result_found = False
                        async for event in request_stream:
                            if isinstance(event, PartStartEvent):
                                output_messages.append(f'[Request] Starting part {event.index}: {event.part!r}')
                            elif isinstance(event, PartDeltaEvent):
                                if isinstance(event.delta, TextPartDelta):
                                    output_messages.append(
                                        f'[Request] Part {event.index} text delta: {event.delta.content_delta!r}'
                                    )
                                    yield TextPart(
                                        content=event.delta.content_delta
                                    )
                                elif isinstance(event.delta, ThinkingPartDelta):
                                    output_messages.append(
                                        f'[Request] Part {event.index} thinking delta: {event.delta.content_delta!r}'
                                    )
                                elif isinstance(event.delta, ToolCallPartDelta):
                                    output_messages.append(
                                        f'[Request] Part {event.index} args delta: {event.delta.args_delta}'
                                    )
                            elif isinstance(event, FinalResultEvent):
                                output_messages.append(
                                    f'[Result] The model started producing a final result (tool_name={event.tool_name})'
                                )
                                final_result_found = True
                                break

                        if final_result_found:
                            # Once the final result is found, we can call `AgentStream.stream_text()` to stream the text.
                            # A similar `AgentStream.stream_output()` method is available to stream structured output.
                            async for output in request_stream.stream_text(delta=True, debounce_by=None):
                                output_messages.append(f'[Output] {output}')
                                yield TextPart(
                                    content=output
                                )
                elif Agent.is_call_tools_node(node):
                    # A handle-response node => The model returned some data, potentially calls a tool
                    output_messages.append('=== CallToolsNode: streaming partial response & tool usage ===')
                    async with node.stream(run.ctx) as handle_stream:
                        async for event in handle_stream:
                            if isinstance(event, FunctionToolCallEvent):
                                output_messages.append(
                                    f'[Tools] The LLM calls tool={event.part.tool_name!r} with args={event.part.args} (tool_call_id={event.part.tool_call_id!r})'
                                )
                                yield ToolCallPart(
                                    tool_name=event.part.tool_name,
                                    args=event.part.args,
                                    tool_call_id=event.part.tool_call_id
                                )
                            elif isinstance(event, FunctionToolResultEvent):
                                output_messages.append(
                                    f'[Tools] Tool call {event.tool_call_id!r} returned => {event.result.content}'
                                )
                                yield ToolReturnPart(
                                    tool_name=event.result.tool_name,
                                    content=event.result.content,
                                    tool_call_id=event.tool_call_id,
                                    timestamp=event.result.timestamp
                                )
                elif Agent.is_end_node(node):
                    # Once an End node is reached, the agent run is complete
                    assert run.result is not None
                    assert run.result.output == node.data.output
                    output_messages.append(f'=== Final Agent Output: {run.result.output} ===')

    # for message in output_messages:
    #     print(message)


async def main(prompt):
    with logfire.span('Standalone assistant test run'):
        async for token in gen(prompt, []):
            print(token)



if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Accept one command line argument string.")

    parser.add_argument("prompt", type=str, help="Prompt")
    args = parser.parse_args()
    asyncio.run(main(args.prompt))
