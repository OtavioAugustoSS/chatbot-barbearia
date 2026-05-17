# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

WhatsApp chatbot for **Barbearia Bolshoi** (Unaí, MG, Brazil). Built on FastAPI + MySQL, uses the NVIDIA NIM API (Llama 3.1 70B via OpenAI-compatible client) to process messages received from the Meta WhatsApp Cloud API.

## Commands

```bash
# Install dependencies (use the project's virtual environment)
pip install -r requirements.txt

# Run the server (auto-reload enabled)
python main.py

# Expose locally via ngrok for Meta webhook registration
ngrok http 8000
```

No test suite exists — testing is done manually via WhatsApp with a live webhook.

## Architecture

```
main.py             → FastAPI app init, DB table creation, Uvicorn launch
api/webhook.py      → GET /webhook (verification) + POST /webhook (message handling)
services/
  ai_service.py     → NVIDIA NIM Llama 3.1 70B call, returns JSON {intencao, resposta_sugerida}
  whatsapp.py       → Meta Cloud API v19.0 (send text/buttons, parse incoming payload)
db/
  models.py         → SQLAlchemy models: Usuario, HistoricoConversa, Servico, Barbeiro
  database.py       → MySQL connection via pymysql, session dependency injection
core/
  prompts.py        → SYSTEM_PROMPT_BARBEARIA: all business rules injected into every AI call
```

### Message Flow

1. Meta sends POST to `/webhook` → function returns 200 OK immediately
2. Actual processing runs in a **FastAPI background task** (required by Meta's 15s timeout)
3. Bot checks `usuario.bot_ativo` — if `False`, message is silently dropped (human handoff mode)
4. Last 5 messages from `HistoricoConversa` are fetched and prepended as conversation context
5. Current services/barbers from DB are injected into the system prompt at call time
6. AI returns JSON; if `intencao == "chamar_recepcao"`, bot sets `bot_ativo=False` and hands off to human
7. Special command `!reiniciar` (sent by staff) resets `bot_ativo=True` for a user

### AI Response Contract

`ai_service.py` expects the model to return **exactly** this JSON (defined in `core/prompts.py`):
```json
{"intencao": "<string>", "resposta_sugerida": "<string>"}
```
Any JSON parse failure triggers automatic human handoff (`transbordo_falha` intent).

### WhatsApp Formatting

The system prompt mandates `<br>` tags for line breaks in AI responses. `whatsapp.py` sends these as-is to the Meta API, which renders them correctly in WhatsApp.

## Environment Variables

Copy `.env` structure (no `.env.example` exists):

| Variable | Purpose |
|---|---|
| `DB_USER`, `DB_PASS`, `DB_HOST`, `DB_NAME` | MySQL connection |
| `WHATSAPP_TOKEN` | Meta temporary access token (refreshes every 24h in sandbox) |
| `WHATSAPP_PHONE_ID` | WhatsApp Business phone number ID |
| `WEBHOOK_VERIFY_TOKEN` | Token for Meta webhook verification handshake |
| `NVIDIA_API_KEY` | NVIDIA NIM API key for Llama 3.1 70B |
| `GEMINI_API_KEY` | Present but **not used** — code uses NVIDIA NIM |

## Key Business Rules (in `core/prompts.py`)

- **Never book appointments** — always redirect to the AppBarber app
- Services split into two categories: 💈 barbershop (barbers) and 💆‍♀️ aesthetics (Isabella only)
- Cannot handle media (audio, images, documents)
- Tone: professional Portuguese, no slang, no colloquialisms
- Fred's personal contact: (38) 99897-0661 — shared **only** if client asks explicitly

## Database

Schema is in `barbearia_bot_db.sql`. SQLAlchemy creates tables automatically on startup via `Base.metadata.create_all()`. Migrations are manual — update models then recreate tables or alter them directly in MySQL.

## Operation Modes (`MODO_OPERACAO` env)

- `"bot_only"` (default) — pure IA mode, no human dashboard
- `"hibrido"` — enables admin dashboard at `/admin/*`, SSE events, operator takeover. Requires `JWT_SECRET`.

Hybrid mode is loaded conditionally in `main.py`: imports `/admin` router and mounts `/static` only when enabled.

## Pre-AI Processing Layers (`api/webhook.py`)

Messages pass through these checks **before** hitting the AI (cheapest-first):

1. Deduplication — `MensagemProcessada` table (DB-level, survives restarts); 1% chance of opportunistic cleanup
2. Rate limit — 10 msg/min per phone in-memory (`RATE_LIMIT_MSGS_POR_MINUTO`); buckets cleaned every 300s
3. Per-phone threading lock — 30-min TTL, prevents concurrent processing for same client
4. Auto-reactivation — if `bot_ativo=False` and `BOT_REATIVAR_APOS_HORAS` (default 24) elapsed, reactivates
5. First message → fixed welcome menu (no AI)
6. Menu request (regex `_PADROES_PEDIDO_MENU`) → fixed menu text
7. Pure greeting (`_e_saudacao_pura`) → personalized menu with client first name
8. Canonical FAQ (hours, address, booking, payment) → regex match from `core/respostas_canonicas.py`, zero AI cost

History auto-trimmed: >50 messages → keep newest 50 (AI context window uses last 15).

## AI Service Details (`services/ai_service.py`)

- DB cache (5-min TTL) for services/barbers — avoids 4 SQL queries per message
- Temporal context injected at call time: current date/time in São Paulo (UTC-3, no DST since 2019), open/closed status, schedule for next 2 days. Hours hardcoded Mon–Sat; Sunday closed.
- Anti-appointment regex: if IA output matches booking promise pattern, silently replaced with AppBarber redirect
- Anti-drift anchor: ≥6 messages in conversation → extra system reminder injected before user query
- Errors appended to `erro_ia_debug.txt` with ISO timestamp

## Human Handoff Mechanics

Handoff triggers: `intencao == "chamar_recepcao"` or `intencao == "transbordo_falha"` (JSON parse error).
Sets `bot_ativo=False`, `aguardando_humano=True`. In bot-only mode, replaces handoff promise with AppBarber guidance.

Button `"🙋 Falar c/ Recepção"` → same handoff logic.

Reactivation order in `devolver` (hybrid): send farewell message **first**, then reactivate bot — prevents race if client messages arrive mid-transition.

## Admin Dashboard (Hybrid Mode)

Endpoints in `api/admin.py`:
- `POST /admin/login` — bcrypt auth, returns JWT (HS256, `JWT_TTL_MIN` default 15 min); rate-limited 5 attempts/60s per IP
- `POST /admin/assumir/{telefone}` — conditional grab (only if `atendente_id IS NULL`); sends greeting, publishes SSE
- `POST /admin/enviar/{telefone}` — operator sends message; uses `\n` directly (not `<br>`)
- `POST /admin/devolver/{telefone}` — returns conversation to bot
- `GET /admin/eventos/stream` — SSE stream (heartbeat every 25s, queue max 100 events)

Create operator accounts via `scripts/criar_atendente.py` (interactive CLI, password min 8 chars).

## Text Formatting

AI responses use `<br>` for line breaks (mandated in system prompt). `_normalizar_texto_envio()` in `api/webhook.py` converts `<br>` and `\n` to actual newlines and collapses 3+ newlines to 2 before sending to Meta API. Operator messages use `\n` directly.

## Additional Environment Variables

| Variable | Purpose | Default |
|---|---|---|
| `MODO_OPERACAO` | `"bot_only"` or `"hibrido"` | `"bot_only"` |
| `JWT_SECRET` | Required for hybrid mode | — |
| `JWT_TTL_MIN` | JWT lifetime in minutes | 15 |
| `META_APP_SECRET` | HMAC webhook signature validation; if absent, dev mode (unsigned accepted) | — |
| `ADMIN_PHONES` | Comma-separated phones allowed to use `!reiniciar` | — |
| `BOT_REATIVAR_APOS_HORAS` | Hours before auto-reactivation after handoff | 24 |
| `RATE_LIMIT_MSGS_POR_MINUTO` | Per-phone rate limit | 10 |
| `LOG_LEVEL` | Set to `DEBUG` for full AI payload logging | INFO |

## Multi-Agent System

Specialized agents live in `.claude/agents/`. Claude principal IS the coordinator. Full workflow in `.claude/WORKFLOW.md`. Task history in `.claude/AGENT_STATE.md`.

| Agent | subagent_type | Model | Role |
|-------|---------------|-------|------|
| `po-agent` | po-agent | Opus 4.7 | Business rules — approves before Dev implements |
| `dev-agent` | dev-agent | Sonnet 4.6 | Implements features and bug fixes |
| `qa-agent` | qa-agent | Sonnet 4.6 | Quality review — always last before shipping |
| `db-agent` | db-agent | Haiku 4.5 | SQL migrations only (ADD/ALTER/DROP/RENAME) |
| `prompt-engineer` | prompt-engineer | Opus 4.7 | AI behavior and system prompt optimization |

**Two modes:**
- **Standalone**: `Agent(subagent_type="...")` sequential — Claude principal coordinates each step
- **Team**: `TeamCreate` + `Agent(name="...", run_in_background=True)` — agents communicate via `SendMessage` directly with each other

**Communication graph**: po → dev → qa (PASS → Claude principal, FAIL → dev). db → dev. prompt-engineer → qa.

**Standard flows:**
- Feature with client impact: `po → dev → [db →] qa`
- Technical bug: `dev → qa`
- AI behavior problem: `po → prompt-engineer → qa`
- Parallel audit: spawn qa + po + prompt-engineer simultaneously

**To start a full system improvement cycle:**
> "Faça uma revisão completa do sistema usando os agentes especializados"
