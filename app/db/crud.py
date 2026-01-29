# app/db/crud.py
import datetime as dt
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db.models import (
    UserSettings, Session, Message, Answer,
    SessionDocument, InterviewPhase, SessionStats, InterviewFeedback
)


# ============== UserSettings ==============

async def ensure_user_settings(db: AsyncSession, chat_id: int) -> UserSettings:
    res = await db.execute(select(UserSettings).where(UserSettings.chat_id == chat_id))
    s = res.scalar_one_or_none()
    if s:
        return s
    s = UserSettings(chat_id=chat_id)
    db.add(s)
    await db.flush()
    return s


async def get_user_settings(db: AsyncSession, chat_id: int) -> UserSettings | None:
    res = await db.execute(select(UserSettings).where(UserSettings.chat_id == chat_id))
    return res.scalar_one_or_none()


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


async def update_user_interview_type(db: AsyncSession, chat_id: int, interview_type: str) -> None:
    """Обновляет тип интервью: hr_soft | technical_hard | mixed"""
    s = await ensure_user_settings(db, chat_id)
    s.interview_type = interview_type
    s.updated_at = dt.datetime.utcnow()


async def update_user_difficulty(db: AsyncSession, chat_id: int, difficulty: str) -> None:
    """Обновляет уровень сложности: junior | middle | senior | lead"""
    s = await ensure_user_settings(db, chat_id)
    s.difficulty = difficulty
    s.updated_at = dt.datetime.utcnow()


# ============== Session ==============

async def create_session(
    db: AsyncSession,
    chat_id: int,
    language: str,
    track: str,
    mode: str,
    interview_type: str = "mixed",
    difficulty: str = "middle",
) -> Session:
    """Создает новую сессию интервью со снапшотом настроек"""
    s = Session(
        chat_id=chat_id,
        language=language,
        track=track,
        mode=mode,
        interview_type=interview_type,
        difficulty=difficulty,
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


async def get_session_with_documents(db: AsyncSession, session_id: int) -> Session | None:
    """Получает сессию с загруженными документами"""
    res = await db.execute(
        select(Session)
        .where(Session.id == session_id)
        .options(selectinload(Session.documents))
    )
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


async def update_session_interview_type(db: AsyncSession, session_id: int, interview_type: str) -> None:
    s = await get_session(db, session_id)
    if not s:
        return
    s.interview_type = interview_type
    s.updated_at = dt.datetime.utcnow()


async def update_session_difficulty(db: AsyncSession, session_id: int, difficulty: str) -> None:
    s = await get_session(db, session_id)
    if not s:
        return
    s.difficulty = difficulty
    s.updated_at = dt.datetime.utcnow()


async def update_session_stage(db: AsyncSession, session_id: int, stage: str) -> None:
    s = await get_session(db, session_id)
    if not s:
        return
    s.stage = stage
    s.updated_at = dt.datetime.utcnow()


# ============== Vacancy Status ==============

async def set_vacancy_pending(db: AsyncSession, session_id: int, vacancy_url: str) -> None:
    s = await get_session(db, session_id)
    if not s:
        return
    s.vacancy_url = vacancy_url
    s.vacancy_status = "pending"
    s.vacancy_error = None
    s.vacancy_text = None
    s.vacancy_summary = None
    s.updated_at = dt.datetime.utcnow()


async def set_vacancy_ok(
    db: AsyncSession,
    session_id: int,
    vacancy_text: str,
    vacancy_summary: str | None = None,
    vacancy_url: str | None = None,
) -> None:
    s = await get_session(db, session_id)
    if not s:
        return
    if vacancy_url:
        s.vacancy_url = vacancy_url
    s.vacancy_text = vacancy_text  # legacy, для обратной совместимости
    s.vacancy_summary = vacancy_summary[:512] if vacancy_summary else vacancy_text[:512]
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


async def set_vacancy_skipped(db: AsyncSession, session_id: int) -> None:
    """Пользователь явно пропустил вакансию"""
    s = await get_session(db, session_id)
    if not s:
        return
    s.vacancy_status = "skipped"
    s.vacancy_error = None
    s.updated_at = dt.datetime.utcnow()


# ============== CV Status ==============

async def set_cv_ok(
    db: AsyncSession,
    session_id: int,
    cv_text: str,
    cv_summary: str | None = None,
) -> None:
    s = await get_session(db, session_id)
    if not s:
        return
    s.cv_text = cv_text  # legacy
    s.cv_summary = cv_summary[:512] if cv_summary else cv_text[:512]
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


async def set_cv_skipped(db: AsyncSession, session_id: int) -> None:
    """Пользователь явно пропустил резюме"""
    s = await get_session(db, session_id)
    if not s:
        return
    s.cv_status = "skipped"
    s.cv_error = None
    s.updated_at = dt.datetime.utcnow()


# ============== SessionDocument ==============

async def add_session_document(
    db: AsyncSession,
    session_id: int,
    doc_type: str,
    raw_text: str,
    processed_text: str | None = None,
    source_url: str | None = None,
    token_count: int = 0,
) -> SessionDocument:
    """Добавляет документ (CV или вакансию) к сессии"""
    doc = SessionDocument(
        session_id=session_id,
        doc_type=doc_type,
        source_url=source_url,
        raw_text=raw_text,
        processed_text=processed_text or raw_text,
        token_count=token_count,
    )
    db.add(doc)
    await db.flush()
    return doc


async def get_session_document(db: AsyncSession, session_id: int, doc_type: str) -> SessionDocument | None:
    """Получает документ определенного типа для сессии"""
    res = await db.execute(
        select(SessionDocument)
        .where(SessionDocument.session_id == session_id)
        .where(SessionDocument.doc_type == doc_type)
        .order_by(SessionDocument.id.desc())
        .limit(1)
    )
    return res.scalar_one_or_none()


async def get_session_documents(db: AsyncSession, session_id: int) -> list[SessionDocument]:
    """Получает все документы сессии"""
    res = await db.execute(
        select(SessionDocument)
        .where(SessionDocument.session_id == session_id)
        .order_by(SessionDocument.id)
    )
    return list(res.scalars().all())


# ============== InterviewPhase ==============

async def create_interview_phases(
    db: AsyncSession,
    session_id: int,
    interview_type: str,
) -> list[InterviewPhase]:
    """
    Создает фазы интервью в зависимости от типа.

    hr_soft: intro → behavioral → questions_to_company → closing
    technical_hard: intro → warmup → technical_deep → closing
    mixed: intro → warmup → technical_deep → behavioral → questions_to_company → closing
    """
    phase_configs = {
        "hr_soft": [
            ("intro", {"duration_min": 2}),
            ("behavioral", {"questions_count": 5}),
            ("questions_to_company", {"duration_min": 5}),
            ("closing", {"duration_min": 2}),
        ],
        "technical_hard": [
            ("intro", {"duration_min": 2}),
            ("warmup", {"questions_count": 2}),
            ("technical_deep", {"questions_count": 5}),
            ("closing", {"duration_min": 2}),
        ],
        "mixed": [
            ("intro", {"duration_min": 2}),
            ("warmup", {"questions_count": 2}),
            ("technical_deep", {"questions_count": 3}),
            ("behavioral", {"questions_count": 3}),
            ("questions_to_company", {"duration_min": 3}),
            ("closing", {"duration_min": 2}),
        ],
    }

    phases_config = phase_configs.get(interview_type, phase_configs["mixed"])
    phases = []

    for order, (phase_type, config) in enumerate(phases_config, start=1):
        phase = InterviewPhase(
            session_id=session_id,
            phase_type=phase_type,
            phase_order=order,
            status="pending",
            phase_config=config,
        )
        db.add(phase)
        phases.append(phase)

    await db.flush()
    return phases


async def get_current_phase(db: AsyncSession, session_id: int) -> InterviewPhase | None:
    """Получает текущую активную фазу интервью"""
    res = await db.execute(
        select(InterviewPhase)
        .where(InterviewPhase.session_id == session_id)
        .where(InterviewPhase.status == "active")
        .limit(1)
    )
    return res.scalar_one_or_none()


async def get_next_phase(db: AsyncSession, session_id: int) -> InterviewPhase | None:
    """Получает следующую pending фазу"""
    res = await db.execute(
        select(InterviewPhase)
        .where(InterviewPhase.session_id == session_id)
        .where(InterviewPhase.status == "pending")
        .order_by(InterviewPhase.phase_order)
        .limit(1)
    )
    return res.scalar_one_or_none()


async def start_phase(db: AsyncSession, phase_id: int) -> None:
    """Начинает фазу интервью"""
    res = await db.execute(select(InterviewPhase).where(InterviewPhase.id == phase_id))
    phase = res.scalar_one_or_none()
    if phase:
        phase.status = "active"
        phase.started_at = dt.datetime.utcnow()


async def complete_phase(db: AsyncSession, phase_id: int) -> None:
    """Завершает фазу интервью"""
    res = await db.execute(select(InterviewPhase).where(InterviewPhase.id == phase_id))
    phase = res.scalar_one_or_none()
    if phase:
        phase.status = "completed"
        phase.completed_at = dt.datetime.utcnow()


async def get_session_phases(db: AsyncSession, session_id: int) -> list[InterviewPhase]:
    """Получает все фазы сессии"""
    res = await db.execute(
        select(InterviewPhase)
        .where(InterviewPhase.session_id == session_id)
        .order_by(InterviewPhase.phase_order)
    )
    return list(res.scalars().all())


# ============== Message ==============

async def add_message(
    db: AsyncSession,
    session_id: int,
    role: str,
    kind: str,
    text: str,
    phase_id: int | None = None,
    model_used: str | None = None,
    tokens_input: int = 0,
    tokens_output: int = 0,
    latency_ms: int = 0,
) -> Message:
    """Добавляет сообщение с опциональным LLM трекингом"""
    msg = Message(
        session_id=session_id,
        phase_id=phase_id,
        role=role,
        kind=kind,
        text=text,
        model_used=model_used,
        tokens_input=tokens_input,
        tokens_output=tokens_output,
        latency_ms=latency_ms,
    )
    db.add(msg)
    await db.flush()
    return msg


async def get_session_messages(
    db: AsyncSession,
    session_id: int,
    limit: int = 50,
    phase_id: int | None = None,
) -> list[Message]:
    """Получает сообщения сессии с опциональной фильтрацией по фазе"""
    query = select(Message).where(Message.session_id == session_id)
    if phase_id:
        query = query.where(Message.phase_id == phase_id)
    query = query.order_by(Message.id.desc()).limit(limit)
    res = await db.execute(query)
    return list(reversed(res.scalars().all()))


async def get_messages_for_llm_context(
    db: AsyncSession,
    session_id: int,
    max_tokens: int = 4000,
) -> list[Message]:
    """
    Получает сообщения для контекста LLM с учетом лимита токенов.
    Возвращает последние сообщения, которые влезают в лимит.
    """
    res = await db.execute(
        select(Message)
        .where(Message.session_id == session_id)
        .order_by(Message.id.desc())
        .limit(100)  # Берем последние 100 для анализа
    )
    messages = list(res.scalars().all())

    # Считаем токены с конца и отбираем сколько влезет
    result = []
    total_tokens = 0

    for msg in messages:
        # Примерная оценка: 4 символа = 1 токен
        msg_tokens = len(msg.text) // 4 + 1
        if total_tokens + msg_tokens > max_tokens:
            break
        result.append(msg)
        total_tokens += msg_tokens

    return list(reversed(result))


# ============== SessionStats ==============

async def ensure_session_stats(db: AsyncSession, session_id: int) -> SessionStats:
    """Создает или возвращает статистику сессии"""
    res = await db.execute(select(SessionStats).where(SessionStats.session_id == session_id))
    stats = res.scalar_one_or_none()
    if stats:
        return stats
    stats = SessionStats(session_id=session_id)
    db.add(stats)
    await db.flush()
    return stats


async def update_session_stats(
    db: AsyncSession,
    session_id: int,
    tokens_input: int = 0,
    tokens_output: int = 0,
    cost_usd: float = 0.0,
) -> None:
    """Инкрементально обновляет статистику сессии"""
    stats = await ensure_session_stats(db, session_id)
    stats.total_tokens_input += tokens_input
    stats.total_tokens_output += tokens_output
    stats.total_messages += 1
    stats.estimated_cost_usd += cost_usd
    stats.updated_at = dt.datetime.utcnow()


async def get_session_stats(db: AsyncSession, session_id: int) -> SessionStats | None:
    res = await db.execute(select(SessionStats).where(SessionStats.session_id == session_id))
    return res.scalar_one_or_none()


async def calculate_session_duration(db: AsyncSession, session_id: int) -> int:
    """Вычисляет длительность интервью в секундах"""
    res = await db.execute(
        select(
            func.min(Message.created_at).label("first_msg"),
            func.max(Message.created_at).label("last_msg")
        )
        .where(Message.session_id == session_id)
    )
    row = res.one_or_none()
    if row and row.first_msg and row.last_msg:
        delta = row.last_msg - row.first_msg
        return int(delta.total_seconds())
    return 0


# ============== InterviewFeedback ==============

async def create_interview_feedback(
    db: AsyncSession,
    session_id: int,
    technical_score: int | None = None,
    communication_score: int | None = None,
    problem_solving_score: int | None = None,
    overall_score: int | None = None,
    strengths: list | None = None,
    improvements: list | None = None,
    detailed_feedback: str | None = None,
    recommended_topics: list | None = None,
) -> InterviewFeedback:
    """Создает feedback после завершения интервью"""
    feedback = InterviewFeedback(
        session_id=session_id,
        technical_score=technical_score,
        communication_score=communication_score,
        problem_solving_score=problem_solving_score,
        overall_score=overall_score,
        strengths=strengths,
        improvements=improvements,
        detailed_feedback=detailed_feedback,
        recommended_topics=recommended_topics,
    )
    db.add(feedback)
    await db.flush()
    return feedback


async def get_interview_feedback(db: AsyncSession, session_id: int) -> InterviewFeedback | None:
    res = await db.execute(select(InterviewFeedback).where(InterviewFeedback.session_id == session_id))
    return res.scalar_one_or_none()


async def add_user_feedback(
    db: AsyncSession,
    session_id: int,
    rating: int,
    comment: str | None = None,
) -> None:
    """Добавляет оценку пользователя к feedback"""
    feedback = await get_interview_feedback(db, session_id)
    if not feedback:
        feedback = InterviewFeedback(session_id=session_id)
        db.add(feedback)
        await db.flush()

    feedback.user_rating = rating
    feedback.user_comment = comment


# ============== Legacy ==============

async def add_answer(db: AsyncSession, session_id: int, step: str, text: str) -> None:
    """Legacy: добавление ответа"""
    db.add(Answer(session_id=session_id, step=step, text=text))
