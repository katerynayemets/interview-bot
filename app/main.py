import asyncio
from fastapi import FastAPI, Request, Header, HTTPException

from aiogram.types import Update
from aiogram.methods import SetWebhook, DeleteWebhook

from app.config import settings
from app.bot import create_bot, create_dispatcher
from app.db.base import Base
from app.db.session import engine
from app.logging_config import setup_logging, get_logger
from app.middleware import setup_middlewares

setup_logging(
    log_level=settings.LOG_LEVEL if hasattr(settings, "LOG_LEVEL") else "INFO",
    log_to_file=True,
    log_to_console=True,
)

logger = get_logger(__name__)

app = FastAPI(title="Interview Bot API", version="1.0.0")
bot = create_bot()
dp = None
polling_task: asyncio.Task | None = None

from aiogram.types import BotCommand, BotCommandScopeAllPrivateChats, MenuButtonCommands
from aiogram.methods import SetChatMenuButton


async def setup_commands(bot):
    """Configure bot command menu for all supported locales."""
    await bot.set_my_commands(
        commands=[
            BotCommand(command="start", description="Запуск / новый прогон"),
            BotCommand(command="help", description="Помощь"),
            BotCommand(command="settings", description="Настройки"),
            BotCommand(command="language", description="Сменить язык"),
            BotCommand(command="mode", description="Сменить режим"),
            BotCommand(command="cancel", description="Отменить текущий шаг"),
        ],
        scope=BotCommandScopeAllPrivateChats(),
        language_code="ru",
    )

    await bot.set_my_commands(
        commands=[
            BotCommand(command="start", description="Старт / новий прогін"),
            BotCommand(command="help", description="Допомога"),
            BotCommand(command="settings", description="Налаштування"),
            BotCommand(command="language", description="Змінити мову"),
            BotCommand(command="mode", description="Змінити режим"),
            BotCommand(command="cancel", description="Скасувати поточний крок"),
        ],
        scope=BotCommandScopeAllPrivateChats(),
        language_code="uk",
    )

    await bot.set_my_commands(
        commands=[
            BotCommand(command="start", description="Start / new run"),
            BotCommand(command="help", description="Help"),
            BotCommand(command="settings", description="Settings"),
            BotCommand(command="language", description="Change language"),
            BotCommand(command="mode", description="Change mode"),
            BotCommand(command="cancel", description="Cancel current step"),
        ],
        scope=BotCommandScopeAllPrivateChats(),
        language_code="en",
    )

    await bot(SetChatMenuButton(menu_button=MenuButtonCommands()))


@app.on_event("startup")
async def on_startup():
    global dp, polling_task

    logger.info("Starting Interview Bot...")

    dp = await create_dispatcher()

    setup_middlewares(dp)
    logger.info("Middlewares registered")

    # Fallback table creation; primary schema management is via Alembic
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("Database tables verified")

    try:
        await setup_commands(bot)
        logger.info("Bot commands configured")
    except Exception as e:
        logger.warning(f"Failed to setup bot commands: {e}")

    if settings.BOT_MODE == "webhook":
        if not settings.PUBLIC_URL:
            raise RuntimeError("PUBLIC_URL is required for webhook mode")

        await bot(DeleteWebhook(drop_pending_updates=True))
        await bot(SetWebhook(
            url=settings.PUBLIC_URL.rstrip("/") + settings.WEBHOOK_PATH,
            secret_token=settings.WEBHOOK_SECRET,
            drop_pending_updates=True,
        ))
        logger.info(f"Webhook mode: {settings.PUBLIC_URL}{settings.WEBHOOK_PATH}")
    else:
        polling_task = asyncio.create_task(dp.start_polling(bot))
        logger.info("Polling mode started")

    logger.info("Interview Bot started successfully!")


@app.on_event("shutdown")
async def on_shutdown():
    logger.info("Shutting down Interview Bot...")

    if settings.BOT_MODE == "webhook":
        await bot(DeleteWebhook(drop_pending_updates=True))

    if polling_task:
        polling_task.cancel()
        try:
            await polling_task
        except asyncio.CancelledError:
            pass

    await bot.session.close()
    logger.info("Interview Bot stopped")


@app.get("/health")
async def health():
    """Health check endpoint."""
    return {
        "ok": True,
        "mode": settings.BOT_MODE,
        "version": "1.0.0",
    }


@app.post("/tg/webhook")
async def telegram_webhook(
    request: Request,
    x_telegram_bot_api_secret_token: str | None = Header(default=None),
):
    """Telegram webhook endpoint."""
    if settings.BOT_MODE != "webhook":
        raise HTTPException(400, "Webhook endpoint is disabled in polling mode")

    if x_telegram_bot_api_secret_token != settings.WEBHOOK_SECRET:
        logger.warning("Webhook request with invalid secret token")
        raise HTTPException(401, "Bad webhook secret")

    data = await request.json()
    update = Update.model_validate(data)

    try:
        await dp.feed_update(bot, update)
    except Exception as e:
        logger.exception(f"Error processing update: {e}")
        # Suppress error so Telegram does not retry the update
        pass

    return {"ok": True}


@app.get("/api/stats")
async def get_stats():
    """Admin statistics endpoint."""
    from sqlalchemy import select, func
    from app.db.session import SessionLocal
    from app.db.models import UserSettings, Session, UserActivity, ErrorLog

    async with SessionLocal() as db:
        users_result = await db.execute(select(func.count(UserSettings.chat_id)))
        total_users = users_result.scalar() or 0

        sessions_result = await db.execute(select(func.count(Session.id)))
        total_sessions = sessions_result.scalar() or 0

        from datetime import datetime, timedelta
        day_ago = datetime.utcnow() - timedelta(days=1)
        errors_result = await db.execute(
            select(func.count(ErrorLog.id)).where(ErrorLog.created_at > day_ago)
        )
        errors_24h = errors_result.scalar() or 0

    return {
        "total_users": total_users,
        "total_sessions": total_sessions,
        "errors_24h": errors_24h,
    }
