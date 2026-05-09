from typing import List
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Application
    app_env: str = "development"
    debug: bool = False
    secret_key: str = "change-me"

    # Database
    database_url: str = Field(..., alias="DATABASE_URL")

    # Redis
    redis_url: str = Field("redis://localhost:6379/0", alias="REDIS_URL")

    # Anthropic
    anthropic_api_key: str = Field(..., alias="ANTHROPIC_API_KEY")
    anthropic_model_fast: str = Field("claude-haiku-4-5-20251001", alias="ANTHROPIC_MODEL_FAST")
    anthropic_model_smart: str = Field("claude-sonnet-4-6", alias="ANTHROPIC_MODEL_SMART")
    anthropic_max_tokens: int = Field(8192, alias="ANTHROPIC_MAX_TOKENS")

    # OpenAI (embeddings)
    openai_api_key: str = Field("", alias="OPENAI_API_KEY")

    # Clerk
    clerk_secret_key: str = Field("", alias="CLERK_SECRET_KEY")
    clerk_publishable_key: str = Field("", alias="CLERK_PUBLISHABLE_KEY")
    clerk_webhook_secret: str = Field("", alias="CLERK_WEBHOOK_SECRET")

    # Encryption
    encryption_key: str = Field("", alias="ENCRYPTION_KEY")

    # LangSmith
    langchain_tracing_v2: bool = Field(False, alias="LANGCHAIN_TRACING_V2")
    langsmith_api_key: str = Field("", alias="LANGSMITH_API_KEY")
    langchain_project: str = Field("aria", alias="LANGCHAIN_PROJECT")

    # AWS / S3
    aws_access_key_id: str = Field("", alias="AWS_ACCESS_KEY_ID")
    aws_secret_access_key: str = Field("", alias="AWS_SECRET_ACCESS_KEY")
    aws_region: str = Field("us-east-1", alias="AWS_REGION")
    s3_bucket_name: str = Field("aria-outputs", alias="S3_BUCKET_NAME")

    # CORS
    allowed_origins: str = Field("http://localhost:3000", alias="ALLOWED_ORIGINS")

    @property
    def cors_origins(self) -> List[str]:
        return [o.strip() for o in self.allowed_origins.split(",") if o.strip()]

    # Schema Brain
    schema_cache_ttl: int = Field(3600, alias="SCHEMA_CACHE_TTL")

    # Agent system
    sql_agent_max_retries: int = Field(3, alias="SQL_AGENT_MAX_RETRIES")
    redis_cache_ttl: int = Field(3600, alias="REDIS_CACHE_TTL")

    # Feature flags
    feature_proactive_agent: bool = Field(False, alias="FEATURE_PROACTIVE_AGENT")
    feature_google_slides: bool = Field(False, alias="FEATURE_GOOGLE_SLIDES")
    feature_weasyprint: bool = Field(False, alias="FEATURE_WEASYPRINT")


settings = Settings()
