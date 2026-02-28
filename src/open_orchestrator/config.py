"""Configuration models and loader."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Literal

import yaml
from pydantic import BaseModel, Field


class LLMConfig(BaseModel):
    base_url: str = "http://localhost:8000/v1"
    api_key: str = "token-dummy"
    model: str = "qwen2.5-coder-32b"
    max_tokens: int = 8192
    temperature: float = 0.0
    tool_choice: str | None = None  # e.g. "auto" requires vLLM --enable-auto-tool-choice


class PermissionsConfig(BaseModel):
    default_mode: Literal["auto", "ask", "deny"] = "ask"
    auto_allow: list[str] = Field(default_factory=lambda: ["read_file", "glob", "grep"])


class AgentConfig(BaseModel):
    max_iterations: int = 50
    system_prompt: str = (
        "You are a helpful AI assistant with access to tools for reading/writing files, "
        "executing shell commands, and searching codebases. Work step by step and explain "
        "what you're doing."
    )


class Config(BaseModel):
    llm: LLMConfig = Field(default_factory=LLMConfig)
    permissions: PermissionsConfig = Field(default_factory=PermissionsConfig)
    agent: AgentConfig = Field(default_factory=AgentConfig)
    working_dir: Path = Field(default_factory=Path.cwd)


def load_config(config_path: Path | None = None) -> Config:
    """Load configuration from YAML file with environment variable overrides."""
    # Default search paths
    search_paths = [
        config_path,
        Path.cwd() / "config.yaml",
        Path.home() / ".config" / "open-orchestrator" / "config.yaml",
    ]

    raw: dict = {}
    for path in search_paths:
        if path and path.exists():
            with open(path) as f:
                raw = yaml.safe_load(f) or {}
            break

    config = Config.model_validate(raw)

    # Environment variable overrides
    if base_url := os.environ.get("OPENAI_BASE_URL"):
        config.llm.base_url = base_url
    if api_key := os.environ.get("OPENAI_API_KEY"):
        config.llm.api_key = api_key
    if model := os.environ.get("OPENAI_MODEL"):
        config.llm.model = model

    return config
