"""Tests for configuration loading."""

from __future__ import annotations

import os
from pathlib import Path

import pytest
import yaml

from open_orchestrator.config import Config, load_config


class TestLoadConfig:
    def test_default_config(self, tmp_path: Path) -> None:
        """Loading with no file should produce defaults."""
        config = load_config(tmp_path / "nonexistent.yaml")
        assert config.llm.base_url == "http://localhost:8000/v1"
        assert config.permissions.default_mode == "ask"
        assert config.agent.max_iterations == 50

    def test_load_from_yaml(self, tmp_path: Path) -> None:
        config_file = tmp_path / "config.yaml"
        config_file.write_text(yaml.dump({
            "llm": {"model": "my-model", "temperature": 0.5},
            "permissions": {"default_mode": "auto"},
        }))
        config = load_config(config_file)
        assert config.llm.model == "my-model"
        assert config.llm.temperature == 0.5
        assert config.permissions.default_mode == "auto"

    def test_env_var_overrides(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("OPENAI_BASE_URL", "http://custom:9000/v1")
        monkeypatch.setenv("OPENAI_MODEL", "custom-model")
        config = load_config(tmp_path / "nonexistent.yaml")
        assert config.llm.base_url == "http://custom:9000/v1"
        assert config.llm.model == "custom-model"

    def test_partial_config(self, tmp_path: Path) -> None:
        config_file = tmp_path / "config.yaml"
        config_file.write_text(yaml.dump({"llm": {"model": "partial-model"}}))
        config = load_config(config_file)
        # Specified values
        assert config.llm.model == "partial-model"
        # Defaults preserved
        assert config.llm.base_url == "http://localhost:8000/v1"
        assert config.permissions.default_mode == "ask"
