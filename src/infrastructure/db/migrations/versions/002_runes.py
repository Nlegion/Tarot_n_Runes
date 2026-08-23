"""Rune tables (shared users, separate settings and readings)."""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "002_runes"
down_revision: str | None = "001_init"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "rune_user_settings",
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("daily_rune_broadcast", sa.Boolean(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("user_id"),
    )
    op.create_table(
        "runes",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("orig_name", sa.String(length=255), nullable=False),
        sa.Column("unicode", sa.String(length=8), nullable=True),
        sa.Column("straight_position", sa.Text(), nullable=False),
        sa.Column("inverted_position", sa.Text(), nullable=False),
        sa.Column("can_invert", sa.Boolean(), nullable=False),
        sa.Column("source_checksum", sa.String(length=64), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "rune_spread_types",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("code", sa.String(length=32), nullable=False),
        sa.Column("slot_count", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("code"),
    )
    op.create_table(
        "rune_spread_slots",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("spread_type_id", sa.Integer(), nullable=False),
        sa.Column("slot_index", sa.Integer(), nullable=False),
        sa.Column("code", sa.String(length=32), nullable=False),
        sa.ForeignKeyConstraint(["spread_type_id"], ["rune_spread_types.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("spread_type_id", "slot_index"),
        sa.UniqueConstraint("spread_type_id", "code"),
    )
    op.create_table(
        "rune_prompts",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("spread_type_id", sa.Integer(), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("system_template", sa.Text(), nullable=False),
        sa.Column("user_template", sa.Text(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.ForeignKeyConstraint(["spread_type_id"], ["rune_spread_types.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_rune_prompts_one_active",
        "rune_prompts",
        ["spread_type_id"],
        unique=True,
        sqlite_where=sa.text("is_active = 1"),
    )
    op.create_table(
        "rune_readings",
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
        sa.ForeignKeyConstraint(["prompt_id"], ["rune_prompts.id"]),
        sa.ForeignKeyConstraint(["spread_type_id"], ["rune_spread_types.id"]),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "rune_reading_slots",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("reading_id", sa.Integer(), nullable=False),
        sa.Column("spread_slot_id", sa.Integer(), nullable=False),
        sa.Column("rune_id", sa.Integer(), nullable=False),
        sa.Column("is_inverted", sa.Boolean(), nullable=False),
        sa.ForeignKeyConstraint(["reading_id"], ["rune_readings.id"]),
        sa.ForeignKeyConstraint(["rune_id"], ["runes.id"]),
        sa.ForeignKeyConstraint(["spread_slot_id"], ["rune_spread_slots.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("reading_id", "spread_slot_id"),
    )
    op.create_table(
        "rune_daily_readings",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("rune_date", sa.Date(), nullable=False),
        sa.Column("reading_id", sa.Integer(), nullable=False),
        sa.Column("delivery_status", sa.String(length=16), nullable=False),
        sa.Column("attempt_count", sa.Integer(), nullable=False),
        sa.Column("next_attempt_at", sa.DateTime(), nullable=True),
        sa.Column("last_error", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(["reading_id"], ["rune_readings.id"]),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("reading_id"),
        sa.UniqueConstraint("user_id", "rune_date"),
    )


def downgrade() -> None:
    op.drop_table("rune_daily_readings")
    op.drop_table("rune_reading_slots")
    op.drop_table("rune_readings")
    op.drop_index("ix_rune_prompts_one_active", table_name="rune_prompts")
    op.drop_table("rune_prompts")
    op.drop_table("rune_spread_slots")
    op.drop_table("rune_spread_types")
    op.drop_table("runes")
    op.drop_table("rune_user_settings")
