import asyncio
from aiogram import Bot
from aiogram.methods import SetWebhook
from app.config import settings

async def main():
    bot = Bot(settings.BOT_TOKEN)
    await bot(SetWebhook(
        url=settings.PUBLIC_URL.rstrip("/") + settings.WEBHOOK_PATH,
        secret_token=settings.WEBHOOK_SECRET,
        drop_pending_updates=True,
    ))
    await bot.session.close()

if __name__ == "__main__":
    asyncio.run(main())
