import asyncio
import base64
import json
import mimetypes
import os
from pathlib import Path

import httpx
import mcp.types as types
from mcp.server import Server
from mcp.server.stdio import stdio_server
from xai_sdk import Client, chat, tools

# xAI APIの設定
XAI_API_KEY = os.environ.get("XAI_API_KEY")
XAI_CHAT_URL = "https://api.x.ai/v1/chat/completions"
XAI_IMAGE_GENERATION_URL = "https://api.x.ai/v1/images/generations"
XAI_IMAGE_EDIT_URL = "https://api.x.ai/v1/images/edits"

# サーバーインスタンスの作成
server = Server("grok-search-server")


def detect_mime_type(image_bytes: bytes, file_path: str | None = None) -> str:
    """画像データからMIMEタイプを検出する"""
    # マジックバイトで判定
    if image_bytes.startswith(b"\xff\xd8\xff"):
        return "image/jpeg"
    elif image_bytes.startswith(b"\x89PNG\r\n\x1a\n"):
        return "image/png"
    elif image_bytes.startswith(b"GIF87a") or image_bytes.startswith(b"GIF89a"):
        return "image/gif"
    elif image_bytes.startswith(b"RIFF") and image_bytes[8:12] == b"WEBP":
        return "image/webp"
    elif image_bytes.startswith(b"BM"):
        return "image/bmp"

    # マジックバイトで判定できない場合、ファイルパスから推測
    if file_path:
        mime_type, _ = mimetypes.guess_type(file_path)
        if mime_type and mime_type.startswith("image/"):
            return mime_type

    # デフォルトはJPEG
    return "image/jpeg"


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
        types.Tool(
            name="generate_image",
            description="テキストプロンプトから画像を生成します。Grok Imagine Image APIを使用。ローカルにファイルは保存せず、URLを返すだけです。",
            inputSchema={
                "type": "object",
                "properties": {
                    "prompt": {
                        "type": "string",
                        "description": "生成したい画像の説明（テキストプロンプト）",
                    },
                    "n": {
                        "type": "integer",
                        "description": "生成する画像の数（1-10）。デフォルト: 1",
                        "minimum": 1,
                        "maximum": 10,
                    },
                    "aspect_ratio": {
                        "type": "string",
                        "description": "画像のアスペクト比（1:1, 3:4, 4:3, 9:16, 16:9）。デフォルト: 1:1",
                        "enum": ["1:1", "3:4", "4:3", "9:16", "16:9"],
                    },
                },
                "required": ["prompt"],
            },
        ),
        types.Tool(
            name="edit_image",
            description="既存の画像をテキストプロンプトで編集します。Grok Imagine Image APIを使用。ローカルにファイルは保存せず、URLを返すだけです。",
            inputSchema={
                "type": "object",
                "properties": {
                    "prompt": {
                        "type": "string",
                        "description": "画像に対する編集指示（テキストプロンプト）",
                    },
                    "image_path": {
                        "type": "string",
                        "description": "編集する画像のファイルパス",
                    },
                    "image_url": {
                        "type": "string",
                        "description": "編集する画像のURL",
                    },
                    "image_base64": {
                        "type": "string",
                        "description": "編集する画像のbase64エンコードデータ",
                    },
                    "n": {
                        "type": "integer",
                        "description": "生成する編集済み画像の数（1-10）。デフォルト: 1",
                        "minimum": 1,
                        "maximum": 10,
                    },
                },
                "required": ["prompt"],
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

    elif name == "generate_image":
        if not arguments or "prompt" not in arguments:
            return [
                types.TextContent(
                    type="text", text="Error: 'prompt' argument is required."
                )
            ]

        if not XAI_API_KEY:
            return [
                types.TextContent(type="text", text="Error: XAI_API_KEY is not set.")
            ]

        prompt = arguments.get("prompt", "")
        n = arguments.get("n", 1)
        aspect_ratio = arguments.get("aspect_ratio", "1:1")

        try:
            client = Client(api_key=XAI_API_KEY)
            if n == 1:
                response = client.image.sample(
                    model="grok-imagine-image",
                    prompt=prompt,
                    aspect_ratio=aspect_ratio,
                    image_format="url",
                )
                result = {"status": "ok", "image": {"url": response.url}}
            elif n > 1:
                responses = client.image.sample_batch(
                    model="grok-imagine-image",
                    prompt=prompt,
                    aspect_ratio=aspect_ratio,
                    image_format="url",
                    n=n,
                )
                result = {
                    "status": "ok",
                    "images": [{"url": resp.url} for resp in responses],
                }
            return [
                types.TextContent(
                    type="text",
                    text=json.dumps(result, ensure_ascii=True, separators=(",", ":")),
                )
            ]

        except Exception as e:
            return [types.TextContent(type="text", text=f"Error: {str(e)}")]

    elif name == "edit_image":
        if not arguments or "prompt" not in arguments:
            return [
                types.TextContent(
                    type="text", text="Error: 'prompt' argument is required."
                )
            ]

        if not XAI_API_KEY:
            return [
                types.TextContent(type="text", text="Error: XAI_API_KEY is not set.")
            ]

        # 画像ソースの検証（少なくとも1つ必要）
        image_path = arguments.get("image_path")
        image_url = arguments.get("image_url")
        image_base64 = arguments.get("image_base64")

        if not any([image_path, image_url, image_base64]):
            return [
                types.TextContent(
                    type="text",
                    text="Error: One of 'image_path', 'image_url', or 'image_base64' is required.",
                )
            ]

        prompt = arguments.get("prompt", "")
        n = arguments.get("n", 1)

        try:
            # 画像データをbase64エンコードしてData URI形式に変換
            image_data = None
            if image_base64:
                # 既にbase64の場合、Data URI形式に変換
                # image_base64がData URI形式でない場合のみ変換
                if not image_base64.startswith("data:"):
                    # base64からバイナリデータを取得してMIMEタイプを検出
                    try:
                        image_bytes = base64.b64decode(image_base64)
                        mime_type = detect_mime_type(image_bytes)
                        image_data = f"data:{mime_type};base64,{image_base64}"
                    except Exception:
                        # デコードに失敗した場合はデフォルト
                        image_data = f"data:image/jpeg;base64,{image_base64}"
                else:
                    image_data = image_base64
            elif image_path:
                image_bytes = Path(image_path).read_bytes()
                mime_type = detect_mime_type(image_bytes, image_path)
                b64_string = base64.b64encode(image_bytes).decode("utf-8")
                image_data = f"data:{mime_type};base64,{b64_string}"
            elif image_url:
                async with httpx.AsyncClient(timeout=60.0) as client:
                    img_response = await client.get(image_url)
                    img_response.raise_for_status()
                    # Content-Typeヘッダーから取得を試みる
                    content_type = img_response.headers.get("content-type", "")
                    if content_type.startswith("image/"):
                        mime_type = content_type.split(";")[0]
                    else:
                        # ヘッダーにない場合はバイト列から検出
                        mime_type = detect_mime_type(img_response.content, image_url)
                    b64_string = base64.b64encode(img_response.content).decode("utf-8")
                    image_data = f"data:{mime_type};base64,{b64_string}"

            if not image_data:
                return [
                    types.TextContent(
                        type="text", text="Error: Failed to load image data."
                    )
                ]

            client = Client(api_key=XAI_API_KEY)
            if n == 1:
                response = client.image.sample(
                    model="grok-imagine-image",
                    image_url=image_data,
                    prompt=prompt,
                    image_format="url",
                )
                result = {"status": "ok", "image": {"url": response.url}}
            elif n > 1:
                responses = client.image.sample_batch(
                    model="grok-imagine-image",
                    image_url=image_data,
                    prompt=prompt,
                    image_format="url",
                    n=n,
                )
                result = {
                    "status": "ok",
                    "images": [{"url": resp.url} for resp in responses],
                }
            return [
                types.TextContent(
                    type="text",
                    text=json.dumps(result, ensure_ascii=True, separators=(",", ":")),
                )
            ]

        except Exception as e:
            return [types.TextContent(type="text", text=f"Error: {str(e)}")]

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
