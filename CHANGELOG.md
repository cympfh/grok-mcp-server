# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [1.0.0] - 2026-08-17

### Changed
- MCP SDK を 1.x から 2.0 に更新し、low-level `Server` + `@list_tools`/`@call_tool` を `MCPServer` + `@tool()` に移行
- 依存を更新: `mcp>=2.0.0`, `xai-sdk>=1.17.0`
- 起動を `server.run(transport="stdio")` に統一
- ドキュメント (`CLAUDE.md`) を mcp 2.0 構成に合わせて更新

### Fixed
- mcp 2.0 で発生していた `AttributeError: 'Server' object has no attribute 'list_tools'` を解消

## [0.1.0] - 2026-02-02

### Added
- X/Twitter 検索 (`search_x`)、一般質問 (`ask_grok`)
- 画像生成・編集・理解 (`generate_image`, `edit_image`, `image_understanding`)
