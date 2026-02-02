import asyncio
import os

import httpx
import mcp.types as types
from mcp.server import Server
from mcp.server.stdio import stdio_server

# xAI APIの設定
XAI_API_KEY = os.environ.get("XAI_API_KEY")
XAI_BASE_URL = "https://api.x.ai/v1/chat/completions"

# サーバーインスタンスの作成
server = Server("grok-search-server")


@server.list_tools()
async def handle_list_tools() -> list[types.Tool]:
    return [
        types.Tool(
            name="search_x",
            description="X (Twitter) のリアルタイム情報をGrokで検索します。",
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "検索クエリ"},
                },
                "required": ["query"],
            },
        ),
        types.Tool(
            name="ask_grok",
            description="Grokに自由に質問できます。X検索に限らず、一般的な質問や推論タスクに使えます。",
            inputSchema={
                "type": "object",
                "properties": {
                    "question": {"type": "string", "description": "Grokへの質問"},
                },
                "required": ["question"],
            },
        ),
    ]


@server.call_tool()
async def handle_call_tool(
    name: str, arguments: dict | None
) -> list[types.TextContent]:
    if name == "search_x":
        if not arguments or "query" not in arguments:
            return [
                types.TextContent(
                    type="text", text="Error: 'query' argument is required."
                )
            ]

        if not XAI_API_KEY:
            return [
                types.TextContent(type="text", text="Error: XAI_API_KEY is not set.")
            ]

        query = arguments.get("query")
        async with httpx.AsyncClient() as client:
            response = await client.post(
                XAI_BASE_URL,
                headers={
                    "Authorization": f"Bearer {XAI_API_KEY}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": "grok-4-1-fast",
                    "messages": [
                        {
                            "role": "system",
                            "content": "You are a specialized search assistant. Use your search capabilities to find real-time information on X/Twitter.",
                        },
                        {"role": "user", "content": query},
                    ],
                },
                timeout=60.0,
            )

        if response.status_code != 200:
            return [
                types.TextContent(
                    type="text",
                    text=f"API Error: {response.status_code} - {response.text}",
                )
            ]

        result = response.json()
        search_output = result["choices"][0]["message"]["content"]

        return [types.TextContent(type="text", text=search_output)]

    elif name == "ask_grok":
        if not arguments or "question" not in arguments:
            return [
                types.TextContent(
                    type="text", text="Error: 'question' argument is required."
                )
            ]

        if not XAI_API_KEY:
            return [
                types.TextContent(type="text", text="Error: XAI_API_KEY is not set.")
            ]

        question = arguments.get("question")
        async with httpx.AsyncClient() as client:
            response = await client.post(
                XAI_BASE_URL,
                headers={
                    "Authorization": f"Bearer {XAI_API_KEY}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": "grok-4-1-fast",
                    "messages": [
                        {"role": "user", "content": question},
                    ],
                },
                timeout=60.0,
            )

        if response.status_code != 200:
            return [
                types.TextContent(
                    type="text",
                    text=f"API Error: {response.status_code} - {response.text}",
                )
            ]

        result = response.json()
        grok_output = result["choices"][0]["message"]["content"]

        return [types.TextContent(type="text", text=grok_output)]

    raise ValueError(f"Tool not found: {name}")


async def async_main():
    async with stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream, write_stream, server.create_initialization_options()
        )


def main():
    """Entry point for the MCP server."""
    asyncio.run(async_main())


if __name__ == "__main__":
    main()

