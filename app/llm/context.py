# app/llm/context.py
"""
Построение контекста для LLM из данных сессии.
"""

from dataclasses import dataclass, field
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.db import crud
from app.db.models import Session, Message, SessionDocument, InterviewPhase


@dataclass
class InterviewContext:
    """Контекст интервью для LLM"""
    session_id: int
    chat_id: int

    # Настройки
    language: str
    track: str
    difficulty: str
    interview_type: str

    # Документы
    cv_summary: str | None = None
    cv_full: str | None = None
    vacancy_summary: str | None = None
    vacancy_full: str | None = None

    # Текущая фаза
    current_phase: str | None = None
    phase_order: int = 0
    total_phases: int = 0
    phase_config: dict = field(default_factory=dict)

    # История диалога
    conversation: list[dict] = field(default_factory=list)

    # Метаданные
    total_tokens_used: int = 0
    messages_count: int = 0


class ContextBuilder:
    """Строитель контекста для LLM запросов"""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def build_full_context(
        self,
        session_id: int,
        include_full_documents: bool = False,
        max_conversation_messages: int = 20,
    ) -> InterviewContext:
        """
        Строит полный контекст интервью.

        Args:
            session_id: ID сессии
            include_full_documents: включать полные тексты CV/вакансии
            max_conversation_messages: максимум сообщений в истории

        Returns:
            InterviewContext с данными для LLM
        """
        session = await crud.get_session(self.db, session_id)
        if not session:
            raise ValueError(f"Session {session_id} not found")

        context = InterviewContext(
            session_id=session_id,
            chat_id=session.chat_id,
            language=session.language,
            track=session.track,
            difficulty=session.difficulty,
            interview_type=session.interview_type,
        )

        # Загружаем документы
        await self._load_documents(context, session, include_full_documents)

        # Загружаем текущую фазу
        await self._load_current_phase(context, session_id)

        # Загружаем историю диалога
        await self._load_conversation(context, session_id, max_conversation_messages)

        # Загружаем статистику
        await self._load_stats(context, session_id)

        return context

    async def build_minimal_context(self, session_id: int) -> InterviewContext:
        """Строит минимальный контекст (только настройки)"""
        session = await crud.get_session(self.db, session_id)
        if not session:
            raise ValueError(f"Session {session_id} not found")

        return InterviewContext(
            session_id=session_id,
            chat_id=session.chat_id,
            language=session.language,
            track=session.track,
            difficulty=session.difficulty,
            interview_type=session.interview_type,
            cv_summary=session.cv_summary,
            vacancy_summary=session.vacancy_summary,
        )

    async def _load_documents(
        self,
        context: InterviewContext,
        session: Session,
        include_full: bool,
    ) -> None:
        """Загружает документы сессии"""
        # Сначала пробуем взять из Session (для обратной совместимости)
        context.cv_summary = session.cv_summary
        context.vacancy_summary = session.vacancy_summary

        if include_full:
            context.cv_full = session.cv_text
            context.vacancy_full = session.vacancy_text

        # Затем пробуем из SessionDocument (новая схема)
        docs = await crud.get_session_documents(self.db, context.session_id)
        for doc in docs:
            if doc.doc_type == "cv":
                if not context.cv_summary and doc.processed_text:
                    context.cv_summary = doc.processed_text[:500]
                if include_full:
                    context.cv_full = doc.processed_text
            elif doc.doc_type == "vacancy":
                if not context.vacancy_summary and doc.processed_text:
                    context.vacancy_summary = doc.processed_text[:500]
                if include_full:
                    context.vacancy_full = doc.processed_text

    async def _load_current_phase(self, context: InterviewContext, session_id: int) -> None:
        """Загружает информацию о текущей фазе"""
        phases = await crud.get_session_phases(self.db, session_id)
        context.total_phases = len(phases)

        # Ищем активную фазу
        current = await crud.get_current_phase(self.db, session_id)
        if current:
            context.current_phase = current.phase_type
            context.phase_order = current.phase_order
            context.phase_config = current.phase_config or {}
        elif phases:
            # Если нет активной, берем первую pending
            next_phase = await crud.get_next_phase(self.db, session_id)
            if next_phase:
                context.current_phase = next_phase.phase_type
                context.phase_order = next_phase.phase_order
                context.phase_config = next_phase.phase_config or {}

    async def _load_conversation(
        self,
        context: InterviewContext,
        session_id: int,
        max_messages: int,
    ) -> None:
        """Загружает историю диалога"""
        messages = await crud.get_session_messages(
            self.db, session_id, limit=max_messages
        )

        context.conversation = [
            {
                "role": msg.role,
                "content": msg.text,
                "kind": msg.kind,
                "created_at": msg.created_at.isoformat() if msg.created_at else None,
            }
            for msg in messages
        ]
        context.messages_count = len(messages)

    async def _load_stats(self, context: InterviewContext, session_id: int) -> None:
        """Загружает статистику сессии"""
        stats = await crud.get_session_stats(self.db, session_id)
        if stats:
            context.total_tokens_used = stats.total_tokens_input + stats.total_tokens_output


async def build_interview_context(
    db: AsyncSession,
    session_id: int,
    include_full_documents: bool = False,
) -> InterviewContext:
    """
    Удобная функция для построения контекста.

    Args:
        db: сессия БД
        session_id: ID сессии интервью
        include_full_documents: включать полные тексты

    Returns:
        InterviewContext для использования с LLM
    """
    builder = ContextBuilder(db)
    return await builder.build_full_context(
        session_id,
        include_full_documents=include_full_documents,
    )


def context_to_dict(context: InterviewContext) -> dict[str, Any]:
    """Преобразует контекст в словарь для сериализации"""
    return {
        "session_id": context.session_id,
        "chat_id": context.chat_id,
        "language": context.language,
        "track": context.track,
        "difficulty": context.difficulty,
        "interview_type": context.interview_type,
        "cv_summary": context.cv_summary,
        "vacancy_summary": context.vacancy_summary,
        "current_phase": context.current_phase,
        "phase_order": context.phase_order,
        "total_phases": context.total_phases,
        "conversation_length": len(context.conversation),
        "total_tokens_used": context.total_tokens_used,
    }
