"""Tests for permission management."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from open_orchestrator.permissions import PermissionManager
from open_orchestrator.tools import Tool, ToolCall


def make_tool(name: str, requires_permission: bool = True) -> Tool:
    return Tool(
        name=name,
        description=f"Test tool {name}",
        parameters_schema={"type": "object", "properties": {}},
        handler=lambda: None,
        requires_permission=requires_permission,
    )


def make_call(name: str) -> ToolCall:
    return ToolCall(id="test-id", name=name, arguments={})


class TestPermissionManager:
    @pytest.mark.asyncio
    async def test_auto_mode_allows_all(self) -> None:
        pm = PermissionManager(default_mode="auto")
        call = make_call("bash")
        tool = make_tool("bash", requires_permission=True)
        result = await pm.check(call, tool)
        assert result is True

    @pytest.mark.asyncio
    async def test_deny_mode_denies_all(self) -> None:
        with patch("open_orchestrator.display.print_info"):
            pm = PermissionManager(default_mode="deny")
            call = make_call("bash")
            tool = make_tool("bash", requires_permission=True)
            result = await pm.check(call, tool)
            assert result is False

    @pytest.mark.asyncio
    async def test_no_permission_required_always_allowed(self) -> None:
        pm = PermissionManager(default_mode="deny")
        call = make_call("read_file")
        tool = make_tool("read_file", requires_permission=False)
        result = await pm.check(call, tool)
        assert result is True

    @pytest.mark.asyncio
    async def test_auto_allow_list(self) -> None:
        pm = PermissionManager(default_mode="ask", auto_allow=["glob", "grep"])
        call = make_call("glob")
        tool = make_tool("glob", requires_permission=True)
        result = await pm.check(call, tool)
        assert result is True

    @pytest.mark.asyncio
    async def test_session_always_allow(self) -> None:
        pm = PermissionManager(default_mode="ask")
        pm.always_allow("write_file")
        call = make_call("write_file")
        tool = make_tool("write_file", requires_permission=True)
        result = await pm.check(call, tool)
        assert result is True

    @pytest.mark.asyncio
    async def test_ask_mode_user_approves(self) -> None:
        with (
            patch("open_orchestrator.display.print_permission_request"),
            patch("open_orchestrator.display.print_info"),
            patch("open_orchestrator.permissions._async_input", new=AsyncMock(return_value="y")),
        ):
            pm = PermissionManager(default_mode="ask")
            call = make_call("bash")
            tool = make_tool("bash", requires_permission=True)
            result = await pm.check(call, tool)
            assert result is True

    @pytest.mark.asyncio
    async def test_ask_mode_user_denies(self) -> None:
        with (
            patch("open_orchestrator.display.print_permission_request"),
            patch("open_orchestrator.display.print_info"),
            patch("open_orchestrator.permissions._async_input", new=AsyncMock(return_value="n")),
        ):
            pm = PermissionManager(default_mode="ask")
            call = make_call("bash")
            tool = make_tool("bash", requires_permission=True)
            result = await pm.check(call, tool)
            assert result is False

    @pytest.mark.asyncio
    async def test_ask_mode_always_allow(self) -> None:
        with (
            patch("open_orchestrator.display.print_permission_request"),
            patch("open_orchestrator.display.print_info"),
            patch("open_orchestrator.permissions._async_input", new=AsyncMock(return_value="a")),
        ):
            pm = PermissionManager(default_mode="ask")
            call = make_call("bash")
            tool = make_tool("bash", requires_permission=True)
            result = await pm.check(call, tool)
            assert result is True
            assert pm.is_auto_allowed("bash")

    @pytest.mark.asyncio
    async def test_ask_mode_quit(self) -> None:
        with (
            patch("open_orchestrator.display.print_permission_request"),
            patch("open_orchestrator.display.print_info"),
            patch("open_orchestrator.permissions._async_input", new=AsyncMock(return_value="q")),
        ):
            pm = PermissionManager(default_mode="ask")
            call = make_call("bash")
            tool = make_tool("bash", requires_permission=True)
            result = await pm.check(call, tool)
            assert result is False
            assert pm.quit_requested is True

    def test_set_mode(self) -> None:
        pm = PermissionManager(default_mode="ask")
        pm.set_mode("auto")
        assert pm.default_mode == "auto"
