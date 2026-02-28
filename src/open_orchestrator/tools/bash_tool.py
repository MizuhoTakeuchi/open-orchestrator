"""Bash execution tool with timeout."""

from __future__ import annotations

import asyncio
import subprocess

from open_orchestrator.tools import Tool, register_tool

DEFAULT_TIMEOUT = 30


async def bash(command: str, timeout: int = DEFAULT_TIMEOUT, cwd: str | None = None) -> str:
    """Execute a shell command and return its output."""
    try:
        proc = await asyncio.create_subprocess_shell(
            command,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=cwd,
        )
        try:
            stdout, stderr = await asyncio.wait_for(
                proc.communicate(),
                timeout=timeout,
            )
        except asyncio.TimeoutError:
            proc.kill()
            await proc.communicate()
            return f"Error: Command timed out after {timeout} seconds: {command}"

        output_parts = []
        if stdout:
            output_parts.append(stdout.decode("utf-8", errors="replace").rstrip())
        if stderr:
            stderr_text = stderr.decode("utf-8", errors="replace").rstrip()
            if stderr_text:
                output_parts.append(f"[stderr]\n{stderr_text}")

        output = "\n".join(output_parts) if output_parts else ""

        if proc.returncode != 0:
            if output:
                return f"Exit code {proc.returncode}:\n{output}"
            return f"Exit code {proc.returncode}"

        return output if output else "(no output)"

    except Exception as e:
        return f"Error executing command: {e}"


def register_bash_tool() -> None:
    """Register the bash tool into the global registry."""
    register_tool(Tool(
        name="bash",
        description=(
            "Execute a shell command and return its output. "
            f"Commands timeout after {DEFAULT_TIMEOUT} seconds. "
            "Use for running scripts, installing packages, checking system state, etc."
        ),
        parameters_schema={
            "type": "object",
            "properties": {
                "command": {
                    "type": "string",
                    "description": "The shell command to execute",
                },
                "timeout": {
                    "type": "integer",
                    "description": f"Timeout in seconds (default: {DEFAULT_TIMEOUT})",
                    "default": DEFAULT_TIMEOUT,
                },
                "cwd": {
                    "type": "string",
                    "description": "Working directory for the command (default: current directory)",
                },
            },
            "required": ["command"],
        },
        handler=bash,
        requires_permission=True,
    ))
