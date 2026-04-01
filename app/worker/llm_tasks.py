import json
import asyncio
from typing import Any

from app.worker.celery_app import celery
from app.worker.telegram_api import send_message
from app.db.session import SessionLocal
from app.db import crud
from app.config import settings
from app.llm.client import get_llm_client, ChatMessage, LLMResponse, estimate_cost
from app.llm.prompts import PromptManager
from app.llm.context import build_interview_context
from app.logging_config import get_logger

logger = get_logger(__name__)

_loop = None


def get_loop():
    global _loop
    if _loop is None or _loop.is_closed():
        _loop = asyncio.new_event_loop()
        asyncio.set_event_loop(_loop)
    return _loop


def run_async(coro):
    return get_loop().run_until_complete(coro)


@celery.task(name="generate_question", bind=True, max_retries=2)
def generate_question(
    self,
    session_id: int,
    chat_id: int,
    phase_type: str | None = None,
) -> dict:
    try:
        return run_async(_generate_question_async(session_id, chat_id, phase_type))
    except Exception as e:
        logger.exception(f"Error generating question: {e}", session_id=session_id)
        send_message(chat_id, "Произошла ошибка. Попробуй /start заново.")
        raise self.retry(exc=e, countdown=5)


async def _generate_question_async(
    session_id: int,
    chat_id: int,
    phase_type: str | None,
) -> dict:
    async with SessionLocal() as db:
        context = await build_interview_context(db, session_id, include_full_documents=True)
        session = await crud.get_session(db, session_id)

        if not session:
            raise ValueError(f"Session {session_id} not found")

        if not phase_type:
            current_phase = await crud.get_current_phase(db, session_id)
            if current_phase:
                phase_type = current_phase.phase_type
            else:
                next_phase = await crud.get_next_phase(db, session_id)
                if next_phase:
                    await crud.start_phase(db, next_phase.id)
                    phase_type = next_phase.phase_type
                else:
                    phase_type = "technical_deep"

        prompt_manager = PromptManager(
            interview_type=session.interview_type,
            track=session.track,
            difficulty=session.difficulty,
            language=session.language,
            cv_summary=context.cv_summary,
            vacancy_summary=context.vacancy_summary,
        )

        system_prompt = prompt_manager.get_system_prompt()
        question_prompt = prompt_manager.build_question_prompt(
            phase_type=phase_type,
            conversation_history=[
                {"role": m["role"], "content": m["content"]}
                for m in context.conversation[-10:]
            ],
        )

        if session.mode == "real":
            model = settings.LLM_MODEL_REAL
            max_tokens = settings.LLM_MAX_TOKENS_REAL
        else:
            model = settings.LLM_MODEL_TRAINING
            max_tokens = settings.LLM_MAX_TOKENS_TRAINING

        llm = get_llm_client(
            provider=settings.LLM_PROVIDER,
            model=model,
            api_key=settings.OPENAI_API_KEY if settings.LLM_PROVIDER == "openai" else settings.ANTHROPIC_API_KEY,
        )

        messages = [
            ChatMessage(role="system", content=system_prompt),
            ChatMessage(role="user", content=question_prompt),
        ]

        response: LLMResponse = await llm.chat(
            messages=messages,
            temperature=settings.LLM_TEMPERATURE,
            max_tokens=max_tokens,
        )

        question_text = response.content.strip()

        current_phase = await crud.get_current_phase(db, session_id)
        phase_id = current_phase.id if current_phase else None

        await crud.add_message(
            db, session_id,
            role="assistant",
            kind="question",
            text=question_text,
            phase_id=phase_id,
            model_used=response.model,
            tokens_input=response.tokens_input,
            tokens_output=response.tokens_output,
            latency_ms=response.latency_ms,
        )

        cost = estimate_cost(
            settings.LLM_PROVIDER,
            model,
            response.tokens_input,
            response.tokens_output,
        )
        await crud.update_session_stats(
            db, session_id,
            tokens_input=response.tokens_input,
            tokens_output=response.tokens_output,
            cost_usd=cost,
        )

        await db.commit()

        logger.info(
            f"Generated question for session {session_id}",
            session_id=session_id,
            chat_id=chat_id,
            action="llm_question",
            extra={"tokens": response.total_tokens, "cost": cost}
        )

    send_message(chat_id, question_text)

    return {
        "session_id": session_id,
        "question": question_text,
        "tokens_used": response.total_tokens,
        "cost_usd": cost,
        "phase_type": phase_type,
    }


@celery.task(name="evaluate_answer", bind=True, max_retries=2)
def evaluate_answer(
    self,
    session_id: int,
    answer_text: str,
    question_text: str,
) -> dict:
    try:
        return run_async(_evaluate_answer_async(session_id, answer_text, question_text))
    except Exception as e:
        logger.exception(f"Error evaluating answer: {e}", session_id=session_id)
        return {"error": str(e)}


async def _evaluate_answer_async(
    session_id: int,
    answer_text: str,
    question_text: str,
) -> dict:
    async with SessionLocal() as db:
        context = await build_interview_context(db, session_id)
        session = await crud.get_session(db, session_id)

        if not session:
            return {"error": "Session not found"}

        prompt_manager = PromptManager(
            interview_type=session.interview_type,
            track=session.track,
            difficulty=session.difficulty,
            language=session.language,
            cv_summary=context.cv_summary,
            vacancy_summary=context.vacancy_summary,
        )

        evaluation_prompt = prompt_manager.build_evaluation_prompt(
            question=question_text,
            answer=answer_text,
        )

        # Always use the cheaper model for per-answer evaluation
        llm = get_llm_client(
            provider=settings.LLM_PROVIDER,
            model=settings.LLM_MODEL_TRAINING,
            api_key=settings.OPENAI_API_KEY if settings.LLM_PROVIDER == "openai" else settings.ANTHROPIC_API_KEY,
        )

        response = await llm.chat(
            messages=[ChatMessage(role="user", content=evaluation_prompt)],
            temperature=0.3,
            max_tokens=512,
        )

        try:
            content = response.content
            start = content.find("{")
            end = content.rfind("}") + 1
            if start >= 0 and end > start:
                evaluation = json.loads(content[start:end])
            else:
                evaluation = {"error": "No JSON in response", "raw": content}
        except json.JSONDecodeError:
            evaluation = {"error": "Invalid JSON", "raw": response.content}

        cost = estimate_cost(
            settings.LLM_PROVIDER,
            settings.LLM_MODEL_TRAINING,
            response.tokens_input,
            response.tokens_output,
        )
        await crud.update_session_stats(
            db, session_id,
            tokens_input=response.tokens_input,
            tokens_output=response.tokens_output,
            cost_usd=cost,
        )
        await db.commit()

        logger.info(
            f"Evaluated answer for session {session_id}",
            session_id=session_id,
            action="llm_evaluate",
        )

    return evaluation


@celery.task(name="generate_feedback", bind=True, max_retries=2)
def generate_feedback(
    self,
    session_id: int,
    chat_id: int,
    lang: str = "uk",
) -> dict:
    try:
        return run_async(_generate_feedback_async(session_id, chat_id, lang))
    except Exception as e:
        logger.exception(f"Error generating feedback: {e}", session_id=session_id)
        send_message(chat_id, "Не удалось сгенерировать отчёт. Попробуй позже.")
        raise self.retry(exc=e, countdown=10)


async def _generate_feedback_async(
    session_id: int,
    chat_id: int,
    lang: str,
) -> dict:
    async with SessionLocal() as db:
        context = await build_interview_context(db, session_id, include_full_documents=True)
        session = await crud.get_session(db, session_id)

        if not session:
            return {"error": "Session not found"}

        prompt_manager = PromptManager(
            interview_type=session.interview_type,
            track=session.track,
            difficulty=session.difficulty,
            language=session.language,
            cv_summary=context.cv_summary,
            vacancy_summary=context.vacancy_summary,
        )

        question_scores: list = []

        feedback_prompt = prompt_manager.build_feedback_prompt(
            full_conversation=context.conversation,
            question_scores=question_scores,
        )

        model = settings.LLM_MODEL_REAL if session.mode == "real" else settings.LLM_MODEL_TRAINING

        llm = get_llm_client(
            provider=settings.LLM_PROVIDER,
            model=model,
            api_key=settings.OPENAI_API_KEY if settings.LLM_PROVIDER == "openai" else settings.ANTHROPIC_API_KEY,
        )

        response = await llm.chat(
            messages=[ChatMessage(role="user", content=feedback_prompt)],
            temperature=0.5,
            max_tokens=2048,
        )

        try:
            content = response.content
            start = content.find("{")
            end = content.rfind("}") + 1
            if start >= 0 and end > start:
                feedback_data = json.loads(content[start:end])
            else:
                feedback_data = {}
        except json.JSONDecodeError:
            feedback_data = {}

        await crud.create_interview_feedback(
            db, session_id,
            technical_score=feedback_data.get("technical_score"),
            communication_score=feedback_data.get("communication_score"),
            problem_solving_score=feedback_data.get("problem_solving_score"),
            overall_score=feedback_data.get("overall_score"),
            strengths=feedback_data.get("strengths"),
            improvements=feedback_data.get("improvements"),
            detailed_feedback=feedback_data.get("detailed_feedback"),
            recommended_topics=feedback_data.get("recommended_topics"),
        )

        cost = estimate_cost(
            settings.LLM_PROVIDER, model,
            response.tokens_input, response.tokens_output
        )
        await crud.update_session_stats(
            db, session_id,
            tokens_input=response.tokens_input,
            tokens_output=response.tokens_output,
            cost_usd=cost,
        )

        await crud.update_session_stage(db, session_id, "done")

        user = await crud.get_user_settings(db, session.chat_id)
        if user:
            user.total_interviews += 1
            stats = await crud.get_session_stats(db, session_id)
            if stats:
                user.total_tokens_used += stats.total_tokens_input + stats.total_tokens_output
                user.total_spent_usd += stats.estimated_cost_usd

        await db.commit()

        logger.info(
            f"Generated feedback for session {session_id}",
            session_id=session_id,
            chat_id=chat_id,
            action="llm_feedback",
        )

    feedback_text = _format_feedback_message(feedback_data, lang)
    send_message(chat_id, feedback_text)

    return feedback_data


def _format_feedback_message(feedback: dict, lang: str) -> str:
    if not feedback:
        return "Не удалось сгенерировать детальный отчёт."

    lines = []

    lines.append("🎯 **Результаты интервью**\n")

    if feedback.get("overall_score"):
        lines.append(f"📊 Общая оценка: **{feedback['overall_score']}/10**\n")

    scores = []
    if feedback.get("technical_score"):
        scores.append(f"Техника: {feedback['technical_score']}/10")
    if feedback.get("communication_score"):
        scores.append(f"Коммуникация: {feedback['communication_score']}/10")
    if feedback.get("problem_solving_score"):
        scores.append(f"Решение проблем: {feedback['problem_solving_score']}/10")

    if scores:
        lines.append(" | ".join(scores) + "\n")

    if feedback.get("strengths"):
        lines.append("\n✅ **Сильные стороны:**")
        for s in feedback["strengths"][:5]:
            lines.append(f"• {s}")

    if feedback.get("improvements"):
        lines.append("\n📈 **Что улучшить:**")
        for i in feedback["improvements"][:5]:
            lines.append(f"• {i}")

    if feedback.get("recommended_topics"):
        lines.append("\n📚 **Рекомендуем изучить:**")
        for t in feedback["recommended_topics"][:5]:
            lines.append(f"• {t}")

    if feedback.get("detailed_feedback"):
        lines.append(f"\n💬 **Детальный разбор:**\n{feedback['detailed_feedback'][:1500]}")

    return "\n".join(lines)


@celery.task(name="generate_simple_question")
def generate_simple_question(
    session_id: int,
    chat_id: int,
    question_number: int,
) -> dict:
    try:
        return run_async(_generate_simple_question_async(session_id, chat_id, question_number))
    except Exception as e:
        logger.exception(f"Error in simple question: {e}")
        send_message(chat_id, "Ошибка генерации вопроса. Попробуй /start")
        return {"error": str(e)}


async def _generate_simple_question_async(
    session_id: int,
    chat_id: int,
    question_number: int,
) -> dict:
    async with SessionLocal() as db:
        session = await crud.get_session(db, session_id)
        if not session:
            return {"error": "Session not found"}

        messages = await crud.get_session_messages(db, session_id, limit=6)

        history = "\n".join([
            f"{'Q' if m.role == 'assistant' else 'A'}: {m.text[:200]}"
            for m in messages[-4:]
        ])

        prompt = f"""Ты интервьюер для позиции {session.track}.
Уровень: {session.difficulty}
Тип: {session.interview_type}
Язык: {session.language}

Это вопрос #{question_number} из 5.

Предыдущий диалог:
{history}

Задай следующий релевантный вопрос. Ответь ТОЛЬКО вопросом."""

        llm = get_llm_client(
            provider=settings.LLM_PROVIDER,
            model=settings.LLM_MODEL_TRAINING,
            api_key=settings.OPENAI_API_KEY if settings.LLM_PROVIDER == "openai" else settings.ANTHROPIC_API_KEY,
        )

        response = await llm.chat(
            messages=[ChatMessage(role="user", content=prompt)],
            temperature=0.8,
            max_tokens=256,
        )

        question = response.content.strip()

        await crud.add_message(
            db, session_id,
            role="assistant",
            kind="question",
            text=question,
            model_used=response.model,
            tokens_input=response.tokens_input,
            tokens_output=response.tokens_output,
            latency_ms=response.latency_ms,
        )

        cost = estimate_cost(
            settings.LLM_PROVIDER,
            settings.LLM_MODEL_TRAINING,
            response.tokens_input,
            response.tokens_output,
        )
        await crud.update_session_stats(
            db, session_id,
            tokens_input=response.tokens_input,
            tokens_output=response.tokens_output,
            cost_usd=cost,
        )
        await db.commit()

    send_message(chat_id, question)

    return {
        "question": question,
        "question_number": question_number,
        "tokens": response.total_tokens,
    }
