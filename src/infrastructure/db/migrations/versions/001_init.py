"""Initial schema."""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "001_init"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("telegram_id", sa.Integer(), nullable=False),
        sa.Column("username", sa.String(length=255), nullable=True),
        sa.Column("first_name", sa.String(length=255), nullable=True),
        sa.Column("last_name", sa.String(length=255), nullable=True),
        sa.Column("language_code", sa.String(length=16), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.Column("last_seen_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("telegram_id"),
    )
    op.create_table(
        "cards",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("orig_name", sa.String(length=255), nullable=False),
        sa.Column("straight_position", sa.Text(), nullable=False),
        sa.Column("inverted_position", sa.Text(), nullable=False),
        sa.Column("source_checksum", sa.String(length=64), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "spread_types",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("code", sa.String(length=32), nullable=False),
        sa.Column("slot_count", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("code"),
    )
    op.create_table(
        "user_settings",
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("daily_card_broadcast", sa.Boolean(), nullable=False),
        sa.Column("allow_inverted", sa.Boolean(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("user_id"),
    )
    op.create_table(
        "spread_slots",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("spread_type_id", sa.Integer(), nullable=False),
        sa.Column("slot_index", sa.Integer(), nullable=False),
        sa.Column("code", sa.String(length=32), nullable=False),
        sa.ForeignKeyConstraint(["spread_type_id"], ["spread_types.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("spread_type_id", "slot_index"),
        sa.UniqueConstraint("spread_type_id", "code"),
    )
    op.create_table(
        "prompts",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("spread_type_id", sa.Integer(), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("system_template", sa.Text(), nullable=False),
        sa.Column("user_template", sa.Text(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.ForeignKeyConstraint(["spread_type_id"], ["spread_types.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_prompts_one_active",
        "prompts",
        ["spread_type_id"],
        unique=True,
        sqlite_where=sa.text("is_active = 1"),
    )
    op.create_table(
        "readings",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("spread_type_id", sa.Integer(), nullable=False),
        sa.Column("prompt_id", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("raw_llm_text", sa.Text(), nullable=True),
        sa.Column("raw_llm_text_repair", sa.Text(), nullable=True),
        sa.Column("interpretation", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["prompt_id"], ["prompts.id"]),
        sa.ForeignKeyConstraint(["spread_type_id"], ["spread_types.id"]),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "reading_slots",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("reading_id", sa.Integer(), nullable=False),
        sa.Column("spread_slot_id", sa.Integer(), nullable=False),
        sa.Column("card_id", sa.Integer(), nullable=False),
        sa.Column("is_inverted", sa.Boolean(), nullable=False),
        sa.ForeignKeyConstraint(["card_id"], ["cards.id"]),
        sa.ForeignKeyConstraint(["reading_id"], ["readings.id"]),
        sa.ForeignKeyConstraint(["spread_slot_id"], ["spread_slots.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("reading_id", "spread_slot_id"),
    )
    op.create_table(
        "daily_readings",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("card_date", sa.Date(), nullable=False),
        sa.Column("reading_id", sa.Integer(), nullable=False),
        sa.Column("delivery_status", sa.String(length=16), nullable=False),
        sa.Column("attempt_count", sa.Integer(), nullable=False),
        sa.Column("next_attempt_at", sa.DateTime(), nullable=True),
        sa.Column("last_error", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(["reading_id"], ["readings.id"]),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("reading_id"),
        sa.UniqueConstraint("user_id", "card_date"),
    )


def downgrade() -> None:
    op.drop_table("daily_readings")
    op.drop_table("reading_slots")
    op.drop_table("readings")
    op.drop_index("ix_prompts_one_active", table_name="prompts")
    op.drop_table("prompts")
    op.drop_table("spread_slots")
    op.drop_table("user_settings")
    op.drop_table("spread_types")
    op.drop_table("cards")
    op.drop_table("users")
