import asyncio
import os

import mcp.types as types
from mcp.server import Server
from mcp.server.stdio import stdio_server
from xai_sdk import Client, chat, tools

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

        query: str = arguments.get("query", "")

        client = Client(api_key=XAI_API_KEY)
        session = client.chat.create(
            model="grok-4-1-fast",
            tools=[tools.x_search()],
        )
        session.append(
            chat.system(
                """You are a specialized search assistant. Use your search capabilities to find real-time information on X/Twitter.

You MUST respond in the following JSON format:
{
    "posts": [
        {
            "url": "https://x.com/username/status/...",
            "username": "username",
            "content": "The post content"
        }
    ],
    "summary": "A summary answering the user's question based on the search results"
}

Include relevant posts found in the search results. If no posts are found, return an empty posts array."""
            )
        )
        session.append(chat.user(query))
        grok_output = session.sample().content
        return [types.TextContent(type="text", text=grok_output)]

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

        question = arguments.get("question", "")
        client = Client(api_key=XAI_API_KEY)
        session = client.chat.create(
            model="grok-4-1-fast",
            tools=[tools.web_search(), tools.x_search()],
        )
        session.append(
            chat.system(
                """You are a helpful AI assistant that provides accurate and well-researched answers.

You MUST respond in the following JSON format:
{
    "sources": [
        {
            "url": "URL of the source (if available)",
            "content_summary": "Relevant excerpt or description from the source"
        }
    ],
    "summary": "A comprehensive answer to the user's question"
}

Include relevant sources that support your answer. If no specific sources are available, return an empty sources array."""
            )
        )
        session.append(chat.user(question))
        grok_output = session.sample().content
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
