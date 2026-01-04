"""Configuration management for Sasha Sales AI"""

import os
from typing import Optional
from pydantic_settings import BaseSettings
from pydantic import Field


class Settings(BaseSettings):
    """Application settings loaded from environment variables"""

    # LangSmith Configuration
    langsmith_api_key: Optional[str] = Field(default=None, alias="LANGSMITH_API_KEY")
    langsmith_project: str = Field(
        default="sasha-ai-agent-langGraph", alias="LANGSMITH_PROJECT"
    )
    langsmith_tracing: bool = Field(default=True, alias="LANGSMITH_TRACING")

    # LLM Configuration
    openai_api_key: str = Field(default="", alias="OPENAI_API_KEY")
    model_name: str = Field(default="gpt-4o-mini", alias="MODEL_NAME")
    temperature: float = Field(default=0.0)

    # Storage Configuration
    state_storage_path: str = Field(
        default="./state_storage", alias="STATE_STORAGE_PATH"
    )
    
    # Redis Configuration
    redis_url: str = Field(
        default="redis://localhost:6379", alias="REDIS_URL"
    )
    redis_key_prefix: str = Field(
        default="sasha:", alias="REDIS_KEY_PREFIX"
    )

    # API Configuration
    api_host: str = Field(default="0.0.0.0")
    api_port: int = Field(default=8000)

    # Approval Configuration
    approval_threshold: float = Field(default=10000.0)  # Auto-approve below this amount

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "extra": "ignore",
    }

    def setup_environment(self) -> None:
        """Set up environment variables for LangSmith and other services"""
        if self.langsmith_api_key:
            os.environ["LANGSMITH_API_KEY"] = self.langsmith_api_key
        os.environ["LANGSMITH_PROJECT"] = self.langsmith_project
        os.environ["LANGSMITH_TRACING"] = str(self.langsmith_tracing).lower()

        if self.openai_api_key:
            os.environ["OPENAI_API_KEY"] = self.openai_api_key


# Global settings instance
_settings: Optional[Settings] = None


def get_settings() -> Settings:
    """Get or create settings instance"""
    global _settings
    if _settings is None:
        _settings = Settings()
        _settings.setup_environment()
    return _settings

