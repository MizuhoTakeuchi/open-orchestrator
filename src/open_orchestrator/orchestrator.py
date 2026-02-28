"""Multi-agent orchestrator."""

from __future__ import annotations

import asyncio
from typing import Any

from open_orchestrator.config import Config
from open_orchestrator.permissions import PermissionManager
from open_orchestrator.tools import ToolRegistry


class Orchestrator:
    """
    Manages the creation and coordination of agents.
    Handles parallel sub-agent execution via asyncio.gather().
    """

    def __init__(
        self,
        config: Config,
        registry: ToolRegistry,
        permissions: PermissionManager,
    ) -> None:
        self.config = config
        self.registry = registry
        self.permissions = permissions

    def create_main_agent(self) -> "Agent":  # noqa: F821
        """Create the primary agent with all tools."""
        from open_orchestrator.agent import Agent

        return Agent(
            config=self.config,
            registry=self.registry,
            permissions=self.permissions,
        )

    def create_subagent(
        self,
        system_prompt: str | None = None,
        allowed_tools: list[str] | None = None,
    ) -> "Agent":  # noqa: F821
        """Create a sub-agent with limited tool access."""
        from open_orchestrator.agent import Agent
        from open_orchestrator.tools.task_tool import (
            DEFAULT_SUBAGENT_TOOLS,
            SUBAGENT_SYSTEM_PROMPT,
        )

        return Agent(
            config=self.config,
            registry=self.registry,
            permissions=self.permissions,
            system_prompt=system_prompt or SUBAGENT_SYSTEM_PROMPT,
            allowed_tools=allowed_tools or DEFAULT_SUBAGENT_TOOLS,
            is_subagent=True,
        )

    async def run_parallel(self, prompts: list[str]) -> list[str]:
        """Run multiple sub-agents in parallel and collect results."""
        tasks = [self.create_subagent().run(prompt) for prompt in prompts]
        return list(await asyncio.gather(*tasks))
