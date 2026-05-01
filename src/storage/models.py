"""Operational baseline storage models."""
from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlalchemy import JSON, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    """Base model class for all DB entities."""


class RawItem(Base):
    __tablename__ = "raw_items"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    source_name: Mapped[str] = mapped_column(String(120), index=True)
    source_url: Mapped[str] = mapped_column(String(1024), index=True)
    collected_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)
    payload: Mapped[dict] = mapped_column(JSON)
    content_hash: Mapped[str] = mapped_column(String(128), unique=True, index=True)


class CanonicalEvent(Base):
    __tablename__ = "canonical_events"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    event_key: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    title: Mapped[str] = mapped_column(String(512))
    summary: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    normalized_payload: Mapped[dict] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    scores: Mapped[list["Score"]] = relationship(back_populates="event", cascade="all, delete-orphan")
    alerts: Mapped[list["Alert"]] = relationship(back_populates="event", cascade="all, delete-orphan")


class Score(Base):
    __tablename__ = "scores"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    event_id: Mapped[int] = mapped_column(ForeignKey("canonical_events.id", ondelete="CASCADE"), index=True)
    model_name: Mapped[str] = mapped_column(String(128))
    score: Mapped[float] = mapped_column(Float)
    explanation: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    event: Mapped[CanonicalEvent] = relationship(back_populates="scores")


class Alert(Base):
    __tablename__ = "alerts"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    event_id: Mapped[int] = mapped_column(ForeignKey("canonical_events.id", ondelete="CASCADE"), index=True)
    channel: Mapped[str] = mapped_column(String(64), index=True)
    recipient: Mapped[str] = mapped_column(String(255))
    status: Mapped[str] = mapped_column(String(32), index=True)
    sent_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    metadata: Mapped[dict] = mapped_column(JSON, default=dict)

    event: Mapped[CanonicalEvent] = relationship(back_populates="alerts")


class SourceHealth(Base):
    __tablename__ = "source_health"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    source_name: Mapped[str] = mapped_column(String(120), unique=True, index=True)
    status: Mapped[str] = mapped_column(String(32), index=True)
    latency_ms: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    error_count: Mapped[int] = mapped_column(Integer, default=0)
    last_checked_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    details: Mapped[dict] = mapped_column(JSON, default=dict)
