import traceback
import time
from typing import Any, Awaitable, Callable

from aiogram import BaseMiddleware
from aiogram.types import Message, CallbackQuery, Update, TelegramObject

from app.logging_config import get_logger
from app.db.session import SessionLocal
from app.db.models import UserActivity, ErrorLog, UserSettings

logger = get_logger(__name__)


class LoggingMiddleware(BaseMiddleware):
    """Log all incoming messages and callbacks; persist activity and errors to DB."""

    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        start_time = time.time()

        chat_id = None
        username = None
        first_name = None
        action = "unknown"
        message_text = None

        if isinstance(event, Message):
            chat_id = event.chat.id
            username = event.from_user.username if event.from_user else None
            first_name = event.from_user.first_name if event.from_user else None
            message_text = event.text
            if event.document:
                action = "document_upload"
            elif message_text and message_text.startswith("/"):
                action = f"command:{message_text.split()[0]}"
            else:
                action = "message"

        elif isinstance(event, CallbackQuery):
            chat_id = event.message.chat.id if event.message else None
            username = event.from_user.username if event.from_user else None
            first_name = event.from_user.first_name if event.from_user else None
            action = f"callback:{event.data}"

        logger.info(
            f"Incoming: {action}",
            chat_id=chat_id,
            action=action,
            extra={"username": username, "first_name": first_name}
        )

        session_id = None
        state = data.get("state")
        if state:
            try:
                state_data = await state.get_data()
                session_id = state_data.get("session_id")
            except Exception:
                pass

        result = None
        error_occurred = False
        try:
            result = await handler(event, data)
        except Exception as e:
            error_occurred = True
            duration_ms = int((time.time() - start_time) * 1000)

            logger.exception(
                f"Error in handler: {type(e).__name__}: {str(e)}",
                chat_id=chat_id,
                session_id=session_id,
                action=action,
                error=str(e)
            )

            await self._log_error_to_db(
                chat_id=chat_id,
                session_id=session_id,
                error=e,
                action=action
            )

            try:
                if isinstance(event, Message):
                    await event.answer(
                        "Произошла ошибка. Попробуйте позже или начните заново /start"
                    )
                elif isinstance(event, CallbackQuery):
                    await event.answer("Произошла ошибка", show_alert=True)
            except Exception:
                pass

            raise

        finally:
            duration_ms = int((time.time() - start_time) * 1000)

            try:
                await self._log_activity_to_db(
                    chat_id=chat_id,
                    session_id=session_id,
                    action=action,
                    message_text=message_text[:500] if message_text else None,
                    duration_ms=duration_ms,
                    username=username,
                    first_name=first_name,
                    is_error=error_occurred
                )
            except Exception as e:
                logger.warning(f"Failed to log activity: {e}")

        return result

    async def _log_activity_to_db(
        self,
        chat_id: int | None,
        session_id: int | None,
        action: str,
        message_text: str | None,
        duration_ms: int,
        username: str | None = None,
        first_name: str | None = None,
        is_error: bool = False,
    ) -> None:
        """Save user activity to database."""
        if not chat_id:
            return

        try:
            async with SessionLocal() as db:
                from sqlalchemy import select
                result = await db.execute(
                    select(UserSettings).where(UserSettings.chat_id == chat_id)
                )
                user = result.scalar_one_or_none()

                if user:
                    if username and user.username != username:
                        user.username = username
                    if first_name and user.first_name != first_name:
                        user.first_name = first_name

                activity = UserActivity(
                    chat_id=chat_id,
                    session_id=session_id,
                    action=action,
                    action_type="error" if is_error else "user",
                    message_text=message_text,
                    duration_ms=duration_ms,
                    details={"username": username} if username else None,
                )
                db.add(activity)
                await db.commit()
        except Exception as e:
            logger.warning(f"Failed to save activity: {e}")

    async def _log_error_to_db(
        self,
        chat_id: int | None,
        session_id: int | None,
        error: Exception,
        action: str,
    ) -> None:
        """Save error details to database."""
        try:
            async with SessionLocal() as db:
                error_log = ErrorLog(
                    chat_id=chat_id,
                    session_id=session_id,
                    error_type=type(error).__name__,
                    error_message=str(error)[:1000],
                    error_traceback=traceback.format_exc()[:4000],
                    module=action.split(":")[0] if ":" in action else action,
                    function=action,
                )
                db.add(error_log)
                await db.commit()
        except Exception as e:
            logger.warning(f"Failed to save error log: {e}")


class ThrottlingMiddleware(BaseMiddleware):
    """Rate-limit users to prevent spam (default: 0.5 req/s per user)."""

    def __init__(self, rate_limit: float = 0.5):
        self.rate_limit = rate_limit
        self.user_last_request: dict[int, float] = {}

    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        chat_id = None

        if isinstance(event, Message):
            chat_id = event.chat.id
        elif isinstance(event, CallbackQuery):
            chat_id = event.message.chat.id if event.message else None

        if chat_id:
            now = time.time()
            last_request = self.user_last_request.get(chat_id, 0)

            if now - last_request < self.rate_limit:
                logger.debug(f"Throttled user {chat_id}")
                return None

            self.user_last_request[chat_id] = now

            if len(self.user_last_request) > 10000:
                cutoff = now - 3600
                self.user_last_request = {
                    k: v for k, v in self.user_last_request.items() if v > cutoff
                }

        return await handler(event, data)


class BillingCheckMiddleware(BaseMiddleware):
    """Placeholder for billing/quota enforcement before paid interview features."""

    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        return await handler(event, data)


def setup_middlewares(dp) -> None:
    """Register all middleware on the dispatcher. Order matters: first registered = first called."""
    dp.message.middleware(ThrottlingMiddleware(rate_limit=0.3))
    dp.callback_query.middleware(ThrottlingMiddleware(rate_limit=0.3))

    dp.message.middleware(LoggingMiddleware())
    dp.callback_query.middleware(LoggingMiddleware())
