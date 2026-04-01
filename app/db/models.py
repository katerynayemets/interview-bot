import datetime as dt
from sqlalchemy import String, Text, DateTime, Integer, Float, ForeignKey, JSON, Boolean, BigInteger
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base


class UserSettings(Base):
    """Persistent user settings and billing state."""
    __tablename__ = "user_settings"

    chat_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    username: Mapped[str | None] = mapped_column(String(64), nullable=True)
    first_name: Mapped[str | None] = mapped_column(String(64), nullable=True)
    last_name: Mapped[str | None] = mapped_column(String(64), nullable=True)

    language: Mapped[str] = mapped_column(String(8), default="uk")
    track: Mapped[str] = mapped_column(String(32), default="data")
    mode: Mapped[str] = mapped_column(String(32), default="training")  # training|real

    interview_type: Mapped[str] = mapped_column(String(32), default="mixed")  # hr_soft|technical_hard|mixed
    difficulty: Mapped[str] = mapped_column(String(16), default="middle")  # junior|middle|senior|lead

    subscription_tier: Mapped[str] = mapped_column(String(16), default="free")  # free|pro|premium
    balance_usd: Mapped[float] = mapped_column(Float, default=0.0)
    free_interviews_left: Mapped[int] = mapped_column(Integer, default=3)
    total_interviews: Mapped[int] = mapped_column(Integer, default=0)
    total_tokens_used: Mapped[int] = mapped_column(Integer, default=0)
    total_spent_usd: Mapped[float] = mapped_column(Float, default=0.0)

    is_blocked: Mapped[bool] = mapped_column(Boolean, default=False)
    is_admin: Mapped[bool] = mapped_column(Boolean, default=False)

    created_at: Mapped[dt.datetime] = mapped_column(DateTime, default=dt.datetime.utcnow)
    updated_at: Mapped[dt.datetime] = mapped_column(DateTime, default=dt.datetime.utcnow, onupdate=dt.datetime.utcnow)

    activities: Mapped[list["UserActivity"]] = relationship(back_populates="user", cascade="all, delete-orphan")
    transactions: Mapped[list["Transaction"]] = relationship(back_populates="user", cascade="all, delete-orphan")


class Session(Base):
    """Interview session with a snapshot of settings at creation time."""
    __tablename__ = "sessions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    chat_id: Mapped[int] = mapped_column(Integer, index=True)
    created_at: Mapped[dt.datetime] = mapped_column(DateTime, default=dt.datetime.utcnow)
    updated_at: Mapped[dt.datetime] = mapped_column(DateTime, default=dt.datetime.utcnow, onupdate=dt.datetime.utcnow)

    language: Mapped[str] = mapped_column(String(8), default="uk")
    track: Mapped[str] = mapped_column(String(32), default="data")
    mode: Mapped[str] = mapped_column(String(32), default="training")  # training|real
    interview_type: Mapped[str] = mapped_column(String(32), default="mixed")  # hr_soft|technical_hard|mixed
    difficulty: Mapped[str] = mapped_column(String(16), default="middle")  # junior|middle|senior|lead

    vacancy_status: Mapped[str] = mapped_column(String(16), default="empty")  # empty|skipped|pending|ok|failed
    vacancy_error: Mapped[str | None] = mapped_column(String(512), nullable=True)
    cv_status: Mapped[str] = mapped_column(String(16), default="empty")  # empty|skipped|pending|ok|failed
    cv_error: Mapped[str | None] = mapped_column(String(512), nullable=True)

    vacancy_summary: Mapped[str | None] = mapped_column(String(512), nullable=True)
    cv_summary: Mapped[str | None] = mapped_column(String(512), nullable=True)

    # Legacy fields
    vacancy_url: Mapped[str | None] = mapped_column(String(512), nullable=True)
    vacancy_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    cv_text: Mapped[str | None] = mapped_column(Text, nullable=True)

    stage: Mapped[str] = mapped_column(String(32), default="collecting")  # collecting|interview|generating_feedback|done

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
    answers: Mapped[list["Answer"]] = relationship(back_populates="session", cascade="all, delete-orphan")


class SessionDocument(Base):
    """CV and vacancy documents stored separately from the session row."""
    __tablename__ = "session_documents"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    session_id: Mapped[int] = mapped_column(ForeignKey("sessions.id"), index=True)
    created_at: Mapped[dt.datetime] = mapped_column(DateTime, default=dt.datetime.utcnow)

    doc_type: Mapped[str] = mapped_column(String(16))  # cv|vacancy
    source_url: Mapped[str | None] = mapped_column(String(512), nullable=True)
    raw_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    processed_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    token_count: Mapped[int] = mapped_column(Integer, default=0)

    session: Mapped["Session"] = relationship(back_populates="documents")


class InterviewPhase(Base):
    """Structured phase within an interview session."""
    __tablename__ = "interview_phases"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    session_id: Mapped[int] = mapped_column(ForeignKey("sessions.id"), index=True)

    phase_type: Mapped[str] = mapped_column(String(32))  # intro|warmup|technical_deep|behavioral|questions_to_company|closing
    phase_order: Mapped[int] = mapped_column(Integer)
    status: Mapped[str] = mapped_column(String(16), default="pending")  # pending|active|completed|skipped

    started_at: Mapped[dt.datetime | None] = mapped_column(DateTime, nullable=True)
    completed_at: Mapped[dt.datetime | None] = mapped_column(DateTime, nullable=True)

    phase_config: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    session: Mapped["Session"] = relationship(back_populates="phases")


class Message(Base):
    """Dialogue message with LLM usage tracking."""
    __tablename__ = "messages"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    session_id: Mapped[int] = mapped_column(ForeignKey("sessions.id"), index=True)
    phase_id: Mapped[int | None] = mapped_column(ForeignKey("interview_phases.id"), nullable=True, index=True)
    created_at: Mapped[dt.datetime] = mapped_column(DateTime, default=dt.datetime.utcnow)

    role: Mapped[str] = mapped_column(String(16))  # user|assistant|system
    kind: Mapped[str] = mapped_column(String(16), default="message")  # question|answer|feedback|event|message
    text: Mapped[str] = mapped_column(Text)

    model_used: Mapped[str | None] = mapped_column(String(64), nullable=True)
    tokens_input: Mapped[int] = mapped_column(Integer, default=0)
    tokens_output: Mapped[int] = mapped_column(Integer, default=0)
    latency_ms: Mapped[int] = mapped_column(Integer, default=0)

    session: Mapped["Session"] = relationship(back_populates="messages")


class SessionStats(Base):
    """Aggregated statistics for an interview session."""
    __tablename__ = "session_stats"

    session_id: Mapped[int] = mapped_column(ForeignKey("sessions.id"), primary_key=True)

    total_tokens_input: Mapped[int] = mapped_column(Integer, default=0)
    total_tokens_output: Mapped[int] = mapped_column(Integer, default=0)
    total_messages: Mapped[int] = mapped_column(Integer, default=0)
    estimated_cost_usd: Mapped[float] = mapped_column(Float, default=0.0)

    interview_duration_sec: Mapped[int] = mapped_column(Integer, default=0)

    updated_at: Mapped[dt.datetime] = mapped_column(DateTime, default=dt.datetime.utcnow, onupdate=dt.datetime.utcnow)

    session: Mapped["Session"] = relationship(back_populates="stats")


class InterviewFeedback(Base):
    """LLM-generated feedback and user rating for a completed session."""
    __tablename__ = "interview_feedback"

    session_id: Mapped[int] = mapped_column(ForeignKey("sessions.id"), primary_key=True)
    created_at: Mapped[dt.datetime] = mapped_column(DateTime, default=dt.datetime.utcnow)

    technical_score: Mapped[int | None] = mapped_column(Integer, nullable=True)
    communication_score: Mapped[int | None] = mapped_column(Integer, nullable=True)
    problem_solving_score: Mapped[int | None] = mapped_column(Integer, nullable=True)
    overall_score: Mapped[int | None] = mapped_column(Integer, nullable=True)

    strengths: Mapped[list | None] = mapped_column(JSON, nullable=True)
    improvements: Mapped[list | None] = mapped_column(JSON, nullable=True)
    detailed_feedback: Mapped[str | None] = mapped_column(Text, nullable=True)

    recommended_topics: Mapped[list | None] = mapped_column(JSON, nullable=True)

    user_rating: Mapped[int | None] = mapped_column(Integer, nullable=True)  # 1-5
    user_comment: Mapped[str | None] = mapped_column(Text, nullable=True)

    session: Mapped["Session"] = relationship(back_populates="feedback")


class Answer(Base):
    """Legacy answer records for backwards compatibility."""
    __tablename__ = "answers"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    session_id: Mapped[int] = mapped_column(ForeignKey("sessions.id"), index=True)
    step: Mapped[str] = mapped_column(String(32))
    text: Mapped[str] = mapped_column(Text)

    session: Mapped["Session"] = relationship(back_populates="answers")


class UserActivity(Base):
    """User action log for admin monitoring."""
    __tablename__ = "user_activities"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    chat_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("user_settings.chat_id"), index=True)
    session_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("sessions.id"), nullable=True, index=True)
    created_at: Mapped[dt.datetime] = mapped_column(DateTime, default=dt.datetime.utcnow, index=True)

    action: Mapped[str] = mapped_column(String(64), index=True)
    action_type: Mapped[str] = mapped_column(String(32), default="user")  # user|system|billing|error

    details: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    message_text: Mapped[str | None] = mapped_column(Text, nullable=True)

    duration_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    tokens_used: Mapped[int | None] = mapped_column(Integer, nullable=True)

    ip_address: Mapped[str | None] = mapped_column(String(45), nullable=True)
    user_agent: Mapped[str | None] = mapped_column(String(256), nullable=True)

    user: Mapped["UserSettings"] = relationship(back_populates="activities")


class ErrorLog(Base):
    """Exception log for monitoring and debugging."""
    __tablename__ = "error_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    created_at: Mapped[dt.datetime] = mapped_column(DateTime, default=dt.datetime.utcnow, index=True)

    chat_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True, index=True)
    session_id: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)

    error_type: Mapped[str] = mapped_column(String(128))
    error_message: Mapped[str] = mapped_column(Text)
    error_traceback: Mapped[str | None] = mapped_column(Text, nullable=True)

    module: Mapped[str | None] = mapped_column(String(128), nullable=True)
    function: Mapped[str | None] = mapped_column(String(128), nullable=True)

    is_resolved: Mapped[bool] = mapped_column(Boolean, default=False)
    resolved_at: Mapped[dt.datetime | None] = mapped_column(DateTime, nullable=True)
    resolved_by: Mapped[str | None] = mapped_column(String(64), nullable=True)
    resolution_notes: Mapped[str | None] = mapped_column(Text, nullable=True)


class BillingPlan(Base):
    """Subscription and pay-per-use billing plan definition."""
    __tablename__ = "billing_plans"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(32), unique=True)  # free|pro|premium
    display_name: Mapped[str] = mapped_column(String(64))

    interviews_per_month: Mapped[int] = mapped_column(Integer, default=3)  # 0 = unlimited
    max_tokens_per_interview: Mapped[int] = mapped_column(Integer, default=4000)

    price_per_month_usd: Mapped[float] = mapped_column(Float, default=0.0)
    price_per_interview_usd: Mapped[float] = mapped_column(Float, default=0.0)
    price_per_1k_tokens_usd: Mapped[float] = mapped_column(Float, default=0.0)

    features: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[dt.datetime] = mapped_column(DateTime, default=dt.datetime.utcnow)


class Transaction(Base):
    """User billing transaction (deposit, withdrawal, refund, or bonus)."""
    __tablename__ = "transactions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    chat_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("user_settings.chat_id"), index=True)
    created_at: Mapped[dt.datetime] = mapped_column(DateTime, default=dt.datetime.utcnow, index=True)

    tx_type: Mapped[str] = mapped_column(String(32))  # deposit|withdraw|refund|bonus
    amount_usd: Mapped[float] = mapped_column(Float)

    session_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("sessions.id"), nullable=True)

    description: Mapped[str | None] = mapped_column(String(256), nullable=True)
    tokens_charged: Mapped[int | None] = mapped_column(Integer, nullable=True)

    payment_provider: Mapped[str | None] = mapped_column(String(32), nullable=True)  # stripe|liqpay|manual
    external_id: Mapped[str | None] = mapped_column(String(128), nullable=True)

    status: Mapped[str] = mapped_column(String(16), default="completed")  # pending|completed|failed|refunded

    balance_after: Mapped[float] = mapped_column(Float)

    user: Mapped["UserSettings"] = relationship(back_populates="transactions")


class PromoCode(Base):
    """Promo code for discounts and bonuses."""
    __tablename__ = "promo_codes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    code: Mapped[str] = mapped_column(String(32), unique=True, index=True)

    promo_type: Mapped[str] = mapped_column(String(32))  # bonus_balance|free_interviews|discount_percent
    value: Mapped[float] = mapped_column(Float)

    max_uses: Mapped[int | None] = mapped_column(Integer, nullable=True)  # None = unlimited
    used_count: Mapped[int] = mapped_column(Integer, default=0)
    max_uses_per_user: Mapped[int] = mapped_column(Integer, default=1)

    valid_from: Mapped[dt.datetime] = mapped_column(DateTime, default=dt.datetime.utcnow)
    valid_until: Mapped[dt.datetime | None] = mapped_column(DateTime, nullable=True)

    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[dt.datetime] = mapped_column(DateTime, default=dt.datetime.utcnow)


class PromoCodeUsage(Base):
    """Record of a promo code activation by a user."""
    __tablename__ = "promo_code_usages"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    promo_code_id: Mapped[int] = mapped_column(Integer, ForeignKey("promo_codes.id"), index=True)
    chat_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("user_settings.chat_id"), index=True)
    used_at: Mapped[dt.datetime] = mapped_column(DateTime, default=dt.datetime.utcnow)

    benefit_type: Mapped[str] = mapped_column(String(32))  # bonus_balance|free_interviews|discount
    benefit_value: Mapped[float] = mapped_column(Float)
