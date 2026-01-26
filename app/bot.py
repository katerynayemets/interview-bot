from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.redis import RedisStorage
from redis.asyncio import Redis

from app.config import settings
from app.routers.start import router as start_router
from app.routers.interview import router as interview_router
from app.routers.menu import router as menu_router

def create_bot() -> Bot:
    return Bot(token=settings.BOT_TOKEN)

async def create_dispatcher() -> Dispatcher:
    redis = Redis.from_url(settings.REDIS_URL)
    storage = RedisStorage(redis=redis)
    dp = Dispatcher(storage=storage)
    dp.include_router(start_router)
    dp.include_router(interview_router)
    dp.include_router(menu_router)
    return dp
