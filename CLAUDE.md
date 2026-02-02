# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a **MCP (Model Context Protocol) Server** that provides real-time X/Twitter search and image generation/editing/understanding capabilities via xAI's Grok API. It implements the following tools that LLM clients (like Claude) can use:
- `search_x`: Search for current information on X/Twitter
- `ask_grok`: Ask Grok general questions (not limited to X search)
- `generate_image`: Generate images from text prompts using Grok Imagine
- `edit_image`: Edit existing images using text prompts
- `image_understanding`: Understand and describe image content using Grok Vision

## Architecture

- **Single-file server**: `server.py` contains the entire MCP server implementation
- **MCP Protocol**: Uses `mcp.server.stdio` for stdio-based communication
- **xAI Integration**: Makes API calls to multiple xAI endpoints:
  - `https://api.x.ai/v1/chat/completions` for chat and search (using `grok-4-1-fast` model)
  - `https://api.x.ai/v1/images/generations` for image generation (using `grok-imagine-image` model)
  - `https://api.x.ai/v1/images/edits` for image editing (using `grok-imagine-image` model)
- **Async-first**: Built with `asyncio` and `httpx` for non-blocking I/O

### How it Works

1. The server runs as a stdio-based MCP server (not HTTP)
2. It registers multiple tools:
   - `search_x`: Accepts a query string and forwards it to Grok with X/Twitter search capabilities
   - `ask_grok`: Accepts a question and forwards it to Grok for general queries (with web and X search capabilities)
   - `generate_image`: Accepts a text prompt and generates images using Grok Imagine API
   - `edit_image`: Accepts an existing image (file path, URL, or base64) and a prompt to modify the image
   - `image_understanding`: Accepts an image (file path, URL, or base64) and a question to understand and describe the image
3. Returns responses as plain text or image data to the MCP client

## Development Commands

### Setup

```bash
# Install dependencies (using uv)
uv sync

# Or with pip
pip install -e .
```

### Running the Server

```bash
# Run as MCP server (stdio mode) - for local development
uv run python server.py

# Or if installed as a package
grok-mcp-server
```

**Note**: This server communicates via stdio (standard input/output), not HTTP. It's designed to be launched by MCP clients like Claude Desktop, not run standalone.

### Environment Variables

- `XAI_API_KEY`: **Required**. Your xAI API key for Grok access

## Configuration for MCP Clients

To use this server with Claude Code or Claude Desktop, add to your MCP settings (`~/.claude/mcp_settings.json`):

```json
{
  "mcpServers": {
    "grok": {
      "command": "uvx",
      "args": ["https://github.com/cympfh/grok-mcp-server"],
      "env": {
        "XAI_API_KEY": "your-api-key-here"
      }
    }
  }
}
```

The `uvx` command will automatically fetch and run the server from GitHub.

## Key Technical Details

- **Python version**: Requires Python 3.13+
- **No database or persistence**: Stateless request/response model
- **Tool interface**: Multiple tools with different purposes:
  - `search_x`: X/Twitter search (required parameter: `query`)
  - `ask_grok`: General Q&A (required parameter: `question`)
  - `generate_image`: Image generation (required: `prompt`; optional: `n`, `aspect_ratio`)
  - `edit_image`: Image editing (required: `prompt` and one of `image_path`/`image_url`/`image_base64`; optional: `n`)
  - `image_understanding`: Image understanding (required: `question` and one of `image_path`/`image_url`/`image_base64`)
- **Image processing features**:
  - Generation: Supports multiple images per request (1-10), customizable aspect ratios (1:1, 3:4, 4:3, 9:16, 16:9)
  - Editing: Modify existing images with text prompts (accepts file path, URL, or base64)
  - Understanding: Analyze and describe image content using Grok Vision API with high detail mode
  - Output format: URL for generated/edited images, text description for understanding
- **Error handling**: Returns errors as text content rather than raising exceptions (MCP convention)
- **Timeout**: 60 second timeout on API calls (3600 seconds for image understanding)
