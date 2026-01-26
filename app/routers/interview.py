from aiogram import Router, F
from aiogram.types import Message
from aiogram.fsm.context import FSMContext

from app.states import InterviewFSM
from app.db.session import SessionLocal
from app.db import crud
from app.worker.tasks import generate_snapshot
from app.i18n import tr, DEFAULT_LANG

router = Router()


async def resolve_lang(state: FSMContext, chat_id: int) -> str:
    data = await state.get_data()
    if data.get("lang"):
        return data["lang"]

    async with SessionLocal() as db:
        us = await crud.ensure_user_settings(db, chat_id)
        lang = us.language or DEFAULT_LANG

    await state.update_data(lang=lang)
    return lang


@router.message(InterviewFSM.q1, F.text & ~F.text.startswith("/"))
async def q1(msg: Message, state: FSMContext):
    data = await state.get_data()
    lang = await resolve_lang(state, msg.chat.id)
    session_id = data["session_id"]

    async with SessionLocal() as db:
        await crud.add_message(db, session_id, role="user", kind="answer", text=msg.text)
        await crud.add_answer(db, session_id, "q1", msg.text)  # legacy
        await crud.add_message(db, session_id, role="assistant", kind="question", text=tr(lang, "q2"))
        await db.commit()

    await msg.answer(tr(lang, "q2"))
    await state.set_state(InterviewFSM.q2)


@router.message(InterviewFSM.q2, F.text & ~F.text.startswith("/"))
async def q2(msg: Message, state: FSMContext):
    data = await state.get_data()
    lang = await resolve_lang(state, msg.chat.id)
    session_id = data["session_id"]

    async with SessionLocal() as db:
        await crud.add_message(db, session_id, role="user", kind="answer", text=msg.text)
        await crud.add_answer(db, session_id, "q2", msg.text)  # legacy
        await crud.add_message(db, session_id, role="assistant", kind="question", text=tr(lang, "q3"))
        await db.commit()

    await msg.answer(tr(lang, "q3"))
    await state.set_state(InterviewFSM.q3)


@router.message(InterviewFSM.q3, F.text & ~F.text.startswith("/"))
async def q3(msg: Message, state: FSMContext):
    data = await state.get_data()
    lang = await resolve_lang(state, msg.chat.id)
    session_id = data["session_id"]

    async with SessionLocal() as db:
        await crud.add_message(db, session_id, role="user", kind="answer", text=msg.text)
        await crud.add_answer(db, session_id, "q3", msg.text)  # legacy
        await crud.add_message(db, session_id, role="assistant", kind="event", text=tr(lang, "generating"))
        await db.commit()

    await msg.answer(tr(lang, "generating"))
    generate_snapshot.delay(session_id=session_id, chat_id=msg.chat.id, lang=lang)

    await state.clear()
    await state.update_data(lang=lang)
