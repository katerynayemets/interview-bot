"""Build LLM context from session data."""

from dataclasses import dataclass, field
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.db import crud
from app.db.models import Session, Message, SessionDocument, InterviewPhase


@dataclass
class InterviewContext:
    session_id: int
    chat_id: int

    language: str
    track: str
    difficulty: str
    interview_type: str

    cv_summary: str | None = None
    cv_full: str | None = None
    vacancy_summary: str | None = None
    vacancy_full: str | None = None

    current_phase: str | None = None
    phase_order: int = 0
    total_phases: int = 0
    phase_config: dict = field(default_factory=dict)

    conversation: list[dict] = field(default_factory=list)

    total_tokens_used: int = 0
    messages_count: int = 0


class ContextBuilder:
    """Assembles interview context from the database for LLM requests."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def build_full_context(
        self,
        session_id: int,
        include_full_documents: bool = False,
        max_conversation_messages: int = 20,
    ) -> InterviewContext:
        """
        Build the complete interview context for an LLM call.

        Args:
            session_id: target session
            include_full_documents: include full CV/vacancy text (not just summaries)
            max_conversation_messages: cap on history entries

        Returns:
            Populated InterviewContext
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

        await self._load_documents(context, session, include_full_documents)
        await self._load_current_phase(context, session_id)
        await self._load_conversation(context, session_id, max_conversation_messages)
        await self._load_stats(context, session_id)

        return context

    async def build_minimal_context(self, session_id: int) -> InterviewContext:
        """Build minimal context with session settings only."""
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
        # Prefer Session-level summaries for backwards compatibility
        context.cv_summary = session.cv_summary
        context.vacancy_summary = session.vacancy_summary

        if include_full:
            context.cv_full = session.cv_text
            context.vacancy_full = session.vacancy_text

        # Override with SessionDocument data if present (newer schema)
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
        phases = await crud.get_session_phases(self.db, session_id)
        context.total_phases = len(phases)

        current = await crud.get_current_phase(self.db, session_id)
        if current:
            context.current_phase = current.phase_type
            context.phase_order = current.phase_order
            context.phase_config = current.phase_config or {}
        elif phases:
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
        stats = await crud.get_session_stats(self.db, session_id)
        if stats:
            context.total_tokens_used = stats.total_tokens_input + stats.total_tokens_output


async def build_interview_context(
    db: AsyncSession,
    session_id: int,
    include_full_documents: bool = False,
) -> InterviewContext:
    """
    Convenience wrapper around ContextBuilder.build_full_context.

    Args:
        db: async database session
        session_id: target interview session
        include_full_documents: include full CV/vacancy text

    Returns:
        InterviewContext ready for use with PromptManager
    """
    builder = ContextBuilder(db)
    return await builder.build_full_context(
        session_id,
        include_full_documents=include_full_documents,
    )


def context_to_dict(context: InterviewContext) -> dict[str, Any]:
    """Serialize an InterviewContext to a plain dict."""
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
