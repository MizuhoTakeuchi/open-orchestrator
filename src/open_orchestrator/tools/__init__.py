"""Tool registry and base tool definitions."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from typing import Any, Callable


@dataclass
class Tool:
    """A tool that the agent can call."""
    name: str
    description: str
    parameters_schema: dict[str, Any]   # JSON Schema for parameters
    handler: Callable[..., Any]          # async or sync handler
    requires_permission: bool = False


@dataclass
class ToolCall:
    """Represents a tool call from the LLM."""
    id: str
    name: str
    arguments: dict[str, Any]


class ToolRegistry:
    """Registry of available tools."""

    def __init__(self) -> None:
        self._tools: dict[str, Tool] = {}

    def register(self, tool: Tool) -> None:
        """Register a tool."""
        self._tools[tool.name] = tool

    def get(self, name: str) -> Tool | None:
        """Get a tool by name."""
        return self._tools.get(name)

    def names(self) -> list[str]:
        """Get list of tool names."""
        return list(self._tools.keys())

    def to_openai_schema(self, allowed: list[str] | None = None) -> list[dict[str, Any]]:
        """Convert tools to OpenAI API format."""
        tools = []
        for name, tool in self._tools.items():
            if allowed is not None and name not in allowed:
                continue
            tools.append({
                "type": "function",
                "function": {
                    "name": tool.name,
                    "description": tool.description,
                    "parameters": tool.parameters_schema,
                },
            })
        return tools

    async def execute(self, call: ToolCall) -> str:
        """Execute a tool call and return string result."""
        tool = self._tools.get(call.name)
        if tool is None:
            return f"Error: Unknown tool '{call.name}'"

        try:
            if asyncio.iscoroutinefunction(tool.handler):
                result = await tool.handler(**call.arguments)
            else:
                result = tool.handler(**call.arguments)
            return str(result)
        except TypeError as e:
            return f"Error: Invalid arguments for '{call.name}': {e}"
        except Exception as e:
            return f"Error executing '{call.name}': {e}"


# Global registry instance
_registry = ToolRegistry()


def get_registry() -> ToolRegistry:
    """Get the global tool registry."""
    return _registry


def register_tool(tool: Tool) -> None:
    """Register a tool in the global registry."""
    _registry.register(tool)
