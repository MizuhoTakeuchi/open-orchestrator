"""CLI entrypoint: REPL and one-shot modes."""

from __future__ import annotations

import argparse
import asyncio
import sys
from pathlib import Path
from typing import Literal

from prompt_toolkit import PromptSession
from prompt_toolkit.history import FileHistory
from prompt_toolkit.key_binding import KeyBindings
from rich.console import Console

from open_orchestrator.config import Config, load_config
from open_orchestrator.orchestrator import Orchestrator
from open_orchestrator.permissions import PermissionManager
from open_orchestrator.tools import get_registry
from open_orchestrator.tools.bash_tool import register_bash_tool
from open_orchestrator.tools.file_tools import register_file_tools
from open_orchestrator.tools.search_tools import register_search_tools

console = Console()


def setup_tools(config: Config, permissions: PermissionManager) -> None:
    """Register all tools into the global registry."""
    working_dir = config.working_dir
    register_file_tools(working_dir)
    register_bash_tool(working_dir)
    register_search_tools(working_dir)

    # Task tool is registered last as it depends on other components
    registry = get_registry()
    from open_orchestrator.tools.task_tool import register_task_tool
    register_task_tool(config, registry, permissions)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="open-orchestrator",
        description="AI orchestrator for local LLMs",
    )
    parser.add_argument(
        "prompt",
        nargs="?",
        help="One-shot prompt. If omitted, starts interactive REPL.",
    )
    parser.add_argument(
        "--model",
        help="LLM model name (overrides config)",
    )
    parser.add_argument(
        "--base-url",
        help="vLLM API base URL (overrides config)",
    )
    parser.add_argument(
        "--mode",
        choices=["auto", "ask", "deny"],
        help="Permission mode (overrides config)",
    )
    parser.add_argument(
        "--config",
        type=Path,
        help="Path to config.yaml",
    )
    parser.add_argument(
        "-C",
        "--working-dir",
        type=Path,
        help="Working directory for file operations (default: current directory)",
    )
    return parser.parse_args()


def handle_slash_command(
    cmd: str,
    agent: "Agent",  # noqa: F821
    permissions: PermissionManager,
    config: Config,
) -> bool:
    """
    Handle a slash command.
    Returns True if the REPL should continue, False to exit.
    """
    from open_orchestrator import display

    parts = cmd.strip().split()
    command = parts[0].lower()
    args = parts[1:] if len(parts) > 1 else []

    if command in ("/exit", "/quit"):
        console.print("[dim]Goodbye.[/dim]")
        return False

    elif command == "/help":
        display.print_help()

    elif command == "/clear":
        agent.reset()
        console.print("[dim]Conversation history cleared.[/dim]")

    elif command == "/tools":
        registry = get_registry()
        display.print_tools_list(registry.to_openai_schema())

    elif command == "/mode":
        if args and args[0] in ("auto", "ask", "deny"):
            mode = args[0]
            permissions.set_mode(mode)  # type: ignore
            console.print(f"[dim]Permission mode set to: {mode}[/dim]")
        else:
            console.print(
                f"[dim]Current mode: {permissions.default_mode}. "
                "Usage: /mode [auto|ask|deny][/dim]"
            )

    else:
        console.print(f"[red]Unknown command: {command}. Type /help for help.[/red]")

    return True


async def run_repl(agent: "Agent", permissions: PermissionManager, config: Config) -> None:  # noqa: F821
    """Run the interactive REPL loop."""
    from open_orchestrator import display

    display.print_welcome(config.working_dir)

    history_file = Path.home() / ".local" / "share" / "open-orchestrator" / "history"
    history_file.parent.mkdir(parents=True, exist_ok=True)

    session: PromptSession = PromptSession(
        history=FileHistory(str(history_file)),
        multiline=False,
    )

    while True:
        try:
            user_input = await session.prompt_async(
                "\n[You] ",
            )
        except KeyboardInterrupt:
            console.print("\n[dim]Use /exit to quit.[/dim]")
            continue
        except EOFError:
            console.print("\n[dim]Goodbye.[/dim]")
            break

        user_input = user_input.strip()
        if not user_input:
            continue

        # Handle slash commands
        if user_input.startswith("/"):
            should_continue = handle_slash_command(user_input, agent, permissions, config)
            if not should_continue:
                break
            continue

        # Run the agent
        try:
            await agent.run_streaming(user_input)
        except KeyboardInterrupt:
            console.print("\n[dim]Interrupted.[/dim]")
        except Exception as e:
            display.print_error(f"Unexpected error: {e}")

        if permissions.quit_requested:
            break


async def run_oneshot(agent: "Agent", prompt: str) -> None:  # noqa: F821
    """Run a single prompt and exit."""
    from open_orchestrator import display

    try:
        await agent.run_streaming(prompt)
    except KeyboardInterrupt:
        console.print("\n[dim]Interrupted.[/dim]")
    except Exception as e:
        display.print_error(f"Unexpected error: {e}")


def main() -> None:
    """CLI entrypoint."""
    args = parse_args()

    # Load config
    config = load_config(args.config)

    # Apply CLI overrides
    if args.working_dir:
        config.working_dir = args.working_dir.resolve()
    if args.model:
        config.llm.model = args.model
    if args.base_url:
        config.llm.base_url = args.base_url

    # Setup permissions
    mode = args.mode or config.permissions.default_mode
    permissions = PermissionManager(
        default_mode=mode,  # type: ignore
        auto_allow=config.permissions.auto_allow,
    )

    # Override config mode too
    if args.mode:
        config.permissions.default_mode = args.mode  # type: ignore

    # Register all tools
    setup_tools(config, permissions)

    # Create orchestrator and main agent
    registry = get_registry()
    orchestrator = Orchestrator(config, registry, permissions)
    agent = orchestrator.create_main_agent()

    # Run
    if args.prompt:
        asyncio.run(run_oneshot(agent, args.prompt))
    else:
        asyncio.run(run_repl(agent, permissions, config))


if __name__ == "__main__":
    main()
