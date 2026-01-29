# app/db/models.py
import datetime as dt
from sqlalchemy import String, Text, DateTime, Integer, Float, ForeignKey, JSON, Boolean, BigInteger
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base


class UserSettings(Base):
    """Персистентные настройки пользователя (дефолты для новых сессий)"""
    __tablename__ = "user_settings"

    chat_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    username: Mapped[str | None] = mapped_column(String(64), nullable=True)  # @username
    first_name: Mapped[str | None] = mapped_column(String(64), nullable=True)
    last_name: Mapped[str | None] = mapped_column(String(64), nullable=True)

    language: Mapped[str] = mapped_column(String(8), default="uk")
    track: Mapped[str] = mapped_column(String(32), default="data")
    mode: Mapped[str] = mapped_column(String(32), default="training")  # training|real

    # Настройки интервью
    interview_type: Mapped[str] = mapped_column(String(32), default="mixed")  # hr_soft|technical_hard|mixed
    difficulty: Mapped[str] = mapped_column(String(16), default="middle")  # junior|middle|senior|lead

    # === Биллинг ===
    subscription_tier: Mapped[str] = mapped_column(String(16), default="free")  # free|pro|premium
    balance_usd: Mapped[float] = mapped_column(Float, default=0.0)  # баланс для pay-per-use
    free_interviews_left: Mapped[int] = mapped_column(Integer, default=3)  # бесплатные интервью
    total_interviews: Mapped[int] = mapped_column(Integer, default=0)  # всего проведено
    total_tokens_used: Mapped[int] = mapped_column(Integer, default=0)  # всего токенов
    total_spent_usd: Mapped[float] = mapped_column(Float, default=0.0)  # всего потрачено

    # Статус
    is_blocked: Mapped[bool] = mapped_column(Boolean, default=False)
    is_admin: Mapped[bool] = mapped_column(Boolean, default=False)

    created_at: Mapped[dt.datetime] = mapped_column(DateTime, default=dt.datetime.utcnow)
    updated_at: Mapped[dt.datetime] = mapped_column(DateTime, default=dt.datetime.utcnow, onupdate=dt.datetime.utcnow)

    # Relationships
    activities: Mapped[list["UserActivity"]] = relationship(back_populates="user", cascade="all, delete-orphan")
    transactions: Mapped[list["Transaction"]] = relationship(back_populates="user", cascade="all, delete-orphan")


class Session(Base):
    """Сессия интервью - легкая таблица с настройками"""
    __tablename__ = "sessions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    chat_id: Mapped[int] = mapped_column(Integer, index=True)
    created_at: Mapped[dt.datetime] = mapped_column(DateTime, default=dt.datetime.utcnow)
    updated_at: Mapped[dt.datetime] = mapped_column(DateTime, default=dt.datetime.utcnow, onupdate=dt.datetime.utcnow)

    # Снапшот настроек на момент старта сессии
    language: Mapped[str] = mapped_column(String(8), default="uk")
    track: Mapped[str] = mapped_column(String(32), default="data")
    mode: Mapped[str] = mapped_column(String(32), default="training")  # training|real
    interview_type: Mapped[str] = mapped_column(String(32), default="mixed")  # hr_soft|technical_hard|mixed
    difficulty: Mapped[str] = mapped_column(String(16), default="middle")  # junior|middle|senior|lead

    # Статусы документов (сами тексты в SessionDocument)
    vacancy_status: Mapped[str] = mapped_column(String(16), default="empty")  # empty|skipped|pending|ok|failed
    vacancy_error: Mapped[str | None] = mapped_column(String(512), nullable=True)
    cv_status: Mapped[str] = mapped_column(String(16), default="empty")  # empty|skipped|pending|ok|failed
    cv_error: Mapped[str | None] = mapped_column(String(512), nullable=True)

    # Краткие превью для UI (до 500 символов)
    vacancy_summary: Mapped[str | None] = mapped_column(String(512), nullable=True)
    cv_summary: Mapped[str | None] = mapped_column(String(512), nullable=True)

    # Legacy поля (для обратной совместимости, будут мигрированы)
    vacancy_url: Mapped[str | None] = mapped_column(String(512), nullable=True)
    vacancy_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    cv_text: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Этап сессии
    stage: Mapped[str] = mapped_column(String(32), default="collecting")  # collecting|interview|generating_feedback|done

    # Relationships
    documents: Mapped[list["SessionDocument"]] = relationship(
        back_populates="session",
        cascade="all, delete-orphan",
    )
    phases: Mapped[list["InterviewPhase"]] = relationship(
        back_populates="session",
        cascade="all, delete-orphan",
        order_by="InterviewPhase.phase_order",
    )
    messages: Mapped[list["Message"]] = relationship(
        back_populates="session",
        cascade="all, delete-orphan",
        order_by="Message.id",
    )
    stats: Mapped["SessionStats | None"] = relationship(
        back_populates="session",
        cascade="all, delete-orphan",
        uselist=False,
    )
    feedback: Mapped["InterviewFeedback | None"] = relationship(
        back_populates="session",
        cascade="all, delete-orphan",
        uselist=False,
    )
    # Legacy
    answers: Mapped[list["Answer"]] = relationship(back_populates="session", cascade="all, delete-orphan")


class SessionDocument(Base):
    """Документы сессии (резюме, вакансия) - отдельная таблица для длинных текстов"""
    __tablename__ = "session_documents"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    session_id: Mapped[int] = mapped_column(ForeignKey("sessions.id"), index=True)
    created_at: Mapped[dt.datetime] = mapped_column(DateTime, default=dt.datetime.utcnow)

    doc_type: Mapped[str] = mapped_column(String(16))  # cv|vacancy
    source_url: Mapped[str | None] = mapped_column(String(512), nullable=True)  # URL если парсили
    raw_text: Mapped[str | None] = mapped_column(Text, nullable=True)  # оригинальный текст
    processed_text: Mapped[str | None] = mapped_column(Text, nullable=True)  # очищенный/анонимизированный
    token_count: Mapped[int] = mapped_column(Integer, default=0)  # примерное кол-во токенов

    session: Mapped["Session"] = relationship(back_populates="documents")


class InterviewPhase(Base):
    """Фазы интервью для структурированного flow"""
    __tablename__ = "interview_phases"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    session_id: Mapped[int] = mapped_column(ForeignKey("sessions.id"), index=True)

    phase_type: Mapped[str] = mapped_column(String(32))  # intro|warmup|technical_deep|behavioral|questions_to_company|closing
    phase_order: Mapped[int] = mapped_column(Integer)  # порядок фазы в интервью
    status: Mapped[str] = mapped_column(String(16), default="pending")  # pending|active|completed|skipped

    started_at: Mapped[dt.datetime | None] = mapped_column(DateTime, nullable=True)
    completed_at: Mapped[dt.datetime | None] = mapped_column(DateTime, nullable=True)

    # Конфиг фазы (кол-во вопросов, темы, и т.д.)
    phase_config: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    session: Mapped["Session"] = relationship(back_populates="phases")


class Message(Base):
    """Сообщения диалога с LLM трекингом"""
    __tablename__ = "messages"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    session_id: Mapped[int] = mapped_column(ForeignKey("sessions.id"), index=True)
    phase_id: Mapped[int | None] = mapped_column(ForeignKey("interview_phases.id"), nullable=True, index=True)
    created_at: Mapped[dt.datetime] = mapped_column(DateTime, default=dt.datetime.utcnow)

    role: Mapped[str] = mapped_column(String(16))  # user|assistant|system
    kind: Mapped[str] = mapped_column(String(16), default="message")  # question|answer|feedback|event|message
    text: Mapped[str] = mapped_column(Text)

    # LLM tracking
    model_used: Mapped[str | None] = mapped_column(String(64), nullable=True)  # gpt-4|claude-3-opus|etc
    tokens_input: Mapped[int] = mapped_column(Integer, default=0)  # токены промпта
    tokens_output: Mapped[int] = mapped_column(Integer, default=0)  # токены ответа
    latency_ms: Mapped[int] = mapped_column(Integer, default=0)  # время ответа в мс

    session: Mapped["Session"] = relationship(back_populates="messages")


class SessionStats(Base):
    """Агрегированная статистика сессии"""
    __tablename__ = "session_stats"

    session_id: Mapped[int] = mapped_column(ForeignKey("sessions.id"), primary_key=True)

    total_tokens_input: Mapped[int] = mapped_column(Integer, default=0)
    total_tokens_output: Mapped[int] = mapped_column(Integer, default=0)
    total_messages: Mapped[int] = mapped_column(Integer, default=0)
    estimated_cost_usd: Mapped[float] = mapped_column(Float, default=0.0)

    # Время интервью
    interview_duration_sec: Mapped[int] = mapped_column(Integer, default=0)

    updated_at: Mapped[dt.datetime] = mapped_column(DateTime, default=dt.datetime.utcnow, onupdate=dt.datetime.utcnow)

    session: Mapped["Session"] = relationship(back_populates="stats")


class InterviewFeedback(Base):
    """Обратная связь и оценка интервью"""
    __tablename__ = "interview_feedback"

    session_id: Mapped[int] = mapped_column(ForeignKey("sessions.id"), primary_key=True)
    created_at: Mapped[dt.datetime] = mapped_column(DateTime, default=dt.datetime.utcnow)

    # Автоматическая оценка от LLM (1-10)
    technical_score: Mapped[int | None] = mapped_column(Integer, nullable=True)
    communication_score: Mapped[int | None] = mapped_column(Integer, nullable=True)
    problem_solving_score: Mapped[int | None] = mapped_column(Integer, nullable=True)
    overall_score: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # Детализация
    strengths: Mapped[list | None] = mapped_column(JSON, nullable=True)  # ["хорошо объясняет", "знает SQL"]
    improvements: Mapped[list | None] = mapped_column(JSON, nullable=True)  # ["углубить алгоритмы"]
    detailed_feedback: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Рекомендации
    recommended_topics: Mapped[list | None] = mapped_column(JSON, nullable=True)  # темы для изучения

    # Пользовательская оценка бота
    user_rating: Mapped[int | None] = mapped_column(Integer, nullable=True)  # 1-5 звезд
    user_comment: Mapped[str | None] = mapped_column(Text, nullable=True)

    session: Mapped["Session"] = relationship(back_populates="feedback")


class Answer(Base):
    """Legacy: ответы на вопросы (для обратной совместимости)"""
    __tablename__ = "answers"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    session_id: Mapped[int] = mapped_column(ForeignKey("sessions.id"), index=True)
    step: Mapped[str] = mapped_column(String(32))
    text: Mapped[str] = mapped_column(Text)

    session: Mapped["Session"] = relationship(back_populates="answers")


# ============== Логирование и Админка ==============

class UserActivity(Base):
    """
    Лог активности пользователей для админки.
    Позволяет отслеживать кто что делает.
    """
    __tablename__ = "user_activities"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    chat_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("user_settings.chat_id"), index=True)
    session_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("sessions.id"), nullable=True, index=True)
    created_at: Mapped[dt.datetime] = mapped_column(DateTime, default=dt.datetime.utcnow, index=True)

    # Действие
    action: Mapped[str] = mapped_column(String(64), index=True)  # start|answer|finish|error|payment|etc
    action_type: Mapped[str] = mapped_column(String(32), default="user")  # user|system|billing|error

    # Детали
    details: Mapped[dict | None] = mapped_column(JSON, nullable=True)  # любые доп. данные
    message_text: Mapped[str | None] = mapped_column(Text, nullable=True)  # текст сообщения (если есть)

    # Метрики
    duration_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)  # длительность операции
    tokens_used: Mapped[int | None] = mapped_column(Integer, nullable=True)  # токены если LLM

    # IP/User-Agent для веб-админки
    ip_address: Mapped[str | None] = mapped_column(String(45), nullable=True)
    user_agent: Mapped[str | None] = mapped_column(String(256), nullable=True)

    user: Mapped["UserSettings"] = relationship(back_populates="activities")


class ErrorLog(Base):
    """Лог ошибок для мониторинга и отладки"""
    __tablename__ = "error_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    created_at: Mapped[dt.datetime] = mapped_column(DateTime, default=dt.datetime.utcnow, index=True)

    # Контекст
    chat_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True, index=True)
    session_id: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)

    # Ошибка
    error_type: Mapped[str] = mapped_column(String(128))  # тип исключения
    error_message: Mapped[str] = mapped_column(Text)  # сообщение
    error_traceback: Mapped[str | None] = mapped_column(Text, nullable=True)  # полный traceback

    # Где произошла
    module: Mapped[str | None] = mapped_column(String(128), nullable=True)
    function: Mapped[str | None] = mapped_column(String(128), nullable=True)

    # Статус обработки
    is_resolved: Mapped[bool] = mapped_column(Boolean, default=False)
    resolved_at: Mapped[dt.datetime | None] = mapped_column(DateTime, nullable=True)
    resolved_by: Mapped[str | None] = mapped_column(String(64), nullable=True)
    resolution_notes: Mapped[str | None] = mapped_column(Text, nullable=True)


# ============== Биллинг ==============

class BillingPlan(Base):
    """Тарифные планы"""
    __tablename__ = "billing_plans"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(32), unique=True)  # free|pro|premium
    display_name: Mapped[str] = mapped_column(String(64))  # "Free", "Pro", "Premium"

    # Лимиты
    interviews_per_month: Mapped[int] = mapped_column(Integer, default=3)  # 0 = unlimited
    max_tokens_per_interview: Mapped[int] = mapped_column(Integer, default=4000)

    # Цены
    price_per_month_usd: Mapped[float] = mapped_column(Float, default=0.0)  # подписка
    price_per_interview_usd: Mapped[float] = mapped_column(Float, default=0.0)  # за интервью
    price_per_1k_tokens_usd: Mapped[float] = mapped_column(Float, default=0.0)  # за токены

    # Фичи
    features: Mapped[dict | None] = mapped_column(JSON, nullable=True)  # {"detailed_feedback": true, ...}

    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[dt.datetime] = mapped_column(DateTime, default=dt.datetime.utcnow)


class Transaction(Base):
    """Транзакции пользователей (пополнения, списания)"""
    __tablename__ = "transactions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    chat_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("user_settings.chat_id"), index=True)
    created_at: Mapped[dt.datetime] = mapped_column(DateTime, default=dt.datetime.utcnow, index=True)

    # Тип транзакции
    tx_type: Mapped[str] = mapped_column(String(32))  # deposit|withdraw|refund|bonus
    amount_usd: Mapped[float] = mapped_column(Float)  # положительное = пополнение, отрицательное = списание

    # Связь с интервью (если списание за интервью)
    session_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("sessions.id"), nullable=True)

    # Детали
    description: Mapped[str | None] = mapped_column(String(256), nullable=True)
    tokens_charged: Mapped[int | None] = mapped_column(Integer, nullable=True)  # токены если списание

    # Платежная система
    payment_provider: Mapped[str | None] = mapped_column(String(32), nullable=True)  # stripe|liqpay|manual
    external_id: Mapped[str | None] = mapped_column(String(128), nullable=True)  # ID в платежной системе

    # Статус
    status: Mapped[str] = mapped_column(String(16), default="completed")  # pending|completed|failed|refunded

    # Баланс после транзакции
    balance_after: Mapped[float] = mapped_column(Float)

    user: Mapped["UserSettings"] = relationship(back_populates="transactions")


class PromoCode(Base):
    """Промокоды для скидок и бонусов"""
    __tablename__ = "promo_codes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    code: Mapped[str] = mapped_column(String(32), unique=True, index=True)  # WELCOME2024

    # Тип промокода
    promo_type: Mapped[str] = mapped_column(String(32))  # bonus_balance|free_interviews|discount_percent

    # Значение
    value: Mapped[float] = mapped_column(Float)  # $5 | 3 interviews | 20%

    # Лимиты
    max_uses: Mapped[int | None] = mapped_column(Integer, nullable=True)  # None = unlimited
    used_count: Mapped[int] = mapped_column(Integer, default=0)
    max_uses_per_user: Mapped[int] = mapped_column(Integer, default=1)

    # Срок действия
    valid_from: Mapped[dt.datetime] = mapped_column(DateTime, default=dt.datetime.utcnow)
    valid_until: Mapped[dt.datetime | None] = mapped_column(DateTime, nullable=True)

    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[dt.datetime] = mapped_column(DateTime, default=dt.datetime.utcnow)


class PromoCodeUsage(Base):
    """Использование промокодов"""
    __tablename__ = "promo_code_usages"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    promo_code_id: Mapped[int] = mapped_column(Integer, ForeignKey("promo_codes.id"), index=True)
    chat_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("user_settings.chat_id"), index=True)
    used_at: Mapped[dt.datetime] = mapped_column(DateTime, default=dt.datetime.utcnow)

    # Что получил пользователь
    benefit_type: Mapped[str] = mapped_column(String(32))  # bonus_balance|free_interviews|discount
    benefit_value: Mapped[float] = mapped_column(Float)
