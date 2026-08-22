"""Apply Alembic migrations."""

from __future__ import annotations

from alembic import command
from alembic.config import Config

from src.core.settings.config import PROJECT_ROOT, Settings


def apply_migrations() -> None:
    ini_path = PROJECT_ROOT / "alembic.ini"
    cfg = Config(str(ini_path))
    cfg.set_main_option("sqlalchemy.url", Settings.db_url())
    cfg.set_main_option(
        "script_location", str(PROJECT_ROOT / "src/infrastructure/db/migrations")
    )
    command.upgrade(cfg, "head")
