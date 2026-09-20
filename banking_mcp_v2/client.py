import asyncio
import json
import os

from dotenv import load_dotenv
from mcp import Client
from openai import AsyncOpenAI

load_dotenv()


async def main():
    query = input("Enter banking query: ")

    async with Client("http://localhost:8000/mcp") as mcp_client, AsyncOpenAI() as ai_client:
        # 1. Discover MCP tools and describe them to OpenAI.
        tool_list = await mcp_client.list_tools()
        tools = [
            {
                "type": "function",
                "name": tool.name,
                "description": tool.description,
                "parameters": tool.input_schema,
                "strict": False,
            }
            for tool in tool_list.tools
        ]

        # 2. Let the model choose one tool.
        response = await ai_client.responses.create(
            model=os.getenv("OPENAI_MODEL", "gpt-5.4-mini"),
            instructions=(
                "Use tools for banking requests. Ask for missing account or card IDs. "
                "Only block a card when explicitly asked. Never invent bank data."
            ),
            input=query,
            tools=tools,
            parallel_tool_calls=False,
        )

        # 3. Call the selected tool and print its text result.
        for call in response.output:
            if call.type == "function_call":
                print(f"LLM SELECTED TOOL: {call.name}")
                result = await mcp_client.call_tool(call.name, json.loads(call.arguments))
                print("TOOL ERROR: " if result.is_error else "", result.content[0].text, sep="")
                return

        print(response.output_text)


if __name__ == "__main__":
    asyncio.run(main())
