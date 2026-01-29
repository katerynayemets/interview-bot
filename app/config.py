from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # Telegram
    BOT_TOKEN: str
    BOT_MODE: str = "polling"  # polling | webhook

    # Webhook (для production)
    PUBLIC_URL: str | None = None
    WEBHOOK_PATH: str = "/tg/webhook"
    WEBHOOK_SECRET: str = "change_me"

    # Database
    DATABASE_URL: str
    REDIS_URL: str

    # Celery
    CELERY_BROKER_URL: str
    CELERY_RESULT_BACKEND: str

    # === LLM ===
    # OpenAI
    OPENAI_API_KEY: str | None = None
    OPENAI_MODEL: str = "gpt-4o-mini"  # дешёвая модель для training

    # Anthropic (Claude)
    ANTHROPIC_API_KEY: str | None = None
    ANTHROPIC_MODEL: str = "claude-3-5-sonnet-20241022"

    # Какой провайдер использовать по умолчанию
    LLM_PROVIDER: str = "openai"  # openai | anthropic

    # Настройки для разных режимов
    LLM_MODEL_TRAINING: str = "gpt-4o-mini"  # для бесплатного режима
    LLM_MODEL_REAL: str = "gpt-4o"  # для платного режима

    # Лимиты
    LLM_MAX_TOKENS_TRAINING: int = 1024
    LLM_MAX_TOKENS_REAL: int = 2048
    LLM_TEMPERATURE: float = 0.7

    # === Logging ===
    LOG_LEVEL: str = "INFO"

    # === Interview ===
    INTERVIEW_TIMER_ENABLED: bool = True
    INTERVIEW_TIMER_SECONDS: int = 120  # 2 минуты на ответ в real режиме

    class Config:
        env_file = ".env"


settings = Settings()
