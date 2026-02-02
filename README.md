# grok-mcp-server

わたくし、X (Twitter) のリアルタイム情報を xAI の Grok さんに聞いてきてくれる MCP サーバーですわ。

## これは何？

Claude Code とか Claude Desktop に「ねえねえ、今 X で何が流行ってるの？」って聞けるようにする拡張機能ですわね。

Grok の検索能力を Claude に追加できるので、リアルタイムの情報が必要なときに便利ですの。ニュース速報とか、トレンドとか、そういうのがすぐ調べられますわよ。

## セットアップ方法

### ステップ1: API キーを取得してください

まず [xAI Console](https://console.x.ai/) でアカウントを作って、API キーをゲットしてくださいな。

### ステップ2: Claude Code に MCP サーバーを追加

ターミナルで以下のコマンドを実行してください：

```bash
claude mcp add --scope user -e XAI_API_KEY=あなたのAPIキー grok -- uvx https://github.com/cympfh/grok-mcp-server
```

たったこれだけですわ！API キーも一緒に設定できるので、設定ファイルを手で編集する必要はありませんの。

### ステップ3: Claude Code を再起動

設定を反映させるために一度再起動してください。これで準備完了ですわ。

## 使い方

Claude Code でこんな感じにリクエストすると、X の最新情報を検索してきてくれますわよ：

```
「今日の AI 業界のニュース教えて」
「Rust の最新トレンドは？」
「○○さんの最近のツイート調べて」
```

わたくしが Grok さんに聞いてきて、結果をお伝えしますわ。

## ちょっとした注意事項

- API キーは絶対に GitHub とかに push しないでくださいね！
- Grok API は有料ですので、使いすぎには注意してください
- X の検索結果なので、情報の正確性はご自身で判断してくださいな

## 開発者向け情報

ローカルで開発したい方はこちらをどうぞ：

```bash
# 依存関係のインストール
uv sync

# サーバーの起動（開発用）
uv run python server.py
```

### 技術スタック

- **Protocol**: MCP (Model Context Protocol)
- **Communication**: stdio（HTTP じゃないですわよ）
- **API**: xAI Grok API (`grok-4-1-fast` モデル)
- **Python**: 3.13 以上
- **依存**: httpx, mcp

コードは `server.py` 一つだけのシンプル構成ですわ。読みやすいと思いますわよ。

## ライセンス

MIT ライセンスですわ。ご自由にお使いくださいな。

---

何か問題があったら Issue を立てていただければ対応しますわ。よろしくお願いいたします！
