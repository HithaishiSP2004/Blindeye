from typing import List
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application configuration settings loaded from environment or .env file."""

    APP_ENV: str = Field(default="development", description="Application environment")
    APP_PORT: int = Field(default=8000, description="Server listening port")
    APP_HOST: str = Field(default="127.0.0.1", description="Server listening host")
    CORS_ORIGINS: str = Field(
        default="*",
        description="Comma-separated allowed origins for CORS (default: * for universal deployment compatibility)",
    )

    GEMINI_API_KEY: str = Field(
        default="",
        description="API key for Gemini model calls",
    )
    GEMINI_MODEL: str = Field(
        default="gemini-3.8-flash",
        description="Configurable Gemini primary model identifier (e.g. gemini-3.8-flash)",
    )
    GEMINI_FALLBACK_MODELS: str = Field(
        default="gemini-3.7-flash,gemini-3.6-flash",
        description="Comma-separated fallback Gemini model identifiers in priority order",
    )

    MAX_FILE_SIZE_MB: int = Field(default=15, description="Maximum file upload size in MB")
    MAX_PAGE_COUNT: int = Field(default=30, description="Maximum allowed document page count")

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    @property
    def cors_origins_list(self) -> List[str]:
        """Convert comma-separated CORS string to clean list."""
        return [origin.strip() for origin in self.CORS_ORIGINS.split(",") if origin.strip()]

    @property
    def gemini_fallback_models_list(self) -> List[str]:
        """Convert comma-separated fallback models string to clean list."""
        return [m.strip() for m in self.GEMINI_FALLBACK_MODELS.split(",") if m.strip()]

    @property
    def gemini_models_cascade(self) -> List[str]:
        """Return full cascade of Gemini models to attempt: [primary, *fallbacks] without duplicates."""
        models = [self.GEMINI_MODEL]
        for fb in self.gemini_fallback_models_list:
            if fb not in models:
                models.append(fb)
        return models


settings = Settings()
