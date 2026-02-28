"""Permission management for tool execution."""

from __future__ import annotations

import sys
from typing import Literal

from open_orchestrator.tools import Tool, ToolCall

PermissionMode = Literal["auto", "ask", "deny"]


class PermissionManager:
    """Manages tool execution permissions."""

    def __init__(
        self,
        default_mode: PermissionMode = "ask",
        auto_allow: list[str] | None = None,
    ) -> None:
        self.default_mode = default_mode
        self._auto_allow: set[str] = set(auto_allow or [])
        self._session_allowed: set[str] = set()  # Tools allowed for the whole session
        self._quit_requested = False

    @property
    def quit_requested(self) -> bool:
        return self._quit_requested

    def set_mode(self, mode: PermissionMode) -> None:
        """Change the default permission mode."""
        self.default_mode = mode

    def always_allow(self, tool_name: str) -> None:
        """Mark a tool as always allowed for this session."""
        self._session_allowed.add(tool_name)

    def is_auto_allowed(self, tool_name: str) -> bool:
        """Check if a tool is automatically allowed."""
        return (
            tool_name in self._auto_allow
            or tool_name in self._session_allowed
            or self.default_mode == "auto"
        )

    async def check(self, call: ToolCall, tool: Tool | None = None) -> bool:
        """
        Check if a tool call is permitted.
        Returns True if allowed, False if denied.
        """
        # Import here to avoid circular imports
        from open_orchestrator import display

        requires_perm = tool.requires_permission if tool else True

        # Tools that don't require permission are always allowed
        if not requires_perm:
            return True

        # Check auto-allow list and mode
        if self.is_auto_allowed(call.name):
            return True

        # Deny mode: never ask
        if self.default_mode == "deny":
            display.print_info(f"Tool '{call.name}' denied (mode: deny)")
            return False

        # Ask mode: prompt user
        return await self._prompt_user(call, display)

    async def _prompt_user(self, call: ToolCall, display: object) -> bool:
        """Prompt the user for permission. Returns True if allowed."""
        display.print_permission_request(call.name, call.arguments)

        while True:
            try:
                response = await _async_input(
                    "[y] Allow  [n] Deny  [a] Always allow  [q] Quit: "
                )
                response = response.strip().lower()

                if response in ("y", "yes"):
                    return True
                elif response in ("n", "no"):
                    display.print_info(f"Tool '{call.name}' denied by user.")
                    return False
                elif response in ("a", "always"):
                    self.always_allow(call.name)
                    display.print_info(f"Tool '{call.name}' will always be allowed this session.")
                    return True
                elif response in ("q", "quit"):
                    self._quit_requested = True
                    display.print_info("Quit requested.")
                    return False
                else:
                    print("Please enter y, n, a, or q.")
            except (EOFError, KeyboardInterrupt):
                return False


async def _async_input(prompt: str) -> str:
    """Async-compatible input function."""
    import asyncio

    loop = asyncio.get_event_loop()
    # Run input() in a thread executor to not block the event loop
    return await loop.run_in_executor(None, lambda: input(prompt))
