"""Core agent loop."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING, Any

from openai import AsyncOpenAI

from open_orchestrator.config import Config
from open_orchestrator.tools import ToolCall, ToolRegistry

if TYPE_CHECKING:
    from open_orchestrator.permissions import PermissionManager

# Message type aliases
Message = dict[str, Any]


class Agent:
    """A single agent instance that runs the LLM + tool loop."""

    def __init__(
        self,
        config: Config,
        registry: ToolRegistry,
        permissions: "PermissionManager",
        system_prompt: str | None = None,
        allowed_tools: list[str] | None = None,
        is_subagent: bool = False,
    ) -> None:
        self.config = config
        self.registry = registry
        self.permissions = permissions
        self.system_prompt = system_prompt or config.agent.system_prompt
        self.allowed_tools = allowed_tools  # None = all tools
        self.is_subagent = is_subagent
        self.messages: list[Message] = []

        self._client = AsyncOpenAI(
            base_url=config.llm.base_url,
            api_key=config.llm.api_key,
        )

    def reset(self) -> None:
        """Clear conversation history."""
        self.messages = []

    def _build_tools_schema(self) -> list[dict[str, Any]]:
        """Build the tools schema for the LLM call."""
        return self.registry.to_openai_schema(allowed=self.allowed_tools)

    async def run(self, user_message: str) -> str:
        """
        Run the agent with a user message.
        Returns the final text response.
        """
        from open_orchestrator import display

        self.messages.append({"role": "user", "content": user_message})

        for iteration in range(self.config.agent.max_iterations):
            tools_schema = self._build_tools_schema()

            # Build the API call parameters
            call_params: dict[str, Any] = {
                "model": self.config.llm.model,
                "messages": [
                    {"role": "system", "content": self.system_prompt},
                    *self.messages,
                ],
                "max_tokens": self.config.llm.max_tokens,
                "temperature": self.config.llm.temperature,
            }
            if tools_schema:
                call_params["tools"] = tools_schema
                if self.config.llm.tool_choice is not None:
                    call_params["tool_choice"] = self.config.llm.tool_choice

            try:
                # Stream for final text responses; non-stream for tool calls
                # We use non-streaming first to detect finish_reason efficiently
                response = await self._client.chat.completions.create(
                    stream=False,
                    **call_params,
                )
            except Exception as e:
                error_msg = f"LLM API error: {e}"
                display.print_error(error_msg)
                return error_msg

            choice = response.choices[0]
            finish_reason = choice.finish_reason
            message = choice.message

            # Append assistant message to history
            assistant_msg: Message = {"role": "assistant"}
            if message.content:
                assistant_msg["content"] = message.content
            if message.tool_calls:
                assistant_msg["tool_calls"] = [
                    {
                        "id": tc.id,
                        "type": "function",
                        "function": {
                            "name": tc.function.name,
                            "arguments": tc.function.arguments,
                        },
                    }
                    for tc in message.tool_calls
                ]
            self.messages.append(assistant_msg)

            # If we have a final text response, display and return it
            if finish_reason == "stop" or not message.tool_calls:
                final_text = message.content or ""
                if final_text and not self.is_subagent:
                    display.print_assistant_text(final_text)
                return final_text

            # Process tool calls
            if message.content and not self.is_subagent:
                display.print_info(message.content)

            tool_results = await self._execute_tool_calls(message.tool_calls)

            # Add tool results to messages
            for tool_call_id, result in tool_results:
                self.messages.append({
                    "role": "tool",
                    "tool_call_id": tool_call_id,
                    "content": result,
                })

            # Check if user requested quit
            if self.permissions.quit_requested:
                return "Session terminated by user."

        return "Error: Maximum iterations reached without completing the task."

    async def _execute_tool_calls(
        self,
        tool_calls: list[Any],
    ) -> list[tuple[str, str]]:
        """Execute tool calls and return (id, result) pairs."""
        from open_orchestrator import display
        import asyncio

        async def execute_one(tc: Any) -> tuple[str, str]:
            try:
                arguments = json.loads(tc.function.arguments)
            except json.JSONDecodeError:
                arguments = {}

            call = ToolCall(
                id=tc.id,
                name=tc.function.name,
                arguments=arguments,
            )

            tool = self.registry.get(call.name)

            if not self.is_subagent:
                display.print_tool_call(call.name, call.arguments)

            permitted = await self.permissions.check(call, tool)
            if not permitted:
                result = f"Tool '{call.name}' was not permitted."
                if not self.is_subagent:
                    display.print_tool_result(call.name, result, success=False)
                return (call.id, result)

            result = await self.registry.execute(call)

            if not self.is_subagent:
                success = not result.startswith("Error")
                display.print_tool_result(call.name, result, success=success)

            return (call.id, result)

        # Execute all tool calls (potentially in parallel)
        if len(tool_calls) == 1:
            return [await execute_one(tool_calls[0])]
        else:
            return list(await asyncio.gather(*[execute_one(tc) for tc in tool_calls]))

    async def run_streaming(self, user_message: str) -> str:
        """
        Run with streaming for the final text response.
        Uses non-streaming for tool-call iterations.
        """
        from open_orchestrator import display
        from rich.live import Live
        from rich.text import Text

        self.messages.append({"role": "user", "content": user_message})

        for iteration in range(self.config.agent.max_iterations):
            tools_schema = self._build_tools_schema()

            call_params: dict[str, Any] = {
                "model": self.config.llm.model,
                "messages": [
                    {"role": "system", "content": self.system_prompt},
                    *self.messages,
                ],
                "max_tokens": self.config.llm.max_tokens,
                "temperature": self.config.llm.temperature,
            }
            if tools_schema:
                call_params["tools"] = tools_schema
                if self.config.llm.tool_choice is not None:
                    call_params["tool_choice"] = self.config.llm.tool_choice

            # First do a non-streaming call to determine finish_reason
            try:
                response = await self._client.chat.completions.create(
                    stream=False,
                    **call_params,
                )
            except Exception as e:
                error_msg = f"LLM API error: {e}"
                display.print_error(error_msg)
                return error_msg

            choice = response.choices[0]
            finish_reason = choice.finish_reason
            message = choice.message

            assistant_msg: Message = {"role": "assistant"}
            if message.content:
                assistant_msg["content"] = message.content
            if message.tool_calls:
                assistant_msg["tool_calls"] = [
                    {
                        "id": tc.id,
                        "type": "function",
                        "function": {
                            "name": tc.function.name,
                            "arguments": tc.function.arguments,
                        },
                    }
                    for tc in message.tool_calls
                ]
            self.messages.append(assistant_msg)

            if finish_reason == "stop" or not message.tool_calls:
                final_text = message.content or ""
                if final_text and not self.is_subagent:
                    display.print_assistant_text(final_text)
                return final_text

            if message.content and not self.is_subagent:
                display.print_info(message.content)

            tool_results = await self._execute_tool_calls(message.tool_calls)

            for tool_call_id, result in tool_results:
                self.messages.append({
                    "role": "tool",
                    "tool_call_id": tool_call_id,
                    "content": result,
                })

            if self.permissions.quit_requested:
                return "Session terminated by user."

        return "Error: Maximum iterations reached without completing the task."
