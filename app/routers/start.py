# app/routers/start.py
import asyncio
from urllib.parse import urlparse

from aiogram import Router, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import (
    Message, CallbackQuery,
    ReplyKeyboardMarkup, KeyboardButton,
)
from aiogram.utils.keyboard import InlineKeyboardBuilder

from app.db.session import SessionLocal
from app.db import crud
from app.i18n import tr
from app.states import InterviewFSM
from app.worker.pdf_reader import read_pdf_text
from app.worker.tasks import fetch_vacancy

router = Router()


def track_kb(lang: str):
    kb = InlineKeyboardBuilder()
    kb.button(text=tr(lang, "btn_track_data"), callback_data="track:data")
    kb.adjust(1)
    return kb.as_markup()


def lang_kb(lang: str):
    kb = InlineKeyboardBuilder()
    kb.button(text=tr(lang, "btn_lang_uk"), callback_data="lang:uk")
    kb.button(text=tr(lang, "btn_lang_ru"), callback_data="lang:ru")
    kb.button(text=tr(lang, "btn_lang_en"), callback_data="lang:en")
    kb.adjust(3)
    return kb.as_markup()


def mode_kb(lang: str):
    kb = InlineKeyboardBuilder()
    kb.button(text=tr(lang, "btn_mode_training"), callback_data="mode:training")
    kb.button(text=tr(lang, "btn_mode_real"), callback_data="mode:real")
    kb.adjust(1)
    return kb.as_markup()


def cancel_kb(lang: str):
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text=tr(lang, "btn_cancel"))]],
        resize_keyboard=True,
    )


async def _get_wizard_data(chat_id: int, state: FSMContext):
    data = await state.get_data()
    async with SessionLocal() as db:
        us = await crud.ensure_user_settings(db, chat_id)
        lang = data.get("lang") or us.language
        track = data.get("track") or us.track
        mode = data.get("mode") or us.mode
    await state.update_data(lang=lang, track=track, mode=mode)
    return lang, track, mode


async def _start_interview(msg: Message, state: FSMContext, session_id: int, lang: str):
    async with SessionLocal() as db:
        s = await crud.get_session(db, session_id)
        if not s:
            await msg.answer(tr(lang, "session_not_found"))
            return
        s.stage = "interview"
        await crud.add_message(db, session_id, "assistant", "event", tr(lang, "trial_intro"))
        await db.commit()

    await msg.answer(tr(lang, "trial_intro"))
    await msg.answer(tr(lang, "q1"))
    async with SessionLocal() as db:
        await crud.add_message(db, session_id, "assistant", "question", tr(lang, "q1"))
        await db.commit()

    await state.set_state(InterviewFSM.q1)


async def _wait_vacancy_then_start(msg: Message, state: FSMContext, session_id: int, lang: str):
    # мягкий poll: 20-25 сек хватает, чтобы Celery успел
    for _ in range(15):
        await asyncio.sleep(1.5)

        # если пользователь уже начал новую сессию — прекращаем
        data = await state.get_data()
        if data.get("session_id") != session_id:
            return

        async with SessionLocal() as db:
            s = await crud.get_session(db, session_id)
            if not s or s.stage != "collecting":
                return

            if s.vacancy_status == "ok":
                # стартуем интервью
                await _start_interview(msg, state, session_id, lang)
                return

            if s.vacancy_status == "failed":
                await msg.answer(tr(lang, "vacancy_fetch_failed"))
                await state.set_state(InterviewFSM.waiting_vacancy)
                return

    await msg.answer(tr(lang, "vacancy_still_pending"))


@router.message(Command("start"))
async def cmd_start(msg: Message, state: FSMContext):
    await state.clear()
    async with SessionLocal() as db:
        us = await crud.ensure_user_settings(db, msg.chat.id)
        await db.commit()

    # мастер: track -> lang -> mode
    await state.update_data(lang=us.language, track=us.track, mode=us.mode)
    await msg.answer(tr(us.language, "choose_track"), reply_markup=track_kb(us.language))
    await state.set_state(InterviewFSM.choose_track)


@router.callback_query(InterviewFSM.choose_track, F.data.startswith("track:"))
async def choose_track(cb: CallbackQuery, state: FSMContext):
    track = cb.data.split(":", 1)[1]
    async with SessionLocal() as db:
        await crud.update_user_track(db, cb.message.chat.id, track)
        await db.commit()

    lang, _, mode = await _get_wizard_data(cb.message.chat.id, state)
    await state.update_data(track=track)
    await cb.answer()
    await cb.message.answer(tr(lang, "choose_lang"), reply_markup=lang_kb(lang))
    await state.set_state(InterviewFSM.choose_lang)


@router.callback_query(InterviewFSM.choose_lang, F.data.startswith("lang:"))
async def choose_lang(cb: CallbackQuery, state: FSMContext):
    lang = cb.data.split(":", 1)[1]
    async with SessionLocal() as db:
        await crud.update_user_language(db, cb.message.chat.id, lang)
        await db.commit()

    _, track, mode = await _get_wizard_data(cb.message.chat.id, state)
    await state.update_data(lang=lang)
    await cb.answer()
    await cb.message.answer(tr(lang, "choose_mode"), reply_markup=mode_kb(lang))
    await state.set_state(InterviewFSM.choose_mode)


@router.callback_query(InterviewFSM.choose_mode, F.data.startswith("mode:"))
async def choose_mode(cb: CallbackQuery, state: FSMContext):
    mode = cb.data.split(":", 1)[1]
    async with SessionLocal() as db:
        await crud.update_user_mode(db, cb.message.chat.id, mode)
        await db.commit()

    lang, track, _ = await _get_wizard_data(cb.message.chat.id, state)
    await state.update_data(mode=mode)
    await cb.answer()

    # создаём session (снапшот настроек)
    async with SessionLocal() as db:
        s = await crud.create_session(db, cb.message.chat.id, language=lang, track=track, mode=mode)
        await db.commit()

    await state.update_data(session_id=s.id)
    await cb.message.answer(tr(lang, "ask_vacancy"), reply_markup=cancel_kb(lang))
    await state.set_state(InterviewFSM.waiting_vacancy)


@router.message(InterviewFSM.waiting_vacancy, F.text & ~F.text.startswith("/"))
async def intake_vacancy(msg: Message, state: FSMContext):
    lang, track, mode = await _get_wizard_data(msg.chat.id, state)
    data = await state.get_data()
    session_id = data.get("session_id")
    if not session_id:
        await msg.answer(tr(lang, "session_not_found"))
        await state.clear()
        return

    text = (msg.text or "").strip()
    is_url = False
    try:
        p = urlparse(text)
        is_url = bool(p.scheme and p.netloc)
    except Exception:
        is_url = False

    async with SessionLocal() as db:
        if is_url:
            await crud.set_vacancy_pending(db, session_id, vacancy_url=text)
            await db.commit()
            fetch_vacancy.delay(session_id, text)
            await msg.answer(tr(lang, "vacancy_fetching"))
        else:
            await crud.set_vacancy_ok(db, session_id, vacancy_text=text)
            await db.commit()

    await msg.answer(tr(lang, "ask_cv"), reply_markup=cancel_kb(lang))
    await state.set_state(InterviewFSM.waiting_cv)


@router.message(InterviewFSM.waiting_cv, (F.text & ~F.text.startswith("/")) | F.document)
async def intake_cv(msg: Message, state: FSMContext):
    lang, _, _ = await _get_wizard_data(msg.chat.id, state)
    data = await state.get_data()
    session_id = data.get("session_id")
    if not session_id:
        await msg.answer(tr(lang, "session_not_found"))
        await state.clear()
        return

    cv_text = None
    if msg.document:
        if msg.document.mime_type != "application/pdf":
            await msg.answer(tr(lang, "cv_pdf_only"))
            return
        file = await msg.bot.get_file(msg.document.file_id)
        file_bytes = await msg.bot.download_file(file.file_path)
        raw = file_bytes.read()
        cv_text = read_pdf_text(raw)
        if not cv_text:
            async with SessionLocal() as db:
                await crud.set_cv_failed(db, session_id, "pdf_no_text")
                await db.commit()
            await msg.answer(tr(lang, "cv_pdf_no_text"))
            return
    else:
        cv_text = (msg.text or "").strip()

    if not cv_text or len(cv_text) < 20:
        await msg.answer(tr(lang, "cv_too_short"))
        return

    async with SessionLocal() as db:
        await crud.set_cv_ok(db, session_id, cv_text=cv_text)
        await db.commit()

        s = await crud.get_session(db, session_id)

    # решаем что дальше по статусу вакансии
    if s and s.vacancy_status == "ok":
        await _start_interview(msg, state, session_id, lang)
        return

    if s and s.vacancy_status == "pending":
        await msg.answer(tr(lang, "cv_received_wait_vacancy"))
        asyncio.create_task(_wait_vacancy_then_start(msg, state, session_id, lang))
        return

    # failed/empty -> просим вакансию текстом
    await msg.answer(tr(lang, "vacancy_need_text"))
    await state.set_state(InterviewFSM.waiting_vacancy)


@router.message(InterviewFSM.waiting_vacancy, F.text == tr("uk", "btn_cancel"))
@router.message(InterviewFSM.waiting_vacancy, F.text == tr("ru", "btn_cancel"))
@router.message(InterviewFSM.waiting_vacancy, F.text == tr("en", "btn_cancel"))
@router.message(InterviewFSM.waiting_cv, F.text == tr("uk", "btn_cancel"))
@router.message(InterviewFSM.waiting_cv, F.text == tr("ru", "btn_cancel"))
@router.message(InterviewFSM.waiting_cv, F.text == tr("en", "btn_cancel"))
async def cancel(msg: Message, state: FSMContext):
    lang, _, _ = await _get_wizard_data(msg.chat.id, state)
    await state.clear()
    await msg.answer(tr(lang, "cancel_ok"))
