# app/logging_config.py
"""
Структурированное логирование для interview-bot.
Логи сохраняются в файл и в БД (для админки).
"""

import logging
import logging.handlers
import json
import os
from datetime import datetime
from typing import Any
from pathlib import Path


class JSONFormatter(logging.Formatter):
    """Форматтер для структурированных JSON логов"""

    def format(self, record: logging.LogRecord) -> str:
        log_data = {
            "timestamp": datetime.utcnow().isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }

        # Добавляем extra поля
        for key in ["chat_id", "session_id", "action", "error", "duration_ms", "extra"]:
            if hasattr(record, key):
                log_data[key] = getattr(record, key)

        # Добавляем exception info
        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)

        return json.dumps(log_data, ensure_ascii=False, default=str)


class ConsoleFormatter(logging.Formatter):
    """Красивый форматтер для консоли"""

    COLORS = {
        "DEBUG": "\033[36m",     # Cyan
        "INFO": "\033[32m",      # Green
        "WARNING": "\033[33m",   # Yellow
        "ERROR": "\033[31m",     # Red
        "CRITICAL": "\033[35m",  # Magenta
    }
    RESET = "\033[0m"

    def format(self, record: logging.LogRecord) -> str:
        color = self.COLORS.get(record.levelname, self.RESET)

        # Базовое сообщение
        base = f"{color}[{record.levelname}]{self.RESET} {record.name}: {record.getMessage()}"

        # Добавляем контекст если есть
        extras = []
        if hasattr(record, "chat_id"):
            extras.append(f"user={record.chat_id}")
        if hasattr(record, "session_id"):
            extras.append(f"session={record.session_id}")
        if hasattr(record, "action"):
            extras.append(f"action={record.action}")
        if hasattr(record, "duration_ms"):
            extras.append(f"duration={record.duration_ms}ms")

        if extras:
            base += f" [{', '.join(extras)}]"

        return base


def setup_logging(
    log_level: str = "INFO",
    log_dir: str = "logs",
    log_to_file: bool = True,
    log_to_console: bool = True,
) -> None:
    """
    Настройка логирования.

    Args:
        log_level: Уровень логирования (DEBUG, INFO, WARNING, ERROR)
        log_dir: Директория для файлов логов
        log_to_file: Писать ли в файл
        log_to_console: Писать ли в консоль
    """
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, log_level.upper(), logging.INFO))

    # Очищаем существующие handlers
    root_logger.handlers.clear()

    # Console handler
    if log_to_console:
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(ConsoleFormatter())
        console_handler.setLevel(logging.DEBUG)
        root_logger.addHandler(console_handler)

    # File handler (JSON, rotating)
    if log_to_file:
        log_path = Path(log_dir)
        log_path.mkdir(parents=True, exist_ok=True)

        file_handler = logging.handlers.RotatingFileHandler(
            log_path / "bot.log",
            maxBytes=10 * 1024 * 1024,  # 10 MB
            backupCount=10,
            encoding="utf-8",
        )
        file_handler.setFormatter(JSONFormatter())
        file_handler.setLevel(logging.DEBUG)
        root_logger.addHandler(file_handler)

        # Отдельный файл для ошибок
        error_handler = logging.handlers.RotatingFileHandler(
            log_path / "errors.log",
            maxBytes=10 * 1024 * 1024,
            backupCount=5,
            encoding="utf-8",
        )
        error_handler.setFormatter(JSONFormatter())
        error_handler.setLevel(logging.ERROR)
        root_logger.addHandler(error_handler)

    # Настраиваем уровни для сторонних библиотек
    logging.getLogger("aiogram").setLevel(logging.WARNING)
    logging.getLogger("aiohttp").setLevel(logging.WARNING)
    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)
    logging.getLogger("celery").setLevel(logging.INFO)
    logging.getLogger("httpx").setLevel(logging.WARNING)


class BotLogger:
    """
    Обёртка для логирования с контекстом пользователя.
    Использование:
        logger = BotLogger(__name__)
        logger.info("User started", chat_id=123, action="start")
    """

    def __init__(self, name: str):
        self._logger = logging.getLogger(name)

    def _log(self, level: int, message: str, **kwargs: Any) -> None:
        extra = {}
        for key in ["chat_id", "session_id", "action", "error", "duration_ms", "extra"]:
            if key in kwargs:
                extra[key] = kwargs.pop(key)

        self._logger.log(level, message, extra=extra, **kwargs)

    def debug(self, message: str, **kwargs: Any) -> None:
        self._log(logging.DEBUG, message, **kwargs)

    def info(self, message: str, **kwargs: Any) -> None:
        self._log(logging.INFO, message, **kwargs)

    def warning(self, message: str, **kwargs: Any) -> None:
        self._log(logging.WARNING, message, **kwargs)

    def error(self, message: str, **kwargs: Any) -> None:
        self._log(logging.ERROR, message, **kwargs)

    def critical(self, message: str, **kwargs: Any) -> None:
        self._log(logging.CRITICAL, message, **kwargs)

    def exception(self, message: str, **kwargs: Any) -> None:
        self._log(logging.ERROR, message, exc_info=True, **kwargs)


def get_logger(name: str) -> BotLogger:
    """Получить логгер с контекстом"""
    return BotLogger(name)
