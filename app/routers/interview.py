import asyncio

from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.utils.keyboard import InlineKeyboardBuilder

from app.states import InterviewFSM
from app.db.session import SessionLocal
from app.db import crud
from app.config import settings
from app.i18n import tr, DEFAULT_LANG
from app.logging_config import get_logger
from app.llm.client import get_llm_client, ChatMessage, estimate_cost
from app.llm.prompts import PromptManager
from app.llm.context import build_interview_context

logger = get_logger(__name__)

router = Router()

MAX_QUESTIONS_TRAINING = 5
MAX_QUESTIONS_REAL = 15


async def _resolve_lang(state: FSMContext, chat_id: int) -> str:
    data = await state.get_data()
    if data.get("lang"):
        return data["lang"]
    async with SessionLocal() as db:
        us = await crud.ensure_user_settings(db, chat_id)
        lang = us.language or DEFAULT_LANG
    await state.update_data(lang=lang)
    return lang


async def _get_session_id(state: FSMContext) -> int | None:
    data = await state.get_data()
    return data.get("session_id")


async def _count_questions_asked(db, session_id: int) -> int:
    messages = await crud.get_session_messages(db, session_id, limit=100)
    return sum(1 for m in messages if m.role == "assistant" and m.kind == "question")


async def _generate_and_send_question(
    msg: Message,
    state: FSMContext,
    session_id: int,
    lang: str,
):
    """Generate the next interview question via LLM and send it to the user."""

    async with SessionLocal() as db:
        session = await crud.get_session(db, session_id)
        if not session:
            await msg.answer(tr(lang, "session_not_found"))
            await state.clear()
            return

        questions_asked = await _count_questions_asked(db, session_id)
        max_questions = MAX_QUESTIONS_REAL if session.mode == "real" else MAX_QUESTIONS_TRAINING

        if questions_asked >= max_questions:
            await _finish_interview(msg, state, session_id, lang)
            return

        current_phase = await crud.get_current_phase(db, session_id)
        if not current_phase:
            next_phase = await crud.get_next_phase(db, session_id)
            if next_phase:
                await crud.start_phase(db, next_phase.id)
                await db.commit()
                current_phase = next_phase
            else:
                await _finish_interview(msg, state, session_id, lang)
                return

        phase_config = current_phase.phase_config or {}
        phase_questions_limit = phase_config.get("questions_count", 3)

        phase_messages = await crud.get_session_messages(
            db, session_id, limit=100, phase_id=current_phase.id
        )
        phase_questions = sum(1 for m in phase_messages if m.role == "assistant" and m.kind == "question")

        if phase_questions >= phase_questions_limit:
            await crud.complete_phase(db, current_phase.id)
            next_phase = await crud.get_next_phase(db, session_id)
            if next_phase:
                await crud.start_phase(db, next_phase.id)
                await db.commit()
                current_phase = next_phase
            else:
                await db.commit()
                await _finish_interview(msg, state, session_id, lang)
                return

        phase_type = current_phase.phase_type

        context = await build_interview_context(db, session_id, include_full_documents=True)

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

    await msg.bot.send_chat_action(msg.chat.id, "typing")

    try:
        llm = get_llm_client(
            provider=settings.LLM_PROVIDER,
            model=model,
            api_key=(
                settings.OPENAI_API_KEY
                if settings.LLM_PROVIDER == "openai"
                else settings.ANTHROPIC_API_KEY
            ),
        )

        messages = [
            ChatMessage(role="system", content=system_prompt),
            ChatMessage(role="user", content=question_prompt),
        ]

        response = await llm.chat(
            messages=messages,
            temperature=settings.LLM_TEMPERATURE,
            max_tokens=max_tokens,
        )

        question_text = response.content.strip()

        # Retry with a larger token budget for reasoning models
        if not question_text and response.finish_reason == "length":
            logger.warning(
                f"Empty LLM response (finish_reason=length), retrying with 2x tokens",
                session_id=session_id,
            )
            response = await llm.chat(
                messages=messages,
                temperature=settings.LLM_TEMPERATURE,
                max_tokens=max_tokens * 2,
            )
            question_text = response.content.strip()

        if not question_text:
            question_text = "..."

        async with SessionLocal() as db:
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
                settings.LLM_PROVIDER, model,
                response.tokens_input, response.tokens_output,
            )
            await crud.update_session_stats(
                db, session_id,
                tokens_input=response.tokens_input,
                tokens_output=response.tokens_output,
                cost_usd=cost,
            )
            await db.commit()

        logger.info(
            f"Question generated for session {session_id}",
            session_id=session_id,
            chat_id=msg.chat.id,
            action="llm_question",
        )

        question_number = questions_asked + 1
        prefix = f"**{tr(lang, 'question_label')} {question_number}/{max_questions}**\n\n"
        await msg.answer(prefix + question_text)

        async with SessionLocal() as db:
            session = await crud.get_session(db, session_id)

        if session and session.mode == "real" and settings.INTERVIEW_TIMER_ENABLED:
            await state.update_data(
                timer_active=True,
                question_number=question_number,
            )
            asyncio.create_task(
                _timer_warning(msg, state, session_id, lang, question_number)
            )

    except Exception as e:
        logger.exception(f"LLM error: {e}", session_id=session_id, chat_id=msg.chat.id)
        await msg.answer(tr(lang, "llm_error"))


async def _timer_warning(
    msg: Message,
    state: FSMContext,
    session_id: int,
    lang: str,
    question_number: int,
):
    """Send a warning and expiry notification for real-mode answer timers."""
    timer_seconds = settings.INTERVIEW_TIMER_SECONDS

    await asyncio.sleep(timer_seconds * 2 // 3)

    data = await state.get_data()
    if data.get("question_number") != question_number:
        return
    if data.get("session_id") != session_id:
        return

    remaining = timer_seconds // 3
    await msg.answer(tr(lang, "timer_warning").format(seconds=remaining))

    await asyncio.sleep(remaining)

    data = await state.get_data()
    if data.get("question_number") != question_number:
        return
    if data.get("session_id") != session_id:
        return

    await msg.answer(tr(lang, "timer_expired"))


async def _finish_interview(
    msg: Message,
    state: FSMContext,
    session_id: int,
    lang: str,
):
    """Complete the interview and generate LLM feedback."""
    await msg.answer(tr(lang, "interview_finishing"))

    async with SessionLocal() as db:
        current_phase = await crud.get_current_phase(db, session_id)
        if current_phase:
            await crud.complete_phase(db, current_phase.id)
        await crud.update_session_stage(db, session_id, "generating_feedback")
        await db.commit()

    await state.set_state(InterviewFSM.generating)

    try:
        await msg.bot.send_chat_action(msg.chat.id, "typing")
        await _generate_feedback(msg, session_id, lang)
    except Exception as e:
        logger.exception(f"Feedback error: {e}", session_id=session_id)
        await msg.answer(tr(lang, "feedback_error"))

    async with SessionLocal() as db:
        await crud.update_session_stage(db, session_id, "done")

        user = await crud.get_user_settings(db, msg.chat.id)
        if user:
            user.total_interviews += 1
            stats = await crud.get_session_stats(db, session_id)
            if stats:
                user.total_tokens_used += stats.total_tokens_input + stats.total_tokens_output
                user.total_spent_usd += stats.estimated_cost_usd
        await db.commit()

    kb = InlineKeyboardBuilder()
    kb.button(text=tr(lang, "btn_rate_interview"), callback_data="rate:start")
    kb.button(text=tr(lang, "btn_new_interview"), callback_data="new_interview")
    kb.adjust(1)

    await msg.answer(tr(lang, "interview_done"), reply_markup=kb.as_markup())
    await state.clear()
    await state.update_data(lang=lang)


async def _generate_feedback(msg: Message, session_id: int, lang: str):
    """Generate comprehensive feedback via LLM and persist to the database."""

    async with SessionLocal() as db:
        context = await build_interview_context(db, session_id, include_full_documents=True)
        session = await crud.get_session(db, session_id)
        if not session:
            return

        prompt_manager = PromptManager(
            interview_type=session.interview_type,
            track=session.track,
            difficulty=session.difficulty,
            language=session.language,
            cv_summary=context.cv_summary,
            vacancy_summary=context.vacancy_summary,
        )

        feedback_prompt = prompt_manager.build_feedback_prompt(
            full_conversation=context.conversation,
            question_scores=[],
        )

        model = settings.LLM_MODEL_REAL if session.mode == "real" else settings.LLM_MODEL_TRAINING

        llm = get_llm_client(
            provider=settings.LLM_PROVIDER,
            model=model,
            api_key=(
                settings.OPENAI_API_KEY
                if settings.LLM_PROVIDER == "openai"
                else settings.ANTHROPIC_API_KEY
            ),
        )

        response = await llm.chat(
            messages=[ChatMessage(role="user", content=feedback_prompt)],
            temperature=0.5,
            max_tokens=4096,
        )

        # Retry for reasoning models that may exhaust the token budget
        if not response.content.strip() and response.finish_reason == "length":
            logger.warning("Empty feedback response, retrying with more tokens", session_id=session_id)
            response = await llm.chat(
                messages=[ChatMessage(role="user", content=feedback_prompt)],
                temperature=0.5,
                max_tokens=8192,
            )

        import json
        feedback_data = {}
        try:
            content = response.content
            start = content.find("{")
            end = content.rfind("}") + 1
            if start >= 0 and end > start:
                feedback_data = json.loads(content[start:end])
        except (json.JSONDecodeError, ValueError):
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
            response.tokens_input, response.tokens_output,
        )
        await crud.update_session_stats(
            db, session_id,
            tokens_input=response.tokens_input,
            tokens_output=response.tokens_output,
            cost_usd=cost,
        )
        await db.commit()

    feedback_text = _format_feedback(feedback_data, lang)
    await msg.answer(feedback_text, parse_mode="Markdown")


def _format_feedback(feedback: dict, lang: str) -> str:
    if not feedback:
        return tr(lang, "feedback_empty")

    lines = []
    lines.append(f"**{tr(lang, 'feedback_title')}**\n")

    if feedback.get("overall_score"):
        lines.append(f"{tr(lang, 'feedback_overall')}: **{feedback['overall_score']}/10**\n")

    scores = []
    if feedback.get("technical_score"):
        scores.append(f"{tr(lang, 'feedback_technical')}: {feedback['technical_score']}/10")
    if feedback.get("communication_score"):
        scores.append(f"{tr(lang, 'feedback_communication')}: {feedback['communication_score']}/10")
    if feedback.get("problem_solving_score"):
        scores.append(f"{tr(lang, 'feedback_problem_solving')}: {feedback['problem_solving_score']}/10")

    if scores:
        lines.append(" | ".join(scores) + "\n")

    if feedback.get("strengths"):
        lines.append(f"\n**{tr(lang, 'feedback_strengths')}:**")
        for s in feedback["strengths"][:5]:
            lines.append(f"• {s}")

    if feedback.get("improvements"):
        lines.append(f"\n**{tr(lang, 'feedback_improvements')}:**")
        for i in feedback["improvements"][:5]:
            lines.append(f"• {i}")

    if feedback.get("recommended_topics"):
        lines.append(f"\n**{tr(lang, 'feedback_topics')}:**")
        for t in feedback["recommended_topics"][:5]:
            lines.append(f"• {t}")

    if feedback.get("detailed_feedback"):
        lines.append(f"\n{feedback['detailed_feedback'][:1500]}")

    return "\n".join(lines)


@router.message(InterviewFSM.interview_phase, F.text & ~F.text.startswith("/"))
async def handle_answer(msg: Message, state: FSMContext):
    """Handle user answer during the interview phase."""
    lang = await _resolve_lang(state, msg.chat.id)
    session_id = await _get_session_id(state)

    if not session_id:
        await msg.answer(tr(lang, "session_not_found"))
        await state.clear()
        return

    async with SessionLocal() as db:
        current_phase = await crud.get_current_phase(db, session_id)
        phase_id = current_phase.id if current_phase else None

        await crud.add_message(
            db, session_id,
            role="user",
            kind="answer",
            text=msg.text,
            phase_id=phase_id,
        )
        await db.commit()

    data = await state.get_data()
    await state.update_data(
        question_number=(data.get("question_number", 0) + 1),
        timer_active=False,
    )

    await _generate_and_send_question(msg, state, session_id, lang)


@router.message(InterviewFSM.q1, F.text & ~F.text.startswith("/"))
async def q1_legacy(msg: Message, state: FSMContext):
    """Legacy handler — redirects to LLM flow."""
    lang = await _resolve_lang(state, msg.chat.id)
    session_id = await _get_session_id(state)
    if not session_id:
        await msg.answer(tr(lang, "session_not_found"))
        await state.clear()
        return

    async with SessionLocal() as db:
        await crud.add_message(db, session_id, role="user", kind="answer", text=msg.text)
        await db.commit()

    await state.set_state(InterviewFSM.interview_phase)
    await _generate_and_send_question(msg, state, session_id, lang)


@router.message(InterviewFSM.q2, F.text & ~F.text.startswith("/"))
async def q2_legacy(msg: Message, state: FSMContext):
    """Legacy handler — redirects to LLM flow."""
    await q1_legacy(msg, state)


@router.message(InterviewFSM.q3, F.text & ~F.text.startswith("/"))
async def q3_legacy(msg: Message, state: FSMContext):
    """Legacy handler — redirects to LLM flow."""
    await q1_legacy(msg, state)


@router.callback_query(F.data == "new_interview")
async def new_interview(cb: CallbackQuery, state: FSMContext):
    await cb.answer()
    await cb.message.answer("/start")


@router.callback_query(F.data == "rate:start")
async def rate_interview_start(cb: CallbackQuery, state: FSMContext):
    lang = await _resolve_lang(state, cb.message.chat.id)
    await cb.answer()

    kb = InlineKeyboardBuilder()
    for i in range(1, 6):
        stars = "⭐" * i
        kb.button(text=stars, callback_data=f"rate:{i}")
    kb.adjust(5)

    await cb.message.answer(tr(lang, "rate_prompt"), reply_markup=kb.as_markup())


@router.callback_query(F.data.startswith("rate:") & ~F.data.in_({"rate:start"}))
async def rate_interview(cb: CallbackQuery, state: FSMContext):
    """Save the user's interview rating."""
    lang = await _resolve_lang(state, cb.message.chat.id)
    rating = int(cb.data.split(":")[1])
    await cb.answer()

    data = await state.get_data()
    session_id = data.get("last_session_id") or data.get("session_id")

    if session_id:
        async with SessionLocal() as db:
            await crud.add_user_feedback(db, session_id, rating=rating)
            await db.commit()

    await cb.message.answer(tr(lang, "rate_thanks"))
