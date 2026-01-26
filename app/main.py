import asyncio
from fastapi import FastAPI, Request, Header, HTTPException

from aiogram.types import Update
from aiogram.methods import SetWebhook, DeleteWebhook

from app.config import settings
from app.bot import create_bot, create_dispatcher
from app.db.base import Base
from app.db.session import engine

app = FastAPI()
bot = create_bot()
dp = None
polling_task: asyncio.Task | None = None

from aiogram.types import BotCommand, BotCommandScopeAllPrivateChats, MenuButtonCommands
from aiogram.methods import SetChatMenuButton

async def setup_commands(bot):
    # RU
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

    # UK
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

    # EN
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

    # Попросим Telegram показать меню именно с командами
    await bot(SetChatMenuButton(menu_button=MenuButtonCommands()))


@app.on_event("startup")
async def on_startup():
    global dp, polling_task
    dp = await create_dispatcher()

    # create tables (MVP). Дальше сделаем Alembic.
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    if settings.BOT_MODE == "webhook":
        if not settings.PUBLIC_URL:
            raise RuntimeError("PUBLIC_URL is required for webhook mode")

        await bot(DeleteWebhook(drop_pending_updates=True))
        await bot(SetWebhook(
            url=settings.PUBLIC_URL.rstrip("/") + settings.WEBHOOK_PATH,
            secret_token=settings.WEBHOOK_SECRET,
            drop_pending_updates=True,
        ))
    else:
        # polling mode for local quick check
        polling_task = asyncio.create_task(dp.start_polling(bot))

@app.on_event("shutdown")
async def on_shutdown():
    if settings.BOT_MODE == "webhook":
        await bot(DeleteWebhook(drop_pending_updates=True))
    if polling_task:
        polling_task.cancel()
    await bot.session.close()

@app.get("/health")
async def health():
    return {"ok": True, "mode": settings.BOT_MODE}

@app.post("/tg/webhook")
async def telegram_webhook(
    request: Request,
    x_telegram_bot_api_secret_token: str | None = Header(default=None),
):
    if settings.BOT_MODE != "webhook":
        raise HTTPException(400, "Webhook endpoint is disabled in polling mode")

    if x_telegram_bot_api_secret_token != settings.WEBHOOK_SECRET:
        raise HTTPException(401, "Bad webhook secret")

    data = await request.json()
    update = Update.model_validate(data)
    await dp.feed_update(bot, update)
    return {"ok": True}


