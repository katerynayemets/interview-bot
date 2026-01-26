# app/db/crud.py
import datetime as dt
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import UserSettings, Session, Message, Answer


async def ensure_user_settings(db: AsyncSession, chat_id: int) -> UserSettings:
    res = await db.execute(select(UserSettings).where(UserSettings.chat_id == chat_id))
    s = res.scalar_one_or_none()
    if s:
        return s
    s = UserSettings(chat_id=chat_id)
    db.add(s)
    await db.flush()
    return s


async def update_user_language(db: AsyncSession, chat_id: int, language: str) -> None:
    s = await ensure_user_settings(db, chat_id)
    s.language = language
    s.updated_at = dt.datetime.utcnow()


async def update_user_track(db: AsyncSession, chat_id: int, track: str) -> None:
    s = await ensure_user_settings(db, chat_id)
    s.track = track
    s.updated_at = dt.datetime.utcnow()


async def update_user_mode(db: AsyncSession, chat_id: int, mode: str) -> None:
    s = await ensure_user_settings(db, chat_id)
    s.mode = mode
    s.updated_at = dt.datetime.utcnow()


async def create_session(db: AsyncSession, chat_id: int, language: str, track: str, mode: str) -> Session:
    s = Session(
        chat_id=chat_id,
        language=language,
        track=track,
        mode=mode,
        stage="collecting",
        vacancy_status="empty",
        cv_status="empty",
    )
    db.add(s)
    await db.flush()
    return s


async def get_session(db: AsyncSession, session_id: int) -> Session | None:
    res = await db.execute(select(Session).where(Session.id == session_id))
    return res.scalar_one_or_none()

async def get_latest_session(db: AsyncSession, chat_id: int) -> Session | None:
    res = await db.execute(
        select(Session)
        .where(Session.chat_id == chat_id)
        .order_by(Session.id.desc())
        .limit(1)
    )
    return res.scalar_one_or_none()


async def update_session_language(db: AsyncSession, session_id: int, language: str) -> None:
    s = await get_session(db, session_id)
    if not s:
        return
    s.language = language
    s.updated_at = dt.datetime.utcnow()


async def update_session_mode(db: AsyncSession, session_id: int, mode: str) -> None:
    s = await get_session(db, session_id)
    if not s:
        return
    s.mode = mode
    s.updated_at = dt.datetime.utcnow()


async def set_vacancy_pending(db: AsyncSession, session_id: int, vacancy_url: str) -> None:
    s = await get_session(db, session_id)
    if not s:
        return
    s.vacancy_url = vacancy_url
    s.vacancy_status = "pending"
    s.vacancy_error = None
    # важно: очищаем текст, чтобы не было "resume"/мусора и странных length=6
    s.vacancy_text = None
    s.updated_at = dt.datetime.utcnow()


async def set_vacancy_ok(db: AsyncSession, session_id: int, vacancy_text: str, vacancy_url: str | None = None) -> None:
    s = await get_session(db, session_id)
    if not s:
        return
    if vacancy_url:
        s.vacancy_url = vacancy_url
    s.vacancy_text = vacancy_text
    s.vacancy_status = "ok"
    s.vacancy_error = None
    s.updated_at = dt.datetime.utcnow()


async def set_vacancy_failed(db: AsyncSession, session_id: int, error: str, vacancy_url: str | None = None) -> None:
    s = await get_session(db, session_id)
    if not s:
        return
    if vacancy_url:
        s.vacancy_url = vacancy_url
    s.vacancy_status = "failed"
    s.vacancy_error = error[:512]
    s.updated_at = dt.datetime.utcnow()


async def set_cv_ok(db: AsyncSession, session_id: int, cv_text: str) -> None:
    s = await get_session(db, session_id)
    if not s:
        return
    s.cv_text = cv_text
    s.cv_status = "ok"
    s.cv_error = None
    s.updated_at = dt.datetime.utcnow()


async def set_cv_failed(db: AsyncSession, session_id: int, error: str) -> None:
    s = await get_session(db, session_id)
    if not s:
        return
    s.cv_status = "failed"
    s.cv_error = error[:512]
    s.updated_at = dt.datetime.utcnow()


async def add_message(db: AsyncSession, session_id: int, role: str, kind: str, text: str) -> None:
    db.add(Message(session_id=session_id, role=role, kind=kind, text=text))


async def add_answer(db: AsyncSession, session_id: int, step: str, text: str) -> None:
    db.add(Answer(session_id=session_id, step=step, text=text))
