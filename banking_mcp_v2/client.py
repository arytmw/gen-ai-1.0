import asyncio
import json
import os
from pathlib import Path

from dotenv import load_dotenv
from mcp import Client
from openai import AsyncOpenAI

load_dotenv(Path(__file__).with_name(".env"))
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-5.4-mini")


def convert_tool_to_openai_schema(tool):
    return {
        "type": "function",
        "name": tool.name,
        "description": tool.description,
        "parameters": tool.input_schema,
        "strict": False,
    }


async def main():
    query = input("Enter banking query: ")

    # SDK v2 connects and negotiates the protocol automatically.
    async with Client("http://localhost:8000/mcp") as mcp_client:
        tool_list = await mcp_client.list_tools()
        openai_tools = [convert_tool_to_openai_schema(t) for t in tool_list.tools]

        async with AsyncOpenAI() as ai_client:
            response = await ai_client.responses.create(
                model=OPENAI_MODEL,
                instructions=(
                    "You are a demo banking assistant. Use the tools for banking requests. "
                    "Use account and card IDs provided by the user; ask if missing. "
                    "Only block a card if the user explicitly asks. Never invent bank data."
                ),
                input=query,
                tools=openai_tools,
                parallel_tool_calls=False,
            )

        tool_calls = [item for item in response.output if item.type == "function_call"]
        for call in tool_calls:
            print(f"LLM SELECTED TOOL: {call.name}")
            result = await mcp_client.call_tool(call.name, json.loads(call.arguments))
            if result.is_error:
                for content in result.content:
                    if content.type == "text":
                        print(f"TOOL ERROR: {content.text}")
            else:
                print(json.dumps(result.structured_content, indent=2))

        if not tool_calls:
            print(response.output_text)


if __name__ == "__main__":
    asyncio.run(main())
