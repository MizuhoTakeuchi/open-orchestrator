# Open Orchestrator

閉域環境（外部ネットワーク不可）で動作する、ローカル LLM 向け AI オーケストレータ。
vLLM の OpenAI 互換 API に接続し、ファイル操作・コマンド実行・マルチエージェント並列実行をサポートする。

---

## 特徴

- **ローカル LLM 対応** — vLLM など OpenAI 互換 API であれば接続可能
- **ツール呼び出し** — ファイル読み書き・シェル実行・ファイル検索
- **パーミッション管理** — 書き込み/実行系ツールは事前確認 (ask/auto/deny の3モード)
- **マルチエージェント** — `task` ツールでサブエージェントを並列起動
- **インタラクティブ REPL** — 履歴・補完対応、スラッシュコマンドで操作
- **外部フレームワーク不使用** — langchain 等に依存しないスクラッチ実装

---

## 要件

- Python 3.11 以上
- [uv](https://docs.astral.sh/uv/) (推奨パッケージマネージャ)
- vLLM などの OpenAI 互換 API サーバ

---

## インストール

### 1. uv のインストール

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

インストール後、シェルを再起動するか以下を実行:

```bash
export PATH="$HOME/.local/bin:$PATH"
```

### 2. 依存パッケージのインストール

```bash
git clone <repository-url>
cd open-orchestrator
uv sync
```

### 3. 動作確認

```bash
uv run open-orchestrator --help
```

---

## 設定

プロジェクトルートの `config.yaml` を編集して、LLM エンドポイントとモデルを設定する。

```yaml
llm:
  base_url: http://localhost:8000/v1   # vLLM サーバのアドレス
  api_key: "token-dummy"               # vLLM は任意の値を受け付ける
  model: "qwen2.5-coder-32b"           # モデル名 (vLLM で起動したモデル)
  max_tokens: 8192
  temperature: 0.0

permissions:
  default_mode: ask                    # auto / ask / deny
  auto_allow:                          # 確認なしで自動実行するツール
    - read_file
    - glob
    - grep

agent:
  max_iterations: 50
  system_prompt: |
    You are a helpful AI assistant ...
```

### 環境変数による上書き

| 環境変数 | 対応する設定 |
|---|---|
| `OPENAI_BASE_URL` | `llm.base_url` |
| `OPENAI_API_KEY` | `llm.api_key` |
| `OPENAI_MODEL` | `llm.model` |

```bash
export OPENAI_BASE_URL=http://192.168.1.10:8000/v1
uv run open-orchestrator
```

---

## 使い方

### 対話モード (REPL)

```bash
uv run open-orchestrator
```

起動するとプロンプトが表示され、自由に指示を入力できる。

```
╭─ Open Orchestrator ─────────────────╮
│ AI orchestrator for local LLMs      │
│                                     │
│ Type your message, or /help         │
╰──────────────────────────────────────╯

[You] src/ ディレクトリの構成を教えて
```

### ワンショットモード

```bash
uv run open-orchestrator "カレントディレクトリのPythonファイルを一覧にして"
```

### オプション

```bash
uv run open-orchestrator [OPTIONS] [PROMPT]

オプション:
  -C, --working-dir DIR     作業ディレクトリを指定 (デフォルト: カレントディレクトリ)
  --model MODEL             モデル名 (config.yaml の設定を上書き)
  --base-url BASE_URL       API エンドポイント (config.yaml の設定を上書き)
  --mode {auto,ask,deny}    パーミッションモード (config.yaml の設定を上書き)
  --config CONFIG           config.yaml のパスを指定
```

例:

```bash
# モデルとエンドポイントを指定して起動
uv run open-orchestrator --model llama3.1-70b --base-url http://gpu-server:8000/v1

# 全ツールを確認なしで自動実行するモード
uv run open-orchestrator --mode auto "テストを実行して結果を報告して"

# 任意のディレクトリを作業対象にして起動
uv run open-orchestrator -C /path/to/project
```

---

## REPL スラッシュコマンド

| コマンド | 説明 |
|---|---|
| `/help` | コマンド一覧を表示 |
| `/clear` | 会話履歴をリセット |
| `/tools` | 利用可能なツール一覧を表示 |
| `/mode auto\|ask\|deny` | パーミッションモードを切り替え |
| `/exit` または `/quit` | 終了 |

### キーボードショートカット

| キー | 動作 |
|---|---|
| `Ctrl+C` | 現在の応答を中断 |
| `Ctrl+D` | 終了 |
| `↑` / `↓` | 入力履歴を遡る |

---

## パーミッション管理

書き込み・実行系のツール (`write_file`, `edit_file`, `bash`) を呼び出す際、以下のプロンプトが表示される:

```
╭─ Permission Required: bash ──────────────────╮
│ {                                             │
│   "command": "rm -rf /tmp/old_files"         │
│ }                                             │
╰── [y] Allow  [n] Deny  [a] Always allow  [q] Quit ─╯
```

| キー | 動作 |
|---|---|
| `y` | 今回だけ許可 |
| `n` | 拒否 |
| `a` | セッション中は常に許可 |
| `q` | セッションを終了 |

### パーミッションモード

| モード | 動作 |
|---|---|
| `ask` (デフォルト) | 要許可ツール実行前に毎回確認 |
| `auto` | 全ツールを確認なしで実行 |
| `deny` | 要許可ツールを常に拒否 |

---

## 利用可能なツール

| ツール名 | 説明 | 要確認 |
|---|---|:---:|
| `read_file` | ファイルを行番号付きで読み込む | — |
| `write_file` | ファイルを新規作成または上書き | Yes |
| `edit_file` | 文字列置換による部分編集 | Yes |
| `bash` | シェルコマンドを実行 (タイムアウト 30秒) | Yes |
| `glob` | ファイルパターン検索 (`**/*.py` 等) | — |
| `grep` | ファイル内容の正規表現検索 | — |
| `task` | サブエージェントを起動して並列実行 | — |

---

## マルチエージェント

LLM が `task` ツールを複数同時に呼び出すと、サブエージェントが `asyncio.gather()` で並列実行される。

```
# 例: 2つのディレクトリを並列調査
[You] src/ と tests/ をそれぞれ調べて概要を教えて

→ task("src/ の構成を調べて概要をまとめて")   ┐ 並列実行
→ task("tests/ の構成を調べて概要をまとめて") ┘
```

サブエージェントは `task` ツールを持たないため、再帰的な無限起動は発生しない。

---

## 開発・テスト

```bash
# 開発用依存パッケージのインストール
uv sync --dev

# テスト実行
uv run pytest tests/ -v

# 特定のテストファイルのみ
uv run pytest tests/test_tools.py -v
```

---

## プロジェクト構成

```
open-orchestrator/
├── pyproject.toml
├── config.yaml
├── docs/
│   └── design.md              # アーキテクチャ設計ドキュメント
└── src/
    └── open_orchestrator/
        ├── main.py            # CLI エントリーポイント (REPL)
        ├── agent.py           # コアエージェントループ
        ├── config.py          # 設定モデル (Pydantic)
        ├── display.py         # Rich ターミナル表示
        ├── permissions.py     # パーミッション管理
        ├── orchestrator.py    # マルチエージェント調整
        └── tools/
            ├── __init__.py    # ToolRegistry
            ├── file_tools.py  # read_file, write_file, edit_file
            ├── bash_tool.py   # bash
            ├── search_tools.py # glob, grep
            └── task_tool.py   # task (サブエージェント)
```
