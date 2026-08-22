"""Database models (3NF)."""

from __future__ import annotations

from datetime import date, datetime

from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.infrastructure.db.base import Base


def utc_now() -> datetime:
    return datetime.utcnow()


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    telegram_id: Mapped[int] = mapped_column(Integer, unique=True, nullable=False)
    username: Mapped[str | None] = mapped_column(String(255), nullable=True)
    first_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    last_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    language_code: Mapped[str | None] = mapped_column(String(16), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=utc_now, onupdate=utc_now
    )
    last_seen_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now)

    settings: Mapped[UserSettings] = relationship(back_populates="user", uselist=False)


class UserSettings(Base):
    __tablename__ = "user_settings"

    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), primary_key=True)
    daily_card_broadcast: Mapped[bool] = mapped_column(Boolean, default=False)
    allow_inverted: Mapped[bool] = mapped_column(Boolean, default=True)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=utc_now, onupdate=utc_now
    )

    user: Mapped[User] = relationship(back_populates="settings")


class Card(Base):
    __tablename__ = "cards"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    orig_name: Mapped[str] = mapped_column(String(255), nullable=False)
    straight_position: Mapped[str] = mapped_column(Text, nullable=False)
    inverted_position: Mapped[str] = mapped_column(Text, nullable=False)
    source_checksum: Mapped[str] = mapped_column(String(64), nullable=False)


class SpreadType(Base):
    __tablename__ = "spread_types"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    code: Mapped[str] = mapped_column(String(32), unique=True, nullable=False)
    slot_count: Mapped[int] = mapped_column(Integer, nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)

    slots: Mapped[list[SpreadSlot]] = relationship(back_populates="spread_type")
    prompts: Mapped[list[Prompt]] = relationship(back_populates="spread_type")


class SpreadSlot(Base):
    __tablename__ = "spread_slots"
    __table_args__ = (
        UniqueConstraint("spread_type_id", "slot_index"),
        UniqueConstraint("spread_type_id", "code"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    spread_type_id: Mapped[int] = mapped_column(
        ForeignKey("spread_types.id"), nullable=False
    )
    slot_index: Mapped[int] = mapped_column(Integer, nullable=False)
    code: Mapped[str] = mapped_column(String(32), nullable=False)

    spread_type: Mapped[SpreadType] = relationship(back_populates="slots")


class Prompt(Base):
    __tablename__ = "prompts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    spread_type_id: Mapped[int] = mapped_column(
        ForeignKey("spread_types.id"), nullable=False
    )
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    system_template: Mapped[str] = mapped_column(Text, nullable=False)
    user_template: Mapped[str] = mapped_column(Text, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    spread_type: Mapped[SpreadType] = relationship(back_populates="prompts")


class Reading(Base):
    __tablename__ = "readings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    spread_type_id: Mapped[int] = mapped_column(
        ForeignKey("spread_types.id"), nullable=False
    )
    prompt_id: Mapped[int] = mapped_column(ForeignKey("prompts.id"), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="pending")
    raw_llm_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    raw_llm_text_repair: Mapped[str | None] = mapped_column(Text, nullable=True)
    interpretation: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=utc_now, onupdate=utc_now
    )

    slots: Mapped[list[ReadingSlot]] = relationship(back_populates="reading")


class ReadingSlot(Base):
    __tablename__ = "reading_slots"
    __table_args__ = (UniqueConstraint("reading_id", "spread_slot_id"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    reading_id: Mapped[int] = mapped_column(ForeignKey("readings.id"), nullable=False)
    spread_slot_id: Mapped[int] = mapped_column(
        ForeignKey("spread_slots.id"), nullable=False
    )
    card_id: Mapped[int] = mapped_column(ForeignKey("cards.id"), nullable=False)
    is_inverted: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    reading: Mapped[Reading] = relationship(back_populates="slots")


class DailyReading(Base):
    __tablename__ = "daily_readings"
    __table_args__ = (UniqueConstraint("user_id", "card_date"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    card_date: Mapped[date] = mapped_column(Date, nullable=False)
    reading_id: Mapped[int] = mapped_column(
        ForeignKey("readings.id"), unique=True, nullable=False
    )
    delivery_status: Mapped[str] = mapped_column(String(16), default="none")
    attempt_count: Mapped[int] = mapped_column(Integer, default=0)
    next_attempt_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    last_error: Mapped[str | None] = mapped_column(Text, nullable=True)
