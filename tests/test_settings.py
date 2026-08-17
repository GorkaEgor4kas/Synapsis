# tests/test_settings.py

"""Tests for settings loading and validation."""

import os
from pathlib import Path

import pytest

from synapsis.config.settings import Settings


@pytest.fixture
def clean_env(monkeypatch):
    """Remove relevant env vars before each test."""
    env_vars = [
        "LLM_API_KEY",
        "LLM_MODEL",
        "DEEPSEEK_API_KEY",
        "OBSIDIAN_VAULT_PATH",
        "MEMEX_INDEX_PATH",
        "VOICE_STT_ENGINE",
        "VOICE_TTS_ENGINE",
        "WHISPER_MODEL",
        "PIPER_VOICE",
        "SANDBOX_TIMEOUT_SECONDS",
        "SANDBOX_MAX_MEMORY_MB",
        "SANDBOX_ALLOW_DANGEROUS_PACKAGES",
        "DATABASE_PATH",
        "LOG_LEVEL",
        "BLACKBOARD_PERSIST",
    ]
    for var in env_vars:
        monkeypatch.delenv(var, raising=False)


def test_defaults(clean_env):
    """Settings load with sensible defaults."""
    settings = Settings()

    assert settings.llm_api_key == ""
    assert settings.llm_model == "llama-3.1-70b-versatile"
    assert settings.obsidian_vault_path == ""
    assert settings.sandbox_timeout_seconds == 120
    assert settings.log_level == "INFO"
    assert settings.is_configured is False


def test_env_override(clean_env, monkeypatch):
    """Environment variables override defaults."""
    monkeypatch.setenv("LLM_API_KEY", "test-key")
    monkeypatch.setenv("LLM_MODEL", "llama-3.1-8b-instant")
    monkeypatch.setenv("SANDBOX_TIMEOUT_SECONDS", "60")

    settings = Settings()

    assert settings.llm_api_key == "test-key"
    assert settings.llm_model == "llama-3.1-8b-instant"
    assert settings.sandbox_timeout_seconds == 60


def test_db_path_default(clean_env, monkeypatch):
    """Database path defaults to ~/.synapsis/sessions.db."""
    monkeypatch.setenv("HOME", "/tmp/test-home")

    settings = Settings()

    assert settings.db_path == Path("/tmp/test-home/.synapsis/sessions.db")


def test_db_path_override(clean_env, monkeypatch):
    """Database path can be overridden."""
    monkeypatch.setenv("DATABASE_PATH", "/custom/path/sessions.db")

    settings = Settings()

    assert settings.db_path == Path("/custom/path/sessions.db")


def test_memex_path_default(clean_env, monkeypatch):
    """Memex path defaults to {vault}/.memex."""
    monkeypatch.setenv("OBSIDIAN_VAULT_PATH", "/home/user/vault")

    settings = Settings()

    assert settings.vault_path == Path("/home/user/vault")
    assert settings.memex_path == Path("/home/user/vault/.memex")


def test_validate_for_startup_fails_when_missing(clean_env, monkeypatch):
    """Startup validation raises if required settings are missing."""
    monkeypatch.setenv("LLM_API_KEY", "test-key")
    # OBSIDIAN_VAULT_PATH not set

    settings = Settings()

    with pytest.raises(ValueError, match="OBSIDIAN_VAULT_PATH"):
        settings.validate_for_startup()


def test_validate_for_startup_succeeds_when_configured(clean_env, monkeypatch, tmp_path):
    """Startup validation passes when required settings exist."""
    monkeypatch.setenv("LLM_API_KEY", "test-key")
    monkeypatch.setenv("OBSIDIAN_VAULT_PATH", str(tmp_path))

    settings = Settings()
    settings.validate_for_startup()  # Should not raise


def test_display_masks_secrets(clean_env, monkeypatch):
    """Display doesn't leak API keys."""
    monkeypatch.setenv("LLM_API_KEY", "super-secret-key")
    monkeypatch.setenv("OBSIDIAN_VAULT_PATH", "/home/user/vault")

    settings = Settings()
    display = settings.display()

    assert "super-secret-key" not in display
    assert "/home/user/vault" in display
    assert "✅ Yes" in display