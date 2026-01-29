# app/routers/start.py
import asyncio
from urllib.parse import urlparse

from aiogram import Router, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import (
    Message, CallbackQuery,
    ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove,
)
from aiogram.utils.keyboard import InlineKeyboardBuilder

from app.db.session import SessionLocal
from app.db import crud
from app.i18n import tr
from app.states import InterviewFSM
from app.worker.pdf_reader import read_pdf_text
from app.worker.docx_reader import read_docx_text
from app.worker.text_processing import process_cv_text, process_vacancy_text, detect_seniority
from app.worker.tasks import fetch_vacancy

router = Router()


# ============== Keyboards ==============

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


def interview_type_kb(lang: str):
    """Клавиатура выбора типа интервью"""
    kb = InlineKeyboardBuilder()
    kb.button(text=tr(lang, "btn_interview_mixed"), callback_data="itype:mixed")
    kb.button(text=tr(lang, "btn_interview_hr_soft"), callback_data="itype:hr_soft")
    kb.button(text=tr(lang, "btn_interview_technical"), callback_data="itype:technical_hard")
    kb.adjust(1)
    return kb.as_markup()


def difficulty_kb(lang: str):
    """Клавиатура выбора уровня сложности"""
    kb = InlineKeyboardBuilder()
    kb.button(text=tr(lang, "btn_difficulty_junior"), callback_data="diff:junior")
    kb.button(text=tr(lang, "btn_difficulty_middle"), callback_data="diff:middle")
    kb.button(text=tr(lang, "btn_difficulty_senior"), callback_data="diff:senior")
    kb.button(text=tr(lang, "btn_difficulty_lead"), callback_data="diff:lead")
    kb.adjust(2)
    return kb.as_markup()


def cancel_skip_kb(lang: str):
    """Клавиатура с кнопками Пропустить и Отмена"""
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=tr(lang, "btn_skip"))],
            [KeyboardButton(text=tr(lang, "btn_cancel"))],
        ],
        resize_keyboard=True,
    )


def cancel_kb(lang: str):
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text=tr(lang, "btn_cancel"))]],
        resize_keyboard=True,
    )


# ============== Helpers ==============

async def _get_wizard_data(chat_id: int, state: FSMContext):
    """Получает настройки из FSM или из БД"""
    data = await state.get_data()
    async with SessionLocal() as db:
        us = await crud.ensure_user_settings(db, chat_id)
        lang = data.get("lang") or us.language
        track = data.get("track") or us.track
        mode = data.get("mode") or us.mode
        interview_type = data.get("interview_type") or us.interview_type
        difficulty = data.get("difficulty") or us.difficulty
    await state.update_data(
        lang=lang, track=track, mode=mode,
        interview_type=interview_type, difficulty=difficulty
    )
    return lang, track, mode, interview_type, difficulty


async def _start_interview(msg: Message, state: FSMContext, session_id: int, lang: str):
    """Начинает интервью после сбора данных — запускает LLM flow"""
    async with SessionLocal() as db:
        s = await crud.get_session(db, session_id)
        if not s:
            await msg.answer(tr(lang, "session_not_found"))
            return
        s.stage = "interview"

        # Создаем фазы интервью
        await crud.create_interview_phases(db, session_id, s.interview_type)

        # Инициализируем статистику сессии
        await crud.ensure_session_stats(db, session_id)
        await db.commit()

    await msg.answer(tr(lang, "interview_starting"), reply_markup=ReplyKeyboardRemove())
    await state.set_state(InterviewFSM.interview_phase)

    # Генерируем первый вопрос через LLM
    from app.routers.interview import _generate_and_send_question
    await _generate_and_send_question(msg, state, session_id, lang)


async def _check_ready_to_start(db, session_id: int) -> bool:
    """Проверяет, готовы ли данные для старта интервью"""
    s = await crud.get_session(db, session_id)
    if not s:
        return False

    # Нужен хотя бы один: CV или vacancy в статусе ok/skipped
    cv_ready = s.cv_status in ("ok", "skipped")
    vacancy_ready = s.vacancy_status in ("ok", "skipped")

    # Хотя бы один должен быть ok (не оба skipped)
    has_data = s.cv_status == "ok" or s.vacancy_status == "ok"

    return cv_ready and vacancy_ready and has_data


async def _wait_vacancy_then_start(msg: Message, state: FSMContext, session_id: int, lang: str):
    """Ждет завершения парсинга вакансии и стартует интервью"""
    for _ in range(15):
        await asyncio.sleep(1.5)

        data = await state.get_data()
        if data.get("session_id") != session_id:
            return

        async with SessionLocal() as db:
            s = await crud.get_session(db, session_id)
            if not s or s.stage != "collecting":
                return

            if s.vacancy_status == "ok":
                if await _check_ready_to_start(db, session_id):
                    await _start_interview(msg, state, session_id, lang)
                return

            if s.vacancy_status == "failed":
                await msg.answer(tr(lang, "vacancy_fetch_failed"))
                await state.set_state(InterviewFSM.waiting_vacancy)
                return

    await msg.answer(tr(lang, "vacancy_still_pending"))


# ============== Wizard Handlers ==============

@router.message(Command("start"))
async def cmd_start(msg: Message, state: FSMContext):
    await state.clear()
    async with SessionLocal() as db:
        us = await crud.ensure_user_settings(db, msg.chat.id)
        await db.commit()

    await state.update_data(
        lang=us.language, track=us.track, mode=us.mode,
        interview_type=us.interview_type, difficulty=us.difficulty
    )
    await msg.answer(tr(us.language, "choose_track"), reply_markup=track_kb(us.language))
    await state.set_state(InterviewFSM.choose_track)


@router.callback_query(InterviewFSM.choose_track, F.data.startswith("track:"))
async def choose_track(cb: CallbackQuery, state: FSMContext):
    track = cb.data.split(":", 1)[1]
    async with SessionLocal() as db:
        await crud.update_user_track(db, cb.message.chat.id, track)
        await db.commit()

    lang, *_ = await _get_wizard_data(cb.message.chat.id, state)
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

    lang, *_ = await _get_wizard_data(cb.message.chat.id, state)
    await state.update_data(mode=mode)
    await cb.answer()

    # Переходим к выбору типа интервью
    await cb.message.answer(tr(lang, "choose_interview_type"), reply_markup=interview_type_kb(lang))
    await state.set_state(InterviewFSM.choose_interview_type)


@router.callback_query(InterviewFSM.choose_interview_type, F.data.startswith("itype:"))
async def choose_interview_type(cb: CallbackQuery, state: FSMContext):
    interview_type = cb.data.split(":", 1)[1]
    async with SessionLocal() as db:
        await crud.update_user_interview_type(db, cb.message.chat.id, interview_type)
        await db.commit()

    lang, *_ = await _get_wizard_data(cb.message.chat.id, state)
    await state.update_data(interview_type=interview_type)
    await cb.answer()

    # Переходим к выбору уровня сложности
    await cb.message.answer(tr(lang, "choose_difficulty"), reply_markup=difficulty_kb(lang))
    await state.set_state(InterviewFSM.choose_difficulty)


@router.callback_query(InterviewFSM.choose_difficulty, F.data.startswith("diff:"))
async def choose_difficulty(cb: CallbackQuery, state: FSMContext):
    difficulty = cb.data.split(":", 1)[1]
    async with SessionLocal() as db:
        await crud.update_user_difficulty(db, cb.message.chat.id, difficulty)
        await db.commit()

    lang, track, mode, interview_type, _ = await _get_wizard_data(cb.message.chat.id, state)
    await state.update_data(difficulty=difficulty)
    await cb.answer()

    # Создаем сессию
    async with SessionLocal() as db:
        s = await crud.create_session(
            db, cb.message.chat.id,
            language=lang, track=track, mode=mode,
            interview_type=interview_type, difficulty=difficulty
        )
        await db.commit()

    await state.update_data(session_id=s.id)
    await cb.message.answer(tr(lang, "ask_vacancy"), reply_markup=cancel_skip_kb(lang))
    await state.set_state(InterviewFSM.waiting_vacancy)


# ============== Data Collection: Vacancy ==============

@router.message(InterviewFSM.waiting_vacancy, F.text & ~F.text.startswith("/"))
async def intake_vacancy(msg: Message, state: FSMContext):
    lang, *_ = await _get_wizard_data(msg.chat.id, state)
    data = await state.get_data()
    session_id = data.get("session_id")
    if not session_id:
        await msg.answer(tr(lang, "session_not_found"))
        await state.clear()
        return

    text = (msg.text or "").strip()

    # Проверяем кнопку "Пропустить"
    if text == tr(lang, "btn_skip") or text == tr("uk", "btn_skip") or text == tr("ru", "btn_skip") or text == tr("en", "btn_skip"):
        async with SessionLocal() as db:
            s = await crud.get_session(db, session_id)
            # Можно пропустить только если CV уже есть
            if s and s.cv_status == "ok":
                await crud.set_vacancy_skipped(db, session_id)
                await db.commit()
                await msg.answer(tr(lang, "vacancy_skipped"))

                if await _check_ready_to_start(db, session_id):
                    await _start_interview(msg, state, session_id, lang)
                    return
            else:
                # CV еще нет - идем собирать CV
                await crud.set_vacancy_skipped(db, session_id)
                await db.commit()
                await msg.answer(tr(lang, "vacancy_skipped"))

        await msg.answer(tr(lang, "ask_cv"), reply_markup=cancel_skip_kb(lang))
        await state.set_state(InterviewFSM.waiting_cv)
        return

    # Проверяем кнопку "Отмена"
    if text == tr(lang, "btn_cancel") or text == tr("uk", "btn_cancel") or text == tr("ru", "btn_cancel") or text == tr("en", "btn_cancel"):
        await state.clear()
        await msg.answer(tr(lang, "cancel_ok"), reply_markup=ReplyKeyboardRemove())
        return

    # Определяем URL или текст
    is_url = False
    try:
        p = urlparse(text)
        is_url = bool(p.scheme and p.netloc)
    except Exception:
        is_url = False

    async with SessionLocal() as db:
        s0 = await crud.get_session(db, session_id)
        cv_already_ok = bool(s0 and s0.cv_status == "ok")

        if is_url:
            await crud.set_vacancy_pending(db, session_id, vacancy_url=text)
            await db.commit()
            fetch_vacancy.delay(session_id, text)
            await msg.answer(tr(lang, "vacancy_fetching"))

            if cv_already_ok:
                asyncio.create_task(_wait_vacancy_then_start(msg, state, session_id, lang))
                return
        else:
            # Обрабатываем текст вакансии
            processed = process_vacancy_text(text)

            await crud.set_vacancy_ok(
                db, session_id,
                vacancy_text=text,
                vacancy_summary=processed.summary
            )

            # Сохраняем в SessionDocument
            await crud.add_session_document(
                db, session_id,
                doc_type="vacancy",
                raw_text=text,
                processed_text=processed.anonymized,
                token_count=processed.token_count
            )
            await db.commit()

            s = await crud.get_session(db, session_id)
            if s and s.cv_status == "ok":
                await _start_interview(msg, state, session_id, lang)
                return

    await msg.answer(tr(lang, "ask_cv"), reply_markup=cancel_skip_kb(lang))
    await state.set_state(InterviewFSM.waiting_cv)


# ============== Data Collection: CV ==============

@router.message(InterviewFSM.waiting_cv, (F.text & ~F.text.startswith("/")) | F.document)
async def intake_cv(msg: Message, state: FSMContext):
    lang, *_ = await _get_wizard_data(msg.chat.id, state)
    data = await state.get_data()
    session_id = data.get("session_id")
    if not session_id:
        await msg.answer(tr(lang, "session_not_found"))
        await state.clear()
        return

    text = (msg.text or "").strip()

    # Проверяем кнопку "Пропустить"
    if text == tr(lang, "btn_skip") or text == tr("uk", "btn_skip") or text == tr("ru", "btn_skip") or text == tr("en", "btn_skip"):
        async with SessionLocal() as db:
            s = await crud.get_session(db, session_id)
            if s and s.vacancy_status == "ok":
                # Вакансия готова — пропускаем CV и стартуем
                await crud.set_cv_skipped(db, session_id)
                await db.commit()
                await msg.answer(tr(lang, "cv_skipped"))

                if await _check_ready_to_start(db, session_id):
                    await _start_interview(msg, state, session_id, lang)
                    return
            elif s and s.vacancy_status == "pending":
                # Вакансия ещё парсится — пропускаем CV и ждём вакансию
                await crud.set_cv_skipped(db, session_id)
                await db.commit()
                await msg.answer(tr(lang, "cv_skipped"))
                await msg.answer(tr(lang, "cv_received_wait_vacancy"))
                asyncio.create_task(_wait_vacancy_then_start(msg, state, session_id, lang))
                return
            else:
                # Нет ни CV ни vacancy - нельзя пропустить
                await msg.answer(tr(lang, "need_cv_or_vacancy"))
                return
        return

    # Проверяем кнопку "Отмена"
    if text == tr(lang, "btn_cancel") or text == tr("uk", "btn_cancel") or text == tr("ru", "btn_cancel") or text == tr("en", "btn_cancel"):
        await state.clear()
        await msg.answer(tr(lang, "cancel_ok"), reply_markup=ReplyKeyboardRemove())
        return

    cv_text = None

    if msg.document:
        filename = (msg.document.file_name or "").lower()
        mime = (msg.document.mime_type or "").lower()

        is_pdf = mime == "application/pdf" or filename.endswith(".pdf")
        is_docx = (
            mime in {
                "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                "application/msword",
            }
            or filename.endswith(".docx")
        )

        if not (is_pdf or is_docx):
            await msg.answer(tr(lang, "cv_pdf_only"))
            return

        file = await msg.bot.get_file(msg.document.file_id)
        file_bytes = await msg.bot.download_file(file.file_path)
        raw = file_bytes.read()

        if is_pdf:
            cv_text = read_pdf_text(raw)
        else:
            cv_text = read_docx_text(raw)

        if not cv_text:
            async with SessionLocal() as db:
                await crud.set_cv_failed(db, session_id, "no_text")
                await db.commit()
            await msg.answer(tr(lang, "cv_pdf_no_text"))
            return
    else:
        cv_text = text

    if not cv_text or len(cv_text) < 20:
        await msg.answer(tr(lang, "cv_too_short"))
        return

    # Обрабатываем CV: анонимизация, токены, summary
    processed = process_cv_text(cv_text)

    # Определяем уровень из CV
    detected_difficulty = detect_seniority(cv_text)

    async with SessionLocal() as db:
        await crud.set_cv_ok(
            db, session_id,
            cv_text=processed.anonymized,  # сохраняем анонимизированный
            cv_summary=processed.summary
        )

        # Обновляем difficulty если определили из CV
        s = await crud.get_session(db, session_id)
        if s and detected_difficulty != "middle":
            await crud.update_session_difficulty(db, session_id, detected_difficulty)

        # Сохраняем в SessionDocument
        await crud.add_session_document(
            db, session_id,
            doc_type="cv",
            raw_text=cv_text,  # оригинал (не сохраняем долго, можно убрать)
            processed_text=processed.anonymized,
            token_count=processed.token_count
        )
        await db.commit()

        s = await crud.get_session(db, session_id)

    await msg.answer(tr(lang, "cv_anonymized"))

    if s and s.vacancy_status == "ok":
        await _start_interview(msg, state, session_id, lang)
        return

    if s and s.vacancy_status == "pending":
        await msg.answer(tr(lang, "cv_received_wait_vacancy"))
        await state.set_state(InterviewFSM.waiting_vacancy)
        asyncio.create_task(_wait_vacancy_then_start(msg, state, session_id, lang))
        return

    if s and s.vacancy_status == "skipped":
        # Vacancy пропущена, CV есть - можно стартовать
        if await _check_ready_to_start(db, session_id):
            await _start_interview(msg, state, session_id, lang)
            return

    await msg.answer(tr(lang, "vacancy_need_text"))
    await state.set_state(InterviewFSM.waiting_vacancy)


# ============== Cancel Handlers ==============

@router.message(Command("cancel"))
async def cmd_cancel(msg: Message, state: FSMContext):
    lang, *_ = await _get_wizard_data(msg.chat.id, state)
    await state.clear()
    await msg.answer(tr(lang, "cancel_ok"), reply_markup=ReplyKeyboardRemove())
