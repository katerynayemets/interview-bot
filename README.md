# Interview Trainer Bot — AI-powered interview practice via Telegram

## Overview

A Telegram bot that conducts structured mock interviews using LLM-generated questions and feedback. Users submit a CV and job vacancy, choose an interview type and difficulty level, and receive a multi-phase interview with real-time questions and a scored evaluation report at the end. Supports OpenAI and Anthropic as interchangeable LLM backends.

## Features

- **Multi-phase interview flow** — structured phases: intro → warmup → technical deep-dive → behavioral → candidate questions → closing
- **Three interview types** — HR/Soft Skills, Technical, Mixed
- **Four difficulty levels** — Junior, Middle, Senior, Lead
- **Two modes** — Training (free, 5 questions, cheaper model) and Real (15 questions, full model)
- **Document ingestion** — CV upload (PDF/DOCX) and vacancy via URL or pasted text
- **Web scraping** — auto-fetch job postings from DOU, Djinni, Work.ua, Robota.ua with Cloudflare detection
- **CV anonymization** — strips emails, phones, social handles, passport data before sending to LLM
- **Seniority detection** — infers candidate level from CV text; auto-adjusts difficulty
- **Pluggable LLM backend** — swap between OpenAI (GPT-4o) and Anthropic (Claude) via a single env variable
- **Comprehensive feedback** — per-dimension scores (technical, communication, problem-solving), strengths, improvement areas, study topics
- **Token and cost tracking** — all LLM calls logged with token counts and estimated USD cost
- **Structured logging** — JSON logs to file, colored console output, user activity and error tables in DB
- **Billing schema** — subscription tiers, pay-per-use balance, promo codes (infrastructure ready, not enforced)
- **Multilingual UI** — Ukrainian, Russian, English

## Architecture

```
┌─────────────────────────────────────┐
│  Telegram  ◄──►  FastAPI + aiogram  │  HTTP webhook or long-polling
│                  app/main.py        │
│                  app/routers/       │
└────────────┬────────────────────────┘
             │ async DB calls
┌────────────▼────────────────────────┐
│  PostgreSQL  (SQLAlchemy async)     │  sessions, messages, feedback,
│  app/db/models.py, crud.py          │  billing, activity logs
└────────────┬────────────────────────┘
             │
┌────────────▼────────────────────────┐
│  Redis + Celery workers             │  vacancy fetch, LLM tasks
│  app/worker/                        │  (prefork, one event loop/worker)
└────────────┬────────────────────────┘
             │
┌────────────▼────────────────────────┐
│  LLM clients  (app/llm/)            │  OpenAI Chat Completions API
│  Abstract base + provider impls     │  Anthropic Messages API
└─────────────────────────────────────┘
```

The bot runs in two modes controlled by `BOT_MODE`:
- `polling` — local development, no public URL needed
- `webhook` — production, requires `PUBLIC_URL` pointing to the FastAPI server

## Tech Stack

| Layer | Technology |
|---|---|
| Bot framework | aiogram 3.x |
| Web server | FastAPI + Uvicorn |
| Database | PostgreSQL 16, SQLAlchemy 2 (async), asyncpg |
| Migrations | Alembic |
| Task queue | Celery 5 + Redis 7 |
| LLM | OpenAI API, Anthropic API (via httpx) |
| Document parsing | pypdf, python-docx |
| Web scraping | httpx, BeautifulSoup4, readability-lxml |
| Config | pydantic-settings |
| Logging | stdlib logging with JSON formatter |
| Containers | Docker + docker-compose |

## Project Structure

```
interview-bot/
├── app/
│   ├── main.py              # FastAPI app, startup/shutdown, webhook endpoint
│   ├── bot.py               # Bot and dispatcher factory
│   ├── config.py            # Settings (pydantic-settings, reads .env)
│   ├── states.py            # aiogram FSM states
│   ├── middleware.py        # Logging, throttling, billing middlewares
│   ├── i18n.py              # UI translations: UK / RU / EN
│   ├── logging_config.py    # JSON + console log formatters, BotLogger
│   ├── db/
│   │   ├── models.py        # SQLAlchemy ORM models
│   │   ├── crud.py          # All database operations
│   │   ├── session.py       # AsyncSession engine
│   │   └── base.py          # DeclarativeBase
│   ├── llm/
│   │   ├── client.py        # Abstract LLMClient + OpenAI/Anthropic impls + factory
│   │   ├── prompts.py       # Prompt templates and PromptManager
│   │   └── context.py       # ContextBuilder — assembles session data for LLM
│   ├── routers/
│   │   ├── start.py         # Setup wizard: track → language → mode → type → difficulty → docs
│   │   ├── interview.py     # Live interview loop, feedback generation, rating
│   │   └── menu.py          # /help, /settings, /language, /mode, /cancel
│   └── worker/
│       ├── celery_app.py    # Celery configuration
│       ├── tasks.py         # fetch_vacancy, generate_snapshot tasks
│       ├── llm_tasks.py     # generate_question, evaluate_answer, generate_feedback tasks
│       ├── pdf_reader.py    # PDF text extraction (pypdf)
│       ├── docx_reader.py   # DOCX text extraction (python-docx)
│       ├── text_processing.py  # Anonymization, token estimation, seniority detection
│       ├── vacancy_fetch.py    # Job board scraper (DOU / Djinni / Work.ua / Robota.ua)
│       └── telegram_api.py  # HTTP helper for sending messages from Celery workers
├── alembic/
│   ├── env.py
│   └── versions/            # 5 migration files
├── Dockerfile
├── docker-compose.yml
├── requirements.txt
└── .env.example
```

## Setup & Run

**Prerequisites:** Docker and docker-compose.

```bash
cp .env.example .env
# Fill in BOT_TOKEN and at least one of OPENAI_API_KEY / ANTHROPIC_API_KEY
docker-compose up --build
```

The API will be available at `http://localhost:8000`. In `polling` mode (default) the bot starts automatically. Switch to `webhook` mode by setting `BOT_MODE=webhook` and `PUBLIC_URL` to your HTTPS endpoint.

**Run migrations manually (if needed):**
```bash
docker-compose exec api alembic upgrade head
```

### Environment variables

See [.env.example](.env.example) for the full list. Key variables:

| Variable | Description |
|---|---|
| `BOT_TOKEN` | Telegram bot token from @BotFather |
| `BOT_MODE` | `polling` (local) or `webhook` (production) |
| `PUBLIC_URL` | Public HTTPS base URL (webhook mode only) |
| `LLM_PROVIDER` | `openai` or `anthropic` |
| `OPENAI_API_KEY` | Required if `LLM_PROVIDER=openai` |
| `ANTHROPIC_API_KEY` | Required if `LLM_PROVIDER=anthropic` |
| `DATABASE_URL` | PostgreSQL async URL (`postgresql+asyncpg://...`) |
| `REDIS_URL` | Redis URL for FSM state storage |
| `CELERY_BROKER_URL` | Redis URL for Celery broker |

## Key Design Decisions

**Abstract LLM client with a factory.** `LLMClient` is an ABC with `OpenAIClient` and `AnthropicClient` implementations. The active provider is selected at runtime via `LLM_PROVIDER`. This means prompts, context assembly, and cost tracking are provider-agnostic — switching backends requires only an env variable change.

**Phase-based interview flow.** Each session has a sequence of `InterviewPhase` rows created upfront based on `interview_type`. The current phase drives prompt selection and question limits. Phases can be completed independently, which makes the flow extensible without touching router logic.

**Async-safe Celery workers.** The codebase uses an async SQLAlchemy engine throughout. Celery workers run with prefork concurrency, where multiple processes share no event loop. Each worker process maintains a single `asyncio` event loop (`run_coro` in `tasks.py`) to safely reuse the async engine and connection pool across task invocations.
