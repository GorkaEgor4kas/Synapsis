"""Application settings loaded from environment variables.

Uses pydantic-settings to validate and type-check configuration.
Values are loaded from a .env file in the project root, or from
actual environment variables (which take precedence).
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Typed application settings.

    All fields can be overridden via environment variables or a .env file.
    Field names map to env vars case-insensitively.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    # ------ LLM Provider ------
    llm_api_key: str = Field(
        default="",
        description="LLM API key",
    )

    llm_model: str = Field(
        default="",
        description="model to use for LLM calls",
    )

    # ------ Obsidian Vault ------

    obsidian_vault_path: str = Field(
        default="",
        description="Absolute path to your Obsidian vault",
    )

    memex_index_path: str | None = Field(
        default = None,
        description="Memex index location",
    )


    # ------ Voice I/O ------

    voice_stt_engine: Literal["whisper_local", "whisper_api"] = Field(
        default="whisper_local",
        description="Speech-to-text engine",
    )

    whisper_model: str = Field(
        default="base",
        description="Whisper model size: tiny, base, small, medium, large",
    )

    whisper_language: str | None = Field(
        default=None,
        description="Whisper language code (e.g., 'en', 'ru'). Auto-detect if None.",
    )

    voice_tts_engine: Literal["piper_local", "elevenlabs"] = Field(
        default="piper_local",
        description="Text-to-speech engine",
    )

    piper_voice: str = Field(
        default="en_US-lessac-medium",
        description="Piper voice model name",
    )

    elevenlabs_api_key: str = Field(
        default="",
        description="ElevenLabs API key (only needed if voice_tts_engine=elevenlabs)",
    )


    # ------ Sandbox ------

    sandbox_timeout_seconds: int = Field(
        default=120,
        ge=5,
        le=300,
        description="Maximum execution time for sandboxed code",
    )
    sandbox_max_memory_mb: int = Field(
        default=512,
        ge=64,
        le=4096,
        description="Maximum memory for sandbox subprocess",
    )
    sandbox_allow_dangerous_packages: bool = Field(
        default=False,
        description="Allow packages outside the whitelist (dangerous!)",
    )


    # ------ Database ------

    database_path: str | None = Field(
        default=None,
        description="SQLite database location. Defaults to ~/.synapsis/sessions.db",
    )


    # ------ Debugging ------

    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR"] = Field(
        default="INFO",
        description="Logging level",
    )
    blackboard_persist: bool = Field(
        default=False,
        description="Persist Blackboard entries to database",
    )

    # ------ Derived ------

    @property
    def vault_path(self) -> Path:
        """Obsidian vault path as a Path object."""
        return Path(self.obsidian_vault_path)

    @property
    def memex_path(self) -> Path:
        """Memex index path, defaulting to {vault_path}/.memex."""
        if self.memex_index_path:
            return Path(self.memex_index_path)
        return self.vault_path / ".memex"

    @property
    def db_path(self) -> Path:
        """SQLite database path, defaulting to ~/.synapsis/sessions.db."""
        if self.database_path:
            return Path(self.database_path)
        return Path.home() / ".synapsis" / "sessions.db"

    @property
    def is_configured(self) -> bool:
        """True if the minimum required configuration is present."""
        return bool(self.llm_api_key and self.obsidian_vault_path)


    def validate_for_startup(self) -> None:
        """Raise ValueError if required settings are missing.

        Called by the CLI before starting any work.
        """

        missing: list[str] = []

        if not self.llm_api_key:
            missing.append("LLM_API_KEY")

        if not self.obsidian_vault_path:
            missing.append("OBSIDIAN_VAULT_PATH")

        if missing:
            raise ValueError(
                "Missing required configuration: "
                + ", ".join(missing)
                + ". Copy .env.example to .env and fill in the values."
            )

        if not self.vault_path.exists():
            raise ValueError(
                f"Obsidian vault path does not exist: {self.obsidian_vault_path}"
            )

    def display(self) -> str:
        """Human-readable summary of non-sensitive settings.

        Used by the CLI `synapsis config` command to show current setup.
        """
        return "\n".join(
            [
                "Synapsis Configuration",
                "──────────────────────",
                f"Obsidian vault:  {self.obsidian_vault_path or '(not set)'}",
                f"llm model:      {self.llm_model}",
                f"STT engine:      {self.voice_stt_engine}",
                f"TTS engine:      {self.voice_tts_engine}",
                f"Sandbox timeout: {self.sandbox_timeout_seconds}s",
                f"Database:        {self.db_path}",
                f"Log level:       {self.log_level}",
                f"Configured:      {'✅ Yes' if self.is_configured else '❌ No'}",
            ]
        )


@lru_cache
def get_settings() -> Settings:
    """Return a cached Settings instance."""
    return Settings()