---
type: qa
title: "RECON_REPORT — QA Full Sweep"
updated: 2026-05-27
tags: [qa, recon, full-sweep]
related: ["[[TEST_PLAN]]", "[[FINDINGS]]", "[[fixes-status]]"]
---

# RECON REPORT — Fase A do QA Full Sweep

Branch: `qa/full-sweep`. Stack real: FastAPI + SQLAlchemy + MySQL (pymysql) + NVIDIA NIM
(Llama 3.1 70B) + SSE + JWT HS256 + frontend vanilla JS.

Legenda de confiança: ✅ verificado por leitura direta nesta sessão · 🔍 mapeado por Explore,
re-confirmar na execução.

---

## 1. Árvore e tamanho dos arquivos-chave (✅ via wc -l)

| Arquivo | Linhas | Papel |
|---|---|---|
| `api/webhook.py` | 1416 | GET/POST `/webhook`, pipeline pré-IA, handoff, background task IA, status updates |
| `api/admin.py` | 2028 | 40+ endpoints `/admin/*`, SSE stream, auth JWT |
| `services/whatsapp.py` | 344 | Meta Cloud API v19.0; `enviar_mensagem_texto()` retorna `(ok, wamid)` |
| `services/ai_service.py` | 475 | Chamada NVIDIA NIM, contrato JSON, cache 5min, contexto temporal, anti-agendamento |
| `db/models.py` | 231 | Usuario, HistoricoConversa, MensagemProcessada, Atendente, Servico, Barbeiro, Label, etc. |
| `main.py` | 69 | Init FastAPI, TZ=UTC, create_all, gating MODO_HIBRIDO, uvicorn |
| `core/prompts.py` | 263 | SYSTEM_PROMPT_BARBEARIA |
| `core/respostas_canonicas.py` | 292 | FAQ canônica regex (horário, endereço, agendamento, pagamento) |
| `static/admin/index.html` | 1956 | Dashboard (markup + CSS inline, dark/light) |
| `static/admin/login.html` | 448 | Login + toggle senha |
| `static/admin/settings.html` | 843 | Atendentes, etiquetas, canned, tema |
| `static/admin/js/app.js` | 3351 | Estado, render, handlers, modais, draft, listeners SSE |
| `static/admin/js/api.js` | 245 | Wrapper fetch `/admin/*`, 401→logout |
| `static/admin/js/sse.js` | 101 | EventSource, backoff exponencial, dispatch `sse:{tipo}` |

> ⚠️ **Discrepância detectada:** Explore citou `sse.js:407-411` (connPulse/connecting) mas o
> arquivo tem só 101 linhas. A lógica de status de conexão (`connecting`/`failed`/`connected`)
> provavelmente está em `app.js` ou no CSS de `index.html`. **Re-confirmar refs de linha do
> frontend na Fase C** antes de citar em achados.

`scripts/`: `criar_atendente.py`, `aplicar_migrations.py`, `seed_horarios.py`.
`scripts/migrations/`: 23 arquivos SQL (`0001`→`0011`, série `TASK*`, `US-TICKS-01-lida-wamid.sql`).

---

## 2. Fluxo de handoff IA→humano (✅ grab verificado; 🔍 resto)

1. **Detecção** (`api/webhook.py` ~1130-1166 🔍): IA retorna `intencao` ∈ {`chamar_recepcao`,
   `transbordo_falha`}. `transbordo_falha` = falha de parse do JSON da IA.
2. **Marcação**: `bot_ativo=False`, `bot_desativado_em=now(UTC)`, `aguardando_humano=True`,
   `transbordo_em=now(UTC)`.
3. **Notificação**: SSE `novo_transbordo` `{tipo, telefone, nome, motivo}`.
4. **Botão** "🙋 Falar c/ Recepção" → `_executar_handoff_recepcao()` (~282-312 🔍) → mesmo efeito.
5. **Bot-only mode**: substitui promessa de handoff por link AppBarber; bot permanece ativo.
6. **Assumir** (`api/admin.py:440-516` ✅): pré-checagem (404/400/409) + UPDATE atômico
   `WHERE telefone=X AND atendente_id IS NULL` setando `atendente_id, bot_ativo=False,
   aguardando_humano=False, status_conversa="open"`. Se `afetadas==0` na corrida → **409**.
   Publica SSE `atendente_assumiu` + `nova_mensagem` (saudação) + `status_alterado(open)`.
7. **Devolver** (`api/admin.py` ~1100-1215 🔍): UPDATE `WHERE telefone=X AND atendente_id=me.id`,
   reseta `atendente_id=NULL, bot_ativo=True, aguardando_humano=False, transbordo_em=NULL`.
   `?silent=true` suprime WhatsApp. Publica `bot_devolveu` + `status_alterado`.

**Corrida de "assumir" (✅):** dois atendentes que leem `atendente_id=None` na pré-checagem
ambos tentam o UPDATE; só um recebe `afetadas=1`. O perdedor (stale `user.atendente_id=None`,
`None != me.id` → True) recebe **409**. Race tratada corretamente.

---

## 3. Endpoints `/admin/*` (🔍 — 40+ rotas, todas JWT exceto login)

Login: `POST /admin/login` (bcrypt, rate-limit 5/60s por IP).
Conversas: `GET /conversas`, `GET /conversa/{tel}`, `POST /assumir/{tel}`, `POST /devolver/{tel}`,
`POST /enviar/{tel}`, `POST /enviar-midia/{tel}`.
Status/tag: `PATCH /conversa/{tel}/status`, `PATCH /conversa/{tel}/tag` (deprecado).
Labels: `GET/POST /labels`, `PATCH/DELETE /labels/{id}`, `POST /conversa/{tel}/labels`,
`DELETE /conversa/{tel}/labels/{label_id}`.
Notas: `GET/POST /notas/{tel}`, `PATCH/DELETE /notas/{nota_id}` (só criador edita).
Atendentes: `GET/POST /atendentes`, `PATCH /atendentes/{id}/desativar|ativar`,
`POST /conversa/{tel}/atribuir` (transferência).
Canned: `GET/POST /canned`, `PATCH/DELETE /canned/{id}`.
Mentions: `GET /mentions/inbox`, `PATCH /mentions/{id}/marcar-lida`.
Bulk: `POST /conversas/bulk` (resolver/snooze/atribuir/label).
Presence: `GET/POST /presence` (heartbeat 30s, auto-offline 90s).
Views: `GET/POST /views`, `PATCH/DELETE /views/{id}`.
Search: `GET /search` (LIKE + snippet — sem FULLTEXT, TD-007).
Cliente: `GET /cliente/{tel}/info`.
SSE: `GET /eventos/stream` (heartbeat 25s, fila máx 100, drop-oldest — ADR-005).

---

## 4. Pipeline pré-IA em `api/webhook.py` (🔍 — ordem cheapest-first)

1. HMAC `_validar_assinatura_meta()` (X-Hub-Signature-256; ausente `META_APP_SECRET` = dev mode).
2. Dedup DB `_ja_processada()` via `MensagemProcessada` (TTL ~2h, cleanup 1%).
3. Rate limit `_excedeu_rate_limit()` (10 msg/min por telefone, janela 60s in-memory).
4. Lock por telefone `_lock_do_telefone()` (TTL 30min, acquire timeout 90s no background task).
5. Auto-reativação `_verificar_e_reativar_bot()` (se `bot_ativo=False` + >24h + sem atendente).
6. Boas-vindas (primeira msg, histórico vazio) → lista interativa, sem IA.
7. Botões de handoff (síncrono) → `_executar_handoff_recepcao()`.
8. Menu interativo `_despachar_menu_principal()` (serviços/equipe/pagamento/horários, DB+texto).
9. Saudação pura `_e_saudacao_pura()` → menu personalizado.
10. FAQ canônica `detectar_resposta_canonica()` → texto determinístico, zero IA.
11. Enfileira `tarefa_em_segundo_plano_ia()` (só se tudo acima passou).

---

## 5. SSE — 11 tipos de evento (🔍)

`nova_mensagem`, `novo_transbordo`, `atendente_assumiu`, `bot_devolveu`, `status_alterado`,
`mensagem_lida` (`{tipo, wamid, status, telefone}`), `presence_changed`, `conversa_atribuida`,
`bulk_aplicado`, `nova_mention`. Frontend dispara `CustomEvent('sse:{tipo}')` consumido em app.js.

**Read receipts (🔍):** Meta envia `statuses[]` no mesmo POST `/webhook`.
`_processar_status_updates()` (~1175-1225) busca `HistoricoConversa.wamid==wamid`, seta
`entregue`/`lida`, publica SSE `mensagem_lida`. Ticks no painel: ⏱ (enviando) → ✓ (entregue) →
✓✓ (lido, azul #53bdeb).

---

## 6. Ações disparáveis no painel (🔍 — base do checklist funcional)

~48 ações mapeadas. Grupos: **sidebar** (mentions inbox, settings, mute, métricas-filtro, tabs,
status-filter, bulk bar, search + modo @/?, views, save view); **thread header** (drawer mobile,
assumir, interromper bot, devolver, transferir, status, tag, info toggle); **composer**
(attach/upload mídia, canned popover, enviar, remove anexo); **info panel** (close, add label,
label picker, remove label, salvar/editar/deletar nota); **mensagens** (botão novas mensagens,
retry de falha); **modais** (confirm, snooze presets, input, atalhos, command palette Cmd+K);
**login** (toggle senha, entrar); **settings** (tabs, ação primária, ativar/desativar atendente,
editar/desativar label, editar/deletar canned, escolher tema).

> Refs de elemento/handler/linha do app.js (3351 linhas) virão re-confirmadas na Fase C ao montar
> os casos funcionais — os números do Explore não foram verificados linha-a-linha.

---

## 7. Persistência (🔍 db/models.py)

- **Usuario** (PK `telefone`): `bot_ativo`, `bot_desativado_em`, `aguardando_humano`,
  `transbordo_em`, `atendente_id` (FK), `status_conversa` (open/pending/resolved/snoozed),
  `snoozed_until`, `resolved_em/por`, `reativado_por_timeout`, `data_ultima_interacao`, `tag`.
- **HistoricoConversa** (PK `id`): `telefone_usuario` (FK), `mensagem_cliente`, `resposta_bot`,
  `origem` (bot/humano/cliente), `intencao`, `atendente_id`, `entregue`, **`wamid`** (indexado),
  **`lida`**, `criado_em`. Índice composto `(telefone_usuario, criado_em)`.
- **MensagemProcessada** (PK `message_id`): dedup, `processada_em` indexado.
- **Atendente** (PK `id`): `nome`, `usuario_login` (único), `senha_hash` (bcrypt), `ativo`,
  `criado_em`, `ultimo_login`.

---

## 8. Env vars e configs sensíveis (🔍)

Obrigatórias: `DB_USER/PASS/HOST/NAME`, `WHATSAPP_TOKEN` (refresca 24h), `WHATSAPP_PHONE_ID`,
`WEBHOOK_VERIFY_TOKEN`, `NVIDIA_API_KEY`. Hibrido: `MODO_OPERACAO=hibrido` + `JWT_SECRET` (main.py
levanta RuntimeError se faltar). Opcionais: `JWT_TTL_MIN` (15), `META_APP_SECRET` (sem ele,
webhook aceita POST sem HMAC — risco prod, main.py loga warning crítico), `LOG_LEVEL`,
`BOT_REATIVAR_APOS_HORAS` (24), `RATE_LIMIT_MSGS_POR_MINUTO` (10), `ADMIN_PHONES`.
`GEMINI_API_KEY` presente porém **não usado** (dead config). `.env` e `.env.example` existem.

---

## 9. Dívida técnica relevante ao sweep (do TECH-DEBT-001 / ADRs)

- **TD-002 CRÍTICO:** zero testes automatizados → este sweep cria o harness.
- **TD-001:** TZ=UTC — confirmar que o deploy real seta TZ.
- **TD-007:** `/admin/search` usa LIKE sem índice FULLTEXT.
- **ADR-011:** RBAC ausente — atendente lê qualquer conversa (validar mitigações vs IDOR).
- **ADR-010:** `tarefa_em_segundo_plano_ia` engole exceção na raiz.
- **ADR-005:** SSE drop-oldest, fila 100, heartbeat 25s.
- Contexto: branch `main` recém-recebeu mega-auditoria (31 bugs) + sprint UI/UX (15 melhorias),
  commit `a01dd1e`. **Atenção a regressões** dessa sprint grande.

---

## 10. Suposições (corrigir se erradas)

1. O banco MySQL de dev é descartável/teste — mas **não rodarei comando destrutivo** sem OK.
2. `MODO_OPERACAO=hibrido` está/estará no `.env` para o sweep do painel valer.
3. Posso criar atendente de teste via `scripts/criar_atendente.py` (aguardo autorização + uso de
   um login/senha de teste, não credenciais reais de produção).
4. Testes unit/integração podem rodar contra um SQLite ou MySQL local de teste com mocks de
   Meta/NVIDIA; o E2E "live" exige o servidor + ngrok que você sobe.

**Estimativa de loop:** 3–6 iterações de fix→reteste (assumindo que a mega-auditoria recente já
zerou a maioria dos P0/P1; sweep deve achar regressões + gaps de borda + itens de segurança).
