# app/db/models.py
import datetime as dt
from sqlalchemy import String, Text, DateTime, Integer, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base


class UserSettings(Base):
    __tablename__ = "user_settings"

    chat_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    language: Mapped[str] = mapped_column(String(8), default="uk")
    track: Mapped[str] = mapped_column(String(32), default="data")
    mode: Mapped[str] = mapped_column(String(32), default="training")

    created_at: Mapped[dt.datetime] = mapped_column(DateTime, default=dt.datetime.utcnow)
    updated_at: Mapped[dt.datetime] = mapped_column(DateTime, default=dt.datetime.utcnow, onupdate=dt.datetime.utcnow)


class Session(Base):
    __tablename__ = "sessions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    chat_id: Mapped[int] = mapped_column(Integer, index=True)
    created_at: Mapped[dt.datetime] = mapped_column(DateTime, default=dt.datetime.utcnow)
    updated_at: Mapped[dt.datetime] = mapped_column(DateTime, default=dt.datetime.utcnow, onupdate=dt.datetime.utcnow)

    # снапшот настроек на прогон
    language: Mapped[str] = mapped_column(String(8), default="uk")
    track: Mapped[str] = mapped_column(String(32), default="data")
    mode: Mapped[str] = mapped_column(String(32), default="training")

    # входные данные
    vacancy_url: Mapped[str | None] = mapped_column(String(512), nullable=True)
    vacancy_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    cv_text: Mapped[str | None] = mapped_column(Text, nullable=True)

    # статусы (для воркеров/парсеров)
    vacancy_status: Mapped[str] = mapped_column(String(16), default="empty")  # empty|pending|ok|failed
    vacancy_error: Mapped[str | None] = mapped_column(String(512), nullable=True)
    cv_status: Mapped[str] = mapped_column(String(16), default="empty")       # empty|pending|ok|failed
    cv_error: Mapped[str | None] = mapped_column(String(512), nullable=True)

    stage: Mapped[str] = mapped_column(String(16), default="collecting")      # collecting|interview|done

    messages: Mapped[list["Message"]] = relationship(
        back_populates="session",
        cascade="all, delete-orphan",
        order_by="Message.id",
    )

    # legacy
    answers: Mapped[list["Answer"]] = relationship(back_populates="session", cascade="all, delete-orphan")


class Message(Base):
    __tablename__ = "messages"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    session_id: Mapped[int] = mapped_column(ForeignKey("sessions.id"), index=True)
    created_at: Mapped[dt.datetime] = mapped_column(DateTime, default=dt.datetime.utcnow)

    role: Mapped[str] = mapped_column(String(16))  # user|assistant|system
    kind: Mapped[str] = mapped_column(String(16), default="message")  # question|answer|feedback|event|message
    text: Mapped[str] = mapped_column(Text)

    session: Mapped["Session"] = relationship(back_populates="messages")


class Answer(Base):
    __tablename__ = "answers"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    session_id: Mapped[int] = mapped_column(ForeignKey("sessions.id"), index=True)
    step: Mapped[str] = mapped_column(String(32))
    text: Mapped[str] = mapped_column(Text)

    session: Mapped["Session"] = relationship(back_populates="answers")
