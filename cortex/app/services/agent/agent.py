
import json
import logging
from typing import List, Dict, Any, Optional

from openai import OpenAI, AsyncOpenAI
import httpx

from app.core.config import settings
from app.services.mcp.client import get_mcp_client
from app.models.stream import StreamEvent, StreamEventType

logger = logging.getLogger(__name__)

class ResearchAgent:
    """
    Agent capable of using MCP tools to conduct research.
    """

    def __init__(self, model: str = None):
        self.model = model or settings.LLM_SOLVER_MODEL # Use smart model for research
        self.client = AsyncOpenAI(
            api_key=settings.OPENAI_API_KEY or "ollama",
            base_url=settings.LLM_SOLVER_API_BASE + "/v1" if settings.LLM_PROVIDER == "ollama" else None
        )
        self.mcp_client = get_mcp_client()
        self.max_turns = 10

    async def execute_stream(self, query: str):
        """
        Run the agent loop and yield StreamEvents.
        """
        yield StreamEvent(
            event=StreamEventType.THOUGHT,
            data={"step": "Refining research plan...", "content": "Analyzing query and available tools."}
        )

        # 1. Fetch available tools
        # For now, we fetch ALL tools from ALL servers.
        # In future, we might filter based on query.
        raw_tools_map = await self.mcp_client.get_all_tools()

        # Flatten and convert
        all_openai_tools = []
        tool_lookup = {}

        for server, tools in raw_tools_map.items():
            for tool in tools:
                # Create a unique ID: server__toolname
                unique_name = f"{server}__{tool.name}"

                # Clone tool object to modify name for LLM uniqueness
                # (Simple hack: we'd ideally wrapping the tool definition)
                # For this PoC, we assume tool names are unique or we just use tool.name
                # But to route correctly back to server, we need to track it.

                tool_def = {
                    "type": "function",
                    "function": {
                        "name": unique_name,
                        "description": tool.description,
                        "parameters": tool.inputSchema
                    }
                }
                all_openai_tools.append(tool_def)
                tool_lookup[unique_name] = (server, tool.name)

        messages = [
            {"role": "system", "content": "You are a research assistant. Use the available tools to answer the user's question purely based on data. If you have enough information, write a final answer."},
            {"role": "user", "content": query}
        ]

        logger.info(f"Starting Research Agent with {len(all_openai_tools)} tools")

        for turn in range(self.max_turns):
            # Call LLM
            try:
                # Prepare kwargs
                kwargs = {
                    "model": self.model,
                    "messages": messages,
                }
                if all_openai_tools:
                    kwargs["tools"] = all_openai_tools
                    kwargs["tool_choice"] = "auto"

                # Notify thinking
                yield StreamEvent(event=StreamEventType.THOUGHT, data={"step": "Reasoning", "content": f"Turn {turn+1}: Assessing information..."})

                response = await self.client.chat.completions.create(**kwargs)
                msg = response.choices[0].message

                # Check for tool calls
                if msg.tool_calls:
                    messages.append(msg) # Add assistant message with tool_calls

                    for tool_call in msg.tool_calls:
                        fname = tool_call.function.name
                        args_str = tool_call.function.arguments
                        args = json.loads(args_str)

                        logger.info(f"Agent calling tool: {fname} with {args}")

                        # Yield Tool Call Event
                        yield StreamEvent(
                            event=StreamEventType.TOOL_CALL,
                            data={"tool": fname, "args": args}
                        )

                        if fname in tool_lookup:
                            server, real_tool_name = tool_lookup[fname]
                            try:
                                yield StreamEvent(event=StreamEventType.THOUGHT, data={"step": "Executing Tool", "content": f"Calling {real_tool_name}..."})

                                result = await self.mcp_client.call_tool(server, real_tool_name, args)
                                tool_result_str = str(result.content) # MCP result content

                                yield StreamEvent(
                                    event=StreamEventType.TOOL_RESULT,
                                    data={"tool": fname, "result": tool_result_str[:200] + "..." if len(tool_result_str) > 200 else tool_result_str}
                                )
                                content = tool_result_str

                            except Exception as e:
                                content = f"Error executing tool: {e}"
                                yield StreamEvent(event=StreamEventType.ERROR, data={"error": str(e)})
                        else:
                            content = "Error: Tool not found."

                        messages.append({
                            "role": "tool",
                            "tool_call_id": tool_call.id,
                            "content": content
                        })

                else:
                    # No tool calls, final answer
                    final_ans = msg.content
                    # Stream tokens (simulated for now since we did non-streaming call)
                    yield StreamEvent(event=StreamEventType.TOKEN, data={"text": final_ans})
                    yield StreamEvent(event=StreamEventType.DONE, data={})
                    return

            except Exception as e:
                logger.error(f"Agent loop error: {e}")
                yield StreamEvent(event=StreamEventType.ERROR, data={"error": str(e)})
                return

        yield StreamEvent(event=StreamEventType.THOUGHT, data={"step": "Limit Reached", "content": "Max turns reached."})
        yield StreamEvent(event=StreamEventType.DONE, data={})

    async def execute(self, query: str) -> str:
        """
        Non-streaming wrapper for execute_stream.
        Aggregates the final answer.
        """
        final_answer = ""
        async for event in self.execute_stream(query):
            if event.event == StreamEventType.TOKEN:
                final_answer += event.data.get("text", "")
            elif event.event == StreamEventType.DONE:
                break

        return final_answer or "No answer generated."
