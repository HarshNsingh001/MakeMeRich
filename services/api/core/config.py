from pydantic_settings import BaseSettings, SettingsConfigDict
from functools import lru_cache


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # App
    app_env: str = "development"
    log_level: str = "INFO"
    secret_key: str = "change_this_in_production"

    # AWS / S3 Storage
    aws_access_key_id: Optional[str] = None
    aws_secret_access_key: Optional[str] = None
    aws_region: str = "ap-south-1"
    s3_bucket_name: Optional[str] = None

    # Database
    postgres_host: str = "localhost"
    postgres_port: int = 5432
    postgres_db: str = "makemerich"
    postgres_user: str = "makemerich"
    postgres_password: str = "makemerich_dev"

    # Redis
    redis_url: str = "redis://localhost:6379/0"

    # Broker APIs
    angel_one_api_key: str = ""
    angel_one_client_id: str = ""
    angel_one_pin: str = ""
    angel_one_totp_secret: str = ""

    fyers_client_id: str = ""
    fyers_secret_key: str = ""

    # LLM Providers (User fills the one they want to use)
    active_llm_provider: str = "openai"  # Options: openai, gemini, anthropic
    openai_api_key: str = ""
    gemini_api_key: str = ""
    anthropic_api_key: str = ""

    @property
    def database_url(self) -> str:
        return (
            f"postgresql+asyncpg://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )

    @property
    def database_url_sync(self) -> str:
        return (
            f"postgresql+psycopg2://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )


@lru_cache
def get_settings() -> Settings:
    return Settings()
