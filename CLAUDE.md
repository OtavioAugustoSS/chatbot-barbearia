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
- Fred's personal contact: (38) 99897-0661

## Database

Schema is in `barbearia_bot_db.sql`. SQLAlchemy creates tables automatically on startup via `Base.metadata.create_all()`. Migrations are manual — update models then recreate tables or alter them directly in MySQL.
