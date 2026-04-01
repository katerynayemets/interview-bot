from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    BOT_TOKEN: str
    BOT_MODE: str = "polling"  # polling | webhook

    PUBLIC_URL: str | None = None
    WEBHOOK_PATH: str = "/tg/webhook"
    WEBHOOK_SECRET: str = "change_me"

    DATABASE_URL: str
    REDIS_URL: str

    CELERY_BROKER_URL: str
    CELERY_RESULT_BACKEND: str

    OPENAI_API_KEY: str | None = None
    OPENAI_MODEL: str = "gpt-4o-mini"

    ANTHROPIC_API_KEY: str | None = None
    ANTHROPIC_MODEL: str = "claude-3-5-sonnet-20241022"

    LLM_PROVIDER: str = "openai"  # openai | anthropic
    LLM_MODEL_TRAINING: str = "gpt-4o-mini"
    LLM_MODEL_REAL: str = "gpt-4o"

    LLM_MAX_TOKENS_TRAINING: int = 1024
    LLM_MAX_TOKENS_REAL: int = 2048
    LLM_TEMPERATURE: float = 0.7

    LOG_LEVEL: str = "INFO"

    INTERVIEW_TIMER_ENABLED: bool = True
    INTERVIEW_TIMER_SECONDS: int = 120

    class Config:
        env_file = ".env"


settings = Settings()
