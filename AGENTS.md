# Tarot Bot — Agent Guide

Telegram bot for tarot readings with DeepSeek interpretation. Live bot: [@NordTarotBot](https://t.me/NordTarotBot).

## Tech Stack

| Layer | Technology |
|-------|------------|
| Language | Python 3.11+ (asyncio) |
| Entry | `src/main.py` |
| LLM | DeepSeek API (`httpx` / `aiohttp`) |
| Database | SQLite async (`sqlalchemy` + `aiosqlite`) |
| Migrations | Alembic |
| Telegram | Raw Bot API via `httpx` (no aiogram) |
| Imaging | Pillow |
| Logging | stdlib `logging` + `structlog` |
| Tests | pytest + pytest-asyncio |
| Quality | ruff, bandit, vulture |

## Project Structure

```
tarot/
├── src/
│   ├── main.py                 # composition root
│   ├── core/settings/          # config, constants, logging
│   ├── domain/                 # draw engine, card text, entities
│   ├── application/            # use cases + ports
│   ├── infrastructure/         # db, llm, telegram, imaging, scheduler
│   └── presentation/           # poller, handlers, keyboards
├── tests/                      # mirrors src/
├── scripts/quality/
├── images/tarot/               # tarot card JPGs 0-77
├── fonts/                      # Noto Sans Runic for rune ovals
├── tarot_cards.csv
├── runes.csv
├── alembic.ini
└── .env
```

## Key Commands

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
pip install -r requirements-dev.txt

alembic upgrade head
python src/main.py

pytest tests -q
python scripts/quality/run_gates.py
```

## Coding Conventions

- Clean layered architecture; application depends only on domain + ports.
- Keyword arguments for 3+ parameter calls.
- Files ≤200 lines when avoidable.
- Structured logging; no bare `except:` or silent `pass`.
- Secrets only in `.env`; never commit `.env` or `*.db`.
- Shared `users` table for tarot and runes bots; per-bot settings and rune tables are separate.
- Rune images are generated in memory from Unicode + font; do not write composites to disk.
