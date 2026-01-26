# app/worker/tasks.py
import asyncio
from datetime import datetime, timezone

from sqlalchemy import select

from app.db.session import SessionLocal
from app.db import crud
from app.worker.celery_app import celery
from app.worker.vacancy_fetch import parse_vacancy_url


@celery.task(name="fetch_vacancy")
def fetch_vacancy(session_id: int, vacancy_url: str) -> None:
    """
    ВАЖНО: этот таск НЕ пишет пользователю в чат.
    Он только обновляет sessions.vacancy_status / vacancy_text / vacancy_error в БД.
    UX и FSM решаем в боте (routers/start.py), чтобы не было гонок и странных сообщений.
    """

    async def _run():
        async with SessionLocal() as db:
            s = await crud.get_session(db, session_id)
            if not s:
                return
            # если уже не ждём или пользователь успел заменить вакансию — выходим
            if s.stage != "collecting" or s.vacancy_status != "pending" or (s.vacancy_url != vacancy_url):
                return

        try:
            text = await parse_vacancy_url(vacancy_url)
        except Exception as e:
            text = None
            err = f"exception: {type(e).__name__}: {e}"
        else:
            err = None

        async with SessionLocal() as db:
            s = await crud.get_session(db, session_id)
            if not s:
                return
            if s.stage != "collecting" or s.vacancy_status != "pending" or (s.vacancy_url != vacancy_url):
                return

            if text and len(text.strip()) >= 200:
                await crud.set_vacancy_ok(db, session_id, vacancy_text=text, vacancy_url=vacancy_url)
            else:
                await crud.set_vacancy_failed(
                    db,
                    session_id,
                    error=err or "too_short_or_blocked",
                    vacancy_url=vacancy_url,
                )
            await db.commit()

    asyncio.run(_run())


@celery.task(name="generate_snapshot")
def generate_snapshot(session_id: int, chat_id: int, lang: str = "uk") -> None:
    """
    Оставляю твою идею снапшота. Тут можно будет потом LLM подключать.
    """

    async def _run():
        from app.worker.telegram_api import send_message
        from app.i18n import tr

        async with SessionLocal() as db:
            s = await crud.get_session(db, session_id)
            if not s:
                return

            # забираем последние N сообщений
            res = await db.execute(
                select(crud.Message)
                .where(crud.Message.session_id == session_id)
                .order_by(crud.Message.id.asc())
            )
            msgs = res.scalars().all()

        lines = []
        for m in msgs[-50:]:
            lines.append(f"[{m.role}/{m.kind}] {m.text}")

        out = "\n".join(lines).strip() or "(empty)"
        send_message(chat_id, tr(lang, "snapshot_ready") + "\n\n" + out)

    asyncio.run(_run())
