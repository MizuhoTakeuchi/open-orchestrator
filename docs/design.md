# Open Orchestrator: Architecture Design

## Overview

Open Orchestrator is an AI orchestrator for local LLMs in air-gapped environments.
It connects to vLLM's OpenAI-compatible API and provides tool calling, multi-agent coordination,
CLI interface, and permission management.

---

## Project Structure

```
open-orchestrator/
├── pyproject.toml
├── config.yaml                    # Default config (endpoint, model name, etc.)
├── docs/
│   └── design.md                  # This document
└── src/
    └── open_orchestrator/
        ├── __init__.py
        ├── main.py                # CLI entrypoint (argparse + REPL)
        ├── agent.py               # Core agent loop
        ├── config.py              # Config model (Pydantic)
        ├── display.py             # Rich terminal display
        ├── permissions.py         # Permission management
        ├── orchestrator.py        # Multi-agent coordination
        └── tools/
            ├── __init__.py        # ToolRegistry + base Tool dataclass
            ├── file_tools.py      # read_file, write_file, edit_file
            ├── bash_tool.py       # bash execution (with timeout)
            ├── search_tools.py    # glob, grep
            └── task_tool.py       # Sub-agent launcher
```

---

## Component Descriptions

### `config.py`
- Pydantic models for all configuration
- Loads from `config.yaml` with environment variable overrides
- LLM settings: base_url, api_key, model, max_tokens, temperature
- Permission settings: default_mode, auto_allow list
- Agent settings: max_iterations, system_prompt

### `agent.py`
The core agent loop:
```
while not done:
    response = llm.chat(messages, tools=registry.to_openai_schema())

    if finish_reason == "stop":
        display.stream_text(response.content)
        break

    if tool_calls:
        for call in tool_calls:
            permitted = await permissions.check(call)
            result = await registry.execute(call) if permitted else deny_result
            messages.append(tool_result_msg(call.id, result))
```
- Continues loop while `finish_reason == "tool_calls"`
- Streaming disabled during tool calls for UX consistency
- Streaming enabled only for final text response

### `tools/__init__.py`
```python
@dataclass
class Tool:
    name: str
    description: str
    schema: dict          # JSON Schema for parameters
    requires_permission: bool
    handler: Callable

class ToolRegistry:
    def register(tool: Tool)
    def to_openai_schema() -> list[dict]  # Convert to OpenAI tools format
    async def execute(call: ToolCall) -> str
```

### `display.py`
- Rich-based terminal output
- Streaming text display with live updates
- Tool call panels showing name, arguments, and results
- Error and permission request display

### `permissions.py`
Three permission levels:
- `auto`: Always execute without asking
- `ask`: Prompt user before each execution (default)
- `deny`: Always deny

Session-level always-allow memory: user can press `[a]` to allow a tool for the rest of the session.

Confirmation UI:
```
╭─ Tool: write_file ─────────────────────────────╮
│ Path: /tmp/test.txt                             │
│ Content: Hello, world!                          │
╰─────────────────────────────────────────────────╯
[y] Allow  [n] Deny  [a] Always allow  [q] Quit
```

### `orchestrator.py`
- Manages multiple Agent instances
- Uses `asyncio.gather()` for parallel task execution
- Routes results back to parent agent

### `tools/task_tool.py`
```python
async def spawn_subagent(prompt: str, tools: list[str] | None = None) -> str:
    sub_agent = Agent(
        system_prompt=SUBAGENT_SYSTEM_PROMPT,
        allowed_tools=tools or DEFAULT_SUBAGENT_TOOLS,  # excludes 'task'
    )
    return await sub_agent.run(prompt)
```

---

## Tool Specifications

| Tool Name   | Description                          | Requires Permission |
|-------------|--------------------------------------|---------------------|
| `read_file` | Read file with line numbers          | No                  |
| `write_file`| Create/overwrite file                | **Yes**             |
| `edit_file` | Partial edit via string replacement  | **Yes**             |
| `bash`      | Shell command execution (30s timeout)| **Yes**             |
| `glob`      | File pattern search                  | No                  |
| `grep`      | File content search (ripgrep-compat) | No                  |
| `task`      | Launch sub-agent                     | No                  |

---

## Multi-Agent Design

- Parent agent calls `task` tool with a prompt
- `orchestrator.py` spawns a new `Agent` instance as an asyncio task
- Multiple parallel `task` calls use `asyncio.gather()`
- Sub-agents cannot call `task` (prevent infinite recursion)
- Results returned as text to parent's message history

---

## CLI Interface

```bash
open-orchestrator                          # Interactive REPL mode
open-orchestrator "Execute this task"      # One-shot mode
open-orchestrator --model qwen2.5-coder   # Specify model
open-orchestrator --base-url http://...   # Specify endpoint
open-orchestrator --mode auto             # Permission mode
```

REPL slash commands:
- `/clear` - Clear conversation history
- `/help` - Show available commands
- `/exit` or `/quit` - Exit
- `/tools` - List available tools
- `/mode [auto|ask|deny]` - Change permission mode

---

## Configuration Example (`config.yaml`)

```yaml
llm:
  base_url: http://localhost:8000/v1
  api_key: "token-dummy"
  model: "qwen2.5-coder-32b"
  max_tokens: 8192
  temperature: 0.0

permissions:
  default_mode: ask
  auto_allow:
    - read_file
    - glob
    - grep

agent:
  max_iterations: 50
  system_prompt: |
    You are a helpful AI assistant with access to tools for reading/writing files
    and executing shell commands. Work step by step and explain what you're doing.
```
