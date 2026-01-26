# app/utils/lang.py
from aiogram.fsm.context import FSMContext
from app.db.session import SessionLocal
from app.db import crud

DEFAULT_LANG = "uk"

async def resolve_lang(state: FSMContext, chat_id: int) -> str:
    data = await state.get_data()
    lang = data.get("lang")
    if lang:
        return lang

    async with SessionLocal() as db:
        s = await crud.get_latest_session(db, chat_id)
        if s and getattr(s, "language", None):
            lang = s.language
            await state.update_data(lang=lang)
            return lang

    await state.update_data(lang=DEFAULT_LANG)
    return DEFAULT_LANG
