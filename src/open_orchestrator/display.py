"""Rich-based terminal display utilities."""

from __future__ import annotations

import json
from typing import Any

from rich.console import Console
from rich.live import Live
from rich.markdown import Markdown
from rich.panel import Panel
from rich.syntax import Syntax
from rich.text import Text

console = Console()


def print_welcome() -> None:
    """Print welcome banner."""
    console.print(
        Panel(
            "[bold cyan]Open Orchestrator[/bold cyan]\n"
            "[dim]AI orchestrator for local LLMs[/dim]\n\n"
            "Type your message, or use /help for commands.\n"
            "Press [bold]Ctrl+C[/bold] to interrupt, [bold]Ctrl+D[/bold] to exit.",
            border_style="cyan",
        )
    )


def print_help() -> None:
    """Print help text."""
    console.print(
        Panel(
            "[bold]Available Commands:[/bold]\n\n"
            "  [cyan]/help[/cyan]            Show this help\n"
            "  [cyan]/clear[/cyan]           Clear conversation history\n"
            "  [cyan]/tools[/cyan]           List available tools\n"
            "  [cyan]/mode [auto|ask|deny][/cyan]  Change permission mode\n"
            "  [cyan]/exit[/cyan] or [cyan]/quit[/cyan]   Exit the program\n\n"
            "[bold]Keyboard Shortcuts:[/bold]\n\n"
            "  [cyan]Ctrl+C[/cyan]           Interrupt current response\n"
            "  [cyan]Ctrl+D[/cyan]           Exit\n"
            "  [cyan]Up/Down[/cyan]          Navigate history\n"
            "  [cyan]Alt+Enter[/cyan]        Insert newline (multiline input)",
            title="Help",
            border_style="blue",
        )
    )


def print_assistant_text(text: str) -> None:
    """Print assistant text response."""
    if text.strip():
        console.print(Markdown(text))


def stream_text(chunks: list[str]) -> None:
    """Display streamed text chunks."""
    with Live(console=console, refresh_per_second=20) as live:
        accumulated = ""
        for chunk in chunks:
            accumulated += chunk
            live.update(Text(accumulated))
    # Final newline
    console.print()


def print_tool_call(tool_name: str, arguments: dict[str, Any]) -> None:
    """Display tool call being made."""
    args_str = json.dumps(arguments, ensure_ascii=False, indent=2)
    syntax = Syntax(args_str, "json", theme="monokai", word_wrap=True)
    console.print(
        Panel(
            syntax,
            title=f"[bold yellow]Tool: {tool_name}[/bold yellow]",
            border_style="yellow",
        )
    )


def print_tool_result(tool_name: str, result: str, success: bool = True) -> None:
    """Display tool execution result."""
    border_color = "green" if success else "red"
    # Truncate very long results for display
    display_result = result
    if len(result) > 2000:
        display_result = result[:2000] + f"\n... [dim]({len(result) - 2000} more chars)[/dim]"
    console.print(
        Panel(
            display_result,
            title=f"[bold {'green' if success else 'red'}]Result: {tool_name}[/bold {'green' if success else 'red'}]",
            border_style=border_color,
        )
    )


def print_permission_request(tool_name: str, arguments: dict[str, Any]) -> None:
    """Display permission request panel."""
    args_str = json.dumps(arguments, ensure_ascii=False, indent=2)
    syntax = Syntax(args_str, "json", theme="monokai", word_wrap=True)
    console.print(
        Panel(
            syntax,
            title=f"[bold red]Permission Required: {tool_name}[/bold red]",
            subtitle="[y] Allow  [n] Deny  [a] Always allow  [q] Quit session",
            border_style="red",
        )
    )


def print_error(message: str) -> None:
    """Print error message."""
    console.print(f"[bold red]Error:[/bold red] {message}")


def print_warning(message: str) -> None:
    """Print warning message."""
    console.print(f"[bold yellow]Warning:[/bold yellow] {message}")


def print_info(message: str) -> None:
    """Print info message."""
    console.print(f"[dim]{message}[/dim]")


def print_tools_list(tools: list[dict[str, Any]]) -> None:
    """Display list of available tools."""
    lines = []
    for tool in tools:
        name = tool.get("function", {}).get("name", "unknown")
        desc = tool.get("function", {}).get("description", "")
        lines.append(f"  [cyan]{name}[/cyan]  {desc}")
    console.print(
        Panel(
            "\n".join(lines),
            title="[bold]Available Tools[/bold]",
            border_style="blue",
        )
    )
