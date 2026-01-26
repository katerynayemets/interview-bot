from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    BOT_TOKEN: str
    BOT_MODE: str = "polling"

    PUBLIC_URL: str | None = None
    WEBHOOK_PATH: str = "/tg/webhook"
    WEBHOOK_SECRET: str = "change_me"

    DATABASE_URL: str
    REDIS_URL: str

    CELERY_BROKER_URL: str
    CELERY_RESULT_BACKEND: str

    class Config:
        env_file = ".env"

settings = Settings()
