from datetime import datetime
from typing import Optional
from sqlalchemy import Boolean, DateTime, Float, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column
from app.database import Base


class Message(Base):
    __tablename__ = "messages"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    gmail_id: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    thread_id: Mapped[str] = mapped_column(String(64), index=True)
    history_id: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    sender_name: Mapped[str] = mapped_column(String(500), default="")
    sender_email: Mapped[str] = mapped_column(String(500), default="", index=True)
    sender_domain: Mapped[str] = mapped_column(String(255), default="", index=True)
    to_emails: Mapped[str] = mapped_column(Text, default="")
    subject: Mapped[str] = mapped_column(Text, default="")
    snippet: Mapped[str] = mapped_column(Text, default="")
    body_text: Mapped[str] = mapped_column(Text, default="")
    received_at: Mapped[datetime] = mapped_column(DateTime, index=True)
    internal_date_ms: Mapped[int] = mapped_column(Integer, default=0)
    labels_json: Mapped[str] = mapped_column(Text, default="[]")
    list_unsubscribe: Mapped[str] = mapped_column(Text, default="")
    list_id: Mapped[str] = mapped_column(Text, default="")
    is_read: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    is_starred: Mapped[bool] = mapped_column(Boolean, default=False)
    is_important: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    is_sent: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    is_inbox: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    has_attachment: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class Classification(Base):
    __tablename__ = "classifications"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    message_id: Mapped[int] = mapped_column(Integer, unique=True, index=True)
    category: Mapped[str] = mapped_column(String(64), default="UNKNOWN", index=True)
    importance: Mapped[float] = mapped_column(Float, default=0.5, index=True)
    usefulness: Mapped[float] = mapped_column(Float, default=0.5, index=True)
    confidence: Mapped[float] = mapped_column(Float, default=0.5)
    action_required: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    urgency: Mapped[str] = mapped_column(String(32), default="LOW")
    summary: Mapped[str] = mapped_column(Text, default="")
    reason: Mapped[str] = mapped_column(Text, default="")
    source: Mapped[str] = mapped_column(String(32), default="heuristic")
    model_used: Mapped[str] = mapped_column(String(255), default="")
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class MessageEvent(Base):
    __tablename__ = "message_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    gmail_id: Mapped[str] = mapped_column(String(64), index=True)
    event_type: Mapped[str] = mapped_column(String(64), index=True)
    observed_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)


class Feedback(Base):
    __tablename__ = "feedback"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    message_id: Mapped[int] = mapped_column(Integer, index=True)
    useful: Mapped[Optional[bool]] = mapped_column(Boolean, nullable=True)
    category_override: Mapped[str] = mapped_column(String(64), default="")
    note: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class SenderPreference(Base):
    __tablename__ = "sender_preferences"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    sender_email: Mapped[str] = mapped_column(String(500), unique=True, index=True)
    preference: Mapped[float] = mapped_column(Float, default=0.0)
    note: Mapped[str] = mapped_column(Text, default="")
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class ReviewLater(Base):
    __tablename__ = "review_later"
    __table_args__ = (UniqueConstraint("message_id", name="uq_review_message"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    message_id: Mapped[int] = mapped_column(Integer, index=True)
    priority: Mapped[str] = mapped_column(String(32), default="NORMAL")
    reason: Mapped[str] = mapped_column(Text, default="")
    added_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)


class SyncState(Base):
    __tablename__ = "sync_state"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    account_email: Mapped[str] = mapped_column(String(500), unique=True)
    history_id: Mapped[str] = mapped_column(String(64), default="")
    sync_days: Mapped[int] = mapped_column(Integer, default=90)
    include_sent: Mapped[bool] = mapped_column(Boolean, default=True)
    last_full_sync: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    last_incremental_sync: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)


class EmailEmbedding(Base):
    __tablename__ = "email_embeddings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    message_id: Mapped[int] = mapped_column(Integer, unique=True, index=True)
    model: Mapped[str] = mapped_column(String(255), default="")
    vector_json: Mapped[str] = mapped_column(Text)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
