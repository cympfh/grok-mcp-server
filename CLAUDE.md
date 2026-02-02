# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a **MCP (Model Context Protocol) Server** that provides real-time X/Twitter search capabilities via xAI's Grok API. It implements a single tool `search_x` that LLM clients (like Claude) can use to search for current information on X/Twitter.

## Architecture

- **Single-file server**: `server.py` contains the entire MCP server implementation
- **MCP Protocol**: Uses `mcp.server.stdio` for stdio-based communication
- **xAI Integration**: Makes API calls to `https://api.x.ai/v1/chat/completions` using the `grok-4-1-fast` model
- **Async-first**: Built with `asyncio` and `httpx` for non-blocking I/O

### How it Works

1. The server runs as a stdio-based MCP server (not HTTP)
2. It registers a tool called `search_x` that accepts a query string
3. When called, it forwards the query to Grok with a system prompt optimized for X/Twitter search
4. Returns the Grok response as plain text to the MCP client

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
- **Tool interface**: Single tool `search_x` with one required parameter `query`
- **Error handling**: Returns errors as text content rather than raising exceptions (MCP convention)
- **Timeout**: 60 second timeout on Grok API calls
