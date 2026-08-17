import base64
import json
import mimetypes
import os
from pathlib import Path
from typing import Literal

import httpx
from mcp.server import MCPServer
from xai_sdk import Client, chat, tools

XAI_API_KEY = os.environ.get("XAI_API_KEY")

# API で利用可能な最新モデル（list_language_models / list_image_generation_models 基準）
CHAT_MODEL = "grok-4.6"
IMAGE_MODEL = "grok-imagine-image-2.0"

server = MCPServer("grok-search-server")

AspectRatio = Literal["1:1", "3:4", "4:3", "9:16", "16:9"]


def detect_mime_type(image_bytes: bytes, file_path: str | None = None) -> str:
    """画像データからMIMEタイプを検出する"""
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

    if file_path:
        mime_type, _ = mimetypes.guess_type(file_path)
        if mime_type and mime_type.startswith("image/"):
            return mime_type

    return "image/jpeg"


def _require_api_key() -> str | None:
    if not XAI_API_KEY:
        return "Error: XAI_API_KEY is not set."
    return None


async def _load_image_data(
    image_path: str | None = None,
    image_url: str | None = None,
    image_base64: str | None = None,
    *,
    allow_url_passthrough: bool = False,
) -> str | None:
    """画像ソースを Data URI（または URL）に変換。失敗時は None。"""
    if image_base64:
        if image_base64.startswith("data:"):
            return image_base64
        try:
            image_bytes = base64.b64decode(image_base64)
            mime_type = detect_mime_type(image_bytes)
            return f"data:{mime_type};base64,{image_base64}"
        except Exception:
            return f"data:image/jpeg;base64,{image_base64}"

    if image_path:
        image_bytes = Path(image_path).read_bytes()
        mime_type = detect_mime_type(image_bytes, image_path)
        b64_string = base64.b64encode(image_bytes).decode("utf-8")
        return f"data:{mime_type};base64,{b64_string}"

    if image_url:
        if allow_url_passthrough:
            return image_url
        async with httpx.AsyncClient(timeout=60.0) as client:
            img_response = await client.get(image_url)
            img_response.raise_for_status()
            content_type = img_response.headers.get("content-type", "")
            if content_type.startswith("image/"):
                mime_type = content_type.split(";")[0]
            else:
                mime_type = detect_mime_type(img_response.content, image_url)
            b64_string = base64.b64encode(img_response.content).decode("utf-8")
            return f"data:{mime_type};base64,{b64_string}"

    return None


def _json_text(payload: dict) -> str:
    return json.dumps(payload, ensure_ascii=True, separators=(",", ":"))


@server.tool(
    description="X (Twitter) のリアルタイム情報をGrokで検索します。",
)
async def search_x(query: str) -> str:
    """X (Twitter) のリアルタイム情報をGrokで検索します。"""
    if err := _require_api_key():
        return err

    client = Client(api_key=XAI_API_KEY)
    session = client.chat.create(
        model=CHAT_MODEL,
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
            "content": "The post content",
            "images": ["https://image_url1", "https://image_url2"]
        }
    ],
    "summary": "A summary answering the user's question based on the search results"
}

Include relevant posts found in the search results. If no posts are found, return an empty posts array."""
        )
    )
    session.append(chat.user(query))
    return session.sample().content


@server.tool(
    description="Grokに自由に質問できます。X検索に限らず、一般的な質問や推論タスクに使えます。",
)
async def ask_grok(question: str) -> str:
    """Grokに自由に質問できます。"""
    if err := _require_api_key():
        return err

    client = Client(api_key=XAI_API_KEY)
    session = client.chat.create(
        model=CHAT_MODEL,
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
    return session.sample().content


@server.tool(
    description="テキストプロンプトから画像を生成します。Grok Imagine Image APIを使用。ローカルにファイルは保存せず、URLを返すだけです。",
)
async def generate_image(
    prompt: str,
    n: int = 1,
    aspect_ratio: AspectRatio = "1:1",
) -> str:
    """テキストプロンプトから画像を生成します。"""
    if err := _require_api_key():
        return err

    if n < 1 or n > 10:
        return "Error: 'n' must be between 1 and 10."

    try:
        client = Client(api_key=XAI_API_KEY)
        if n == 1:
            response = client.image.sample(
                model=IMAGE_MODEL,
                prompt=prompt,
                aspect_ratio=aspect_ratio,
                image_format="url",
            )
            result = {"status": "ok", "image": {"url": response.url}}
        else:
            responses = client.image.sample_batch(
                model=IMAGE_MODEL,
                prompt=prompt,
                aspect_ratio=aspect_ratio,
                image_format="url",
                n=n,
            )
            result = {
                "status": "ok",
                "images": [{"url": resp.url} for resp in responses],
            }
        return _json_text(result)
    except Exception as e:
        return f"Error: {e}"


@server.tool(
    description="既存の画像をテキストプロンプトで編集します。Grok Imagine Image APIを使用。ローカルにファイルは保存せず、URLを返すだけです。",
)
async def edit_image(
    prompt: str,
    image_path: str | None = None,
    image_url: str | None = None,
    image_base64: str | None = None,
    n: int = 1,
) -> str:
    """既存の画像をテキストプロンプトで編集します。"""
    if err := _require_api_key():
        return err

    if not any([image_path, image_url, image_base64]):
        return "Error: One of 'image_path', 'image_url', or 'image_base64' is required."

    if n < 1 or n > 10:
        return "Error: 'n' must be between 1 and 10."

    try:
        image_data = await _load_image_data(image_path, image_url, image_base64)
        if not image_data:
            return "Error: Failed to load image data."

        client = Client(api_key=XAI_API_KEY)
        if n == 1:
            response = client.image.sample(
                model=IMAGE_MODEL,
                image_url=image_data,
                prompt=prompt,
                image_format="url",
            )
            result = {"status": "ok", "image": {"url": response.url}}
        else:
            responses = client.image.sample_batch(
                model=IMAGE_MODEL,
                image_url=image_data,
                prompt=prompt,
                image_format="url",
                n=n,
            )
            result = {
                "status": "ok",
                "images": [{"url": resp.url} for resp in responses],
            }
        return _json_text(result)
    except Exception as e:
        return f"Error: {e}"


@server.tool(
    description="画像の内容を理解して説明します。Grok Vision APIを使用。",
)
async def image_understanding(
    question: str,
    image_path: str | None = None,
    image_url: str | None = None,
    image_base64: str | None = None,
) -> str:
    """画像の内容を理解して説明します。"""
    if err := _require_api_key():
        return err

    if not any([image_path, image_url, image_base64]):
        return "Error: One of 'image_path', 'image_url', or 'image_base64' is required."

    try:
        image_data = await _load_image_data(
            image_path,
            image_url,
            image_base64,
            allow_url_passthrough=True,
        )
        if not image_data:
            return "Error: Failed to load image data."

        client = Client(api_key=XAI_API_KEY, timeout=3600)
        session = client.chat.create(model=CHAT_MODEL)
        session.append(
            chat.user(
                question,
                chat.image(image_url=image_data, detail="high"),
            )
        )
        return session.sample().content
    except Exception as e:
        return f"Error: {e}"


def main() -> None:
    """Entry point for the MCP server."""
    server.run(transport="stdio")


if __name__ == "__main__":
    main()
