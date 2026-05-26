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

## Multi-Agent System — `barbearia-bolshoi-team`

Agent team **in-process** (Windows, sem tmux). 4 teammates + lead. Todos Sonnet 4.6.

### Teammates

| Name | Role | Domínio | Output |
|---|---|---|---|
| `product-owner-agent` | Product Owner | Regras de negócio, user stories | `.claude/wiki/business-rules/`, `docs/user-stories/` |
| `architect-agent` | Architect | Decisões técnicas, ADRs | `.claude/wiki/decisions/ADR-NNN-{slug}.md`, atualiza `CLAUDE.md` |
| `backend-agent` | Backend Dev | `api/`, `services/`, `db/`, `core/`, `scripts/` | Código Python + migrations SQL |
| `frontend-agent` | Frontend Dev | `static/admin/` (vanilla JS) | HTML/JS/CSS |
| `qa-agent` | QA Engineer | Auditoria de qualidade + fidelidade visual ao design | `.claude/wiki/qa/{slug}.md` (punch lists) |
| `lead-agent` (sessão principal) | Tech Lead | Coordena time, gera release reports | `docs/release/{versão}.md` |

### Memória compartilhada (`.claude/wiki/`)

Filesystem-only (sem MCP no MVP). Todos os teammates seguem o protocolo:

1. **Ao iniciar trabalho:** ler `hot.md` → `index.md` → diretório do próprio domínio
2. **Ao concluir tarefa:** append em `log.md` (formato: `[ISO timestamp] [agent] [task-id] resumo`)
3. **Decisões persistentes:** criar `.md` no diretório do domínio + registrar em `index.md`

```
.claude/wiki/
  hot.md           ← cache (atualizado pelo lead)
  index.md         ← catálogo mestre
  log.md           ← append-only ops log
  business-rules/  ← PO
  decisions/       ← Architect (ADRs)
  backend/         ← Backend
  frontend/        ← Frontend
```

### Grafo de comunicação

- `backend-agent` → `product-owner-agent` (dúvida funcional)
- `backend-agent` → `architect-agent` (dúvida técnica)
- `backend-agent` → `frontend-agent` (contrato de endpoint mudou)
- `frontend-agent` → `backend-agent` (obter contrato)
- `frontend-agent` → `architect-agent` (dúvida técnica)
- `frontend-agent` → `product-owner-agent` (dúvida funcional)
- Todos → `lead-agent` (reporte de conclusão)

### Regras rígidas globais

- Bot **NUNCA agenda** — sempre redirecionar para AppBarber (PO bloqueia)
- Mudança no **AI Response Contract** (`{intencao, resposta_sugerida}`) exige ADR aprovado pelo humano (Architect bloqueia)
- Frontend é **vanilla JS** — introduzir framework exige ADR (Architect bloqueia)
- Migrations **manuais**, SQL em `scripts/migrations/{TASK}-{descricao}.sql` ANTES de alterar `db/models.py`
- Operador usa `\n`, IA usa `<br>` — não confundir

### Como ativar o time

O time usa a infraestrutura nativa de Agent Teams do Claude Code (`CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1` em `settings.json`).

**Criar o time (lead cria via `TeamCreate`, depois spawna teammates):**
```
Crie o agent team barbearia-bolshoi-team e spawne os 4 teammates:
product-owner-agent, architect-agent, backend-agent, frontend-agent.
Use as subagent definitions em .claude/agents/.
```

**Infraestrutura criada automaticamente:**
- `~/.claude/teams/barbearia-bolshoi-team/config.json` — config do time
- `~/.claude/tasks/barbearia-bolshoi-team/` — task list compartilhada

### Como interagir

- `Shift+Down` cicla entre teammates ativos
- Falar com teammate específico: cycle até ele e digitar
- Assignar task: "lead, crie task X e atribua ao backend-agent"
- Pedir release: "lead, gere o release report 0.1.0 em docs/release/"
- Encerrar: "lead, shutdown todos os teammates e cleanup do time"

### Comunicação entre teammates

Teammates se comunicam via `SendMessage` (não via Agent()). O lead recebe mensagens automaticamente. Peer DMs são visíveis ao lead como resumo no idle notification.

### Reuso standalone

Subagent definitions em `.claude/agents/` ainda funcionam fora do time quando o contexto não requer coordenação entre agentes:
- `Agent(subagent_type="product-owner-agent", prompt=...)`
- `Agent(subagent_type="architect-agent", prompt=...)`
- `Agent(subagent_type="backend-agent", prompt=...)`
- `Agent(subagent_type="frontend-agent", prompt=...)`

**Diferença:** subagent isolado só reporta de volta ao lead. Teammate no time pode fazer `SendMessage` para outros teammates diretamente.
