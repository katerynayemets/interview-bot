import asyncio
import logging
from sqlalchemy import select

from app.db.session import SessionLocal
from app.db import crud
from app.worker.celery_app import celery
from app.worker.vacancy_fetch import parse_vacancy_url

log = logging.getLogger(__name__)

_LOOP: asyncio.AbstractEventLoop | None = None


def run_coro(coro):
    """
    Run a coroutine on a single per-worker event loop.

    Celery prefork workers must not call asyncio.run() per task when sharing
    an async engine/pool — doing so causes 'Future attached to a different loop'
    and 'another operation is in progress' errors. We keep one loop per worker
    process and drive all coroutines through it.
    """
    global _LOOP
    if _LOOP is None or _LOOP.is_closed():
        _LOOP = asyncio.new_event_loop()
        asyncio.set_event_loop(_LOOP)
    return _LOOP.run_until_complete(coro)


@celery.task(name="fetch_vacancy")
def fetch_vacancy(session_id: int, vacancy_url: str) -> None:
    async def _run():
        async with SessionLocal() as db:
            s = await crud.get_session(db, session_id)
            if not s:
                return
            if s.stage != "collecting" or s.vacancy_status != "pending" or (s.vacancy_url != vacancy_url):
                return

        try:
            text = await parse_vacancy_url(vacancy_url)
            err = None
        except Exception as e:
            text = None
            err = f"exception: {type(e).__name__}: {e}"

        async with SessionLocal() as db:
            s = await crud.get_session(db, session_id)
            if not s:
                return
            if s.stage != "collecting" or s.vacancy_status != "pending" or (s.vacancy_url != vacancy_url):
                return

            length = len((text or "").strip())
            log.info("vacancy parsed len=%s url=%s", length, vacancy_url)

            if text and length >= 200:
                await crud.set_vacancy_ok(db, session_id, vacancy_text=text, vacancy_url=vacancy_url)
            else:
                await crud.set_vacancy_failed(
                    db,
                    session_id,
                    error=err or "too_short_or_blocked",
                    vacancy_url=vacancy_url,
                )
            await db.commit()

    run_coro(_run())


@celery.task(name="generate_snapshot")
def generate_snapshot(session_id: int, chat_id: int, lang: str = "uk") -> None:
    async def _run():
        from app.worker.telegram_api import send_message
        from app.i18n import tr

        async with SessionLocal() as db:
            s = await crud.get_session(db, session_id)
            if not s:
                return

            res = await db.execute(
                select(crud.Message)
                .where(crud.Message.session_id == session_id)
                .order_by(crud.Message.id.asc())
            )
            msgs = res.scalars().all()

        lines = [f"[{m.role}/{m.kind}] {m.text}" for m in msgs[-50:]]
        out = "\n".join(lines).strip() or "(empty)"

        send_message(chat_id, tr(lang, "snapshot_ready") + "\n\n" + out)

    run_coro(_run())
