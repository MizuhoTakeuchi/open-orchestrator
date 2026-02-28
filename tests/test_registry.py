"""Tests for ToolRegistry."""

from __future__ import annotations

import pytest

from open_orchestrator.tools import Tool, ToolCall, ToolRegistry


def sync_handler(**kwargs: object) -> str:
    return f"sync result: {kwargs}"


async def async_handler(**kwargs: object) -> str:
    return f"async result: {kwargs}"


def make_test_tool(name: str = "test_tool", async_fn: bool = False) -> Tool:
    return Tool(
        name=name,
        description=f"Test tool {name}",
        parameters_schema={
            "type": "object",
            "properties": {
                "value": {"type": "string"},
            },
            "required": [],
        },
        handler=async_handler if async_fn else sync_handler,
        requires_permission=False,
    )


class TestToolRegistry:
    def test_register_and_get(self) -> None:
        registry = ToolRegistry()
        tool = make_test_tool("my_tool")
        registry.register(tool)
        assert registry.get("my_tool") is tool

    def test_get_unknown_returns_none(self) -> None:
        registry = ToolRegistry()
        assert registry.get("unknown") is None

    def test_names(self) -> None:
        registry = ToolRegistry()
        registry.register(make_test_tool("tool_a"))
        registry.register(make_test_tool("tool_b"))
        assert set(registry.names()) == {"tool_a", "tool_b"}

    def test_to_openai_schema(self) -> None:
        registry = ToolRegistry()
        registry.register(make_test_tool("my_tool"))
        schema = registry.to_openai_schema()
        assert len(schema) == 1
        assert schema[0]["type"] == "function"
        assert schema[0]["function"]["name"] == "my_tool"

    def test_to_openai_schema_filtered(self) -> None:
        registry = ToolRegistry()
        registry.register(make_test_tool("tool_a"))
        registry.register(make_test_tool("tool_b"))
        schema = registry.to_openai_schema(allowed=["tool_a"])
        assert len(schema) == 1
        assert schema[0]["function"]["name"] == "tool_a"

    @pytest.mark.asyncio
    async def test_execute_sync_handler(self) -> None:
        registry = ToolRegistry()
        registry.register(make_test_tool("sync_tool", async_fn=False))
        call = ToolCall(id="1", name="sync_tool", arguments={"value": "hello"})
        result = await registry.execute(call)
        assert "sync result" in result

    @pytest.mark.asyncio
    async def test_execute_async_handler(self) -> None:
        registry = ToolRegistry()
        registry.register(make_test_tool("async_tool", async_fn=True))
        call = ToolCall(id="2", name="async_tool", arguments={"value": "world"})
        result = await registry.execute(call)
        assert "async result" in result

    @pytest.mark.asyncio
    async def test_execute_unknown_tool(self) -> None:
        registry = ToolRegistry()
        call = ToolCall(id="3", name="unknown", arguments={})
        result = await registry.execute(call)
        assert "Error" in result
        assert "unknown" in result

    @pytest.mark.asyncio
    async def test_execute_bad_arguments(self) -> None:
        def strict_handler(required_arg: str) -> str:
            return required_arg

        registry = ToolRegistry()
        registry.register(Tool(
            name="strict",
            description="Strict tool",
            parameters_schema={"type": "object", "properties": {}},
            handler=strict_handler,
            requires_permission=False,
        ))
        call = ToolCall(id="4", name="strict", arguments={})  # missing required_arg
        result = await registry.execute(call)
        assert "Error" in result
