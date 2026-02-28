"""Task tool for launching sub-agents."""

from __future__ import annotations

from typing import TYPE_CHECKING

from open_orchestrator.tools import Tool, register_tool

if TYPE_CHECKING:
    from open_orchestrator.config import Config
    from open_orchestrator.permissions import PermissionManager
    from open_orchestrator.tools import ToolRegistry

SUBAGENT_SYSTEM_PROMPT = """You are a focused sub-agent assistant. Complete the specific task
assigned to you using the available tools. Be concise and return a clear result.
Do not ask clarifying questions - make reasonable assumptions and proceed."""

# Tools available to sub-agents by default (excludes 'task' to prevent recursion)
DEFAULT_SUBAGENT_TOOLS = [
    "read_file",
    "write_file",
    "edit_file",
    "bash",
    "glob",
    "grep",
]


def make_task_handler(
    config: "Config",
    registry: "ToolRegistry",
    permissions: "PermissionManager",
) -> object:
    """Create a task handler bound to config/registry/permissions."""

    async def task(
        prompt: str,
        tools: list[str] | None = None,
        system_prompt: str | None = None,
    ) -> str:
        """
        Launch a sub-agent to complete a specific task.
        Returns the sub-agent's final response.
        """
        from open_orchestrator.agent import Agent
        from open_orchestrator import display

        allowed = tools or DEFAULT_SUBAGENT_TOOLS
        sub_system = system_prompt or SUBAGENT_SYSTEM_PROMPT

        display.print_info(f"[Sub-agent] Starting task: {prompt[:80]}...")

        sub_agent = Agent(
            config=config,
            registry=registry,
            permissions=permissions,
            system_prompt=sub_system,
            allowed_tools=allowed,
            is_subagent=True,
        )

        result = await sub_agent.run(prompt)
        display.print_info(f"[Sub-agent] Task completed.")
        return result

    return task


def register_task_tool(
    config: "Config",
    registry: "ToolRegistry",
    permissions: "PermissionManager",
) -> None:
    """Register the task tool into the global registry."""
    handler = make_task_handler(config, registry, permissions)

    register_tool(Tool(
        name="task",
        description=(
            "Launch a sub-agent to complete a specific task. "
            "Use this for parallel investigation of independent sub-problems. "
            "The sub-agent has access to file and search tools. "
            "Returns the sub-agent's complete response."
        ),
        parameters_schema={
            "type": "object",
            "properties": {
                "prompt": {
                    "type": "string",
                    "description": "The task or question for the sub-agent to address",
                },
                "tools": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": (
                        "List of tool names the sub-agent can use. "
                        f"Defaults to: {DEFAULT_SUBAGENT_TOOLS}"
                    ),
                },
                "system_prompt": {
                    "type": "string",
                    "description": "Custom system prompt for the sub-agent (optional)",
                },
            },
            "required": ["prompt"],
        },
        handler=handler,
        requires_permission=False,
    ))
