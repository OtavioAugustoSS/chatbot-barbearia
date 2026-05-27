# Revisão Geral Pós-Mega-Auditoria
Data: 2026-05-27
Auditor: qa-agent
Arquivos: index.html, app.js, sse.js, admin.py, webhook.py, whatsapp.py, prompts.py

---

## static/admin/index.html

index.html:787: [WARN] `#messages-area { background-color: #0b141a; }` — hardcoded no dark theme sem usar `var(--bg-chat)`. O token `--bg-chat: #090e13` diverge do valor hardcoded `#0b141a`. A regra `[data-theme="light"] #messages-area` (linha 789) usa var(--bg-chat) corretamente, mas o dark default não. Fix sugerido: substituir `#0b141a` por `var(--bg-chat)` em `#messages-area { background-color: ... }`.

index.html:1139-1140: [INFO] `#metric-atendendo { --metric-color: #00a884; }` e `#metric-bot { --metric-color: #2481cc; }` — valores hardcoded sem token. `--metric-aguardando` usa `var(--danger-text)` corretamente; os outros dois poderiam usar `var(--success)` e `var(--accent)`. Baixa prioridade: comentário na linha 1445 já documenta a impossibilidade de rgba sem token separado.

Todos os fixes auditados intactos:
- `<body` sem font-family Inter inline (linha 1452) — OK
- `body { font-family: var(--font-body, ...) }` (linha 152) — OK
- `.bolha-tick svg { }` vazio (linha 1336) — OK
- `.bolha-tick.tick-animate svg` com stroke-dasharray:30 (linha 1338) — OK
- `.entregue-status.delivered` usa rgba(255,255,255,0.55) (linha 1347) — OK
- `[data-theme="light"] #messages-area { background-color: var(--bg-chat); }` (linha 789) — OK
- `@media(max-width:1023px) #empty-state { display: flex !important; }` (linha 1283) — OK
- prefers-reduced-motion: animation:none !important (linha 1145) — OK
- `#chat-empty-state svg { animation: none !important; }` (linha 1149) — OK
- DS-01..DS-10 todos intactos.

---

## static/admin/js/app.js

app.js — OK em todos os itens auditados:
- `state = { ... presence: {} ... }` (linha 23) — OK
- `isUnread = (c.aguardando_humano && !c.atendente_id) || (c.mensagens_nao_lidas > 0)` (linhas 556-557) — OK
- `tempoBase = c.transbordo_em || c.ultima_mensagem_em` (linha 547) — OK
- `abrirConversa(state.conversaAtual)` após enviarMidia (linha 1419) — OK
- `div class="avatar w-11 h-11 ..."` em renderConvList (linha 565) — OK
- `showToast()` usa getComputedStyle (linhas 146-161) — OK

app.js:1930: [INFO] `state.views = []` declarado fora do objeto `state` literal como propriedade post-hoc. Todos os outros campos de estado estão no objeto inicial. Não é bug funcional; inconsistência de estilo. Fix opcional: mover `views: []` para dentro do objeto `state`.

---

## static/admin/js/sse.js

sse.js:16: [BUG] `dot.className = ok ? 'connected' : '';` — quando `failed=true` (permanentlyFailed), o dot recebe `className = ''` em vez de `'failed'`. O CSS `#conn-status-dot.failed { background: var(--danger-text) !important; }` (index.html:407) nunca é ativado porque a classe `failed` nunca é aplicada ao dot. O `headerDot` recebe `classList.add('failed')` corretamente (sse.js:26), mas o `conn-status-dot` do footer fica cinza genérico (#6b7280, linha 17) em vez de vermelho danger-text.
Fix sugerido: `dot.className = ok ? 'connected' : (failed ? 'failed' : '');` na linha 16.

sse.js — resto OK:
- Backoff exponencial 1s→30s com jitter ±20% (linhas 42-46) — OK
- Reset de _retryDelay=1000 em conexão bem-sucedida (linha 70) — OK
- Dispatch de CustomEvent `sse:${ev.tipo}` (linha 87) — OK
- Dispatch de `sse:connection_status` via _setConnStatus (linhas 8, 32-37) — OK

---

## api/admin.py

admin.py — OK em todos os itens auditados:
- `assumir()` check `user.atendente_id == me.id` → 400 ANTES do UPDATE (linhas 453-454) — OK
- `assumir()` tem `data_ultima_interacao: datetime.now(timezone.utc)` (linha 469) — OK
- `devolver()` tem `data_ultima_interacao: datetime.now(timezone.utc)` (linha 1107) — OK
- `bulk_acao()` tem `user.data_ultima_interacao = agora` antes de `db.flush()` (linha 859) — OK
- `bulk_acao()` tem try/except com `db.rollback()` por item (linhas 864-867) — OK
- `criar_canned()` usa `.is_(None)` (linha 1531) — OK
- `criar_nota()` commit único após flush de nota + flush de mentions (linhas 1834, 1812, 1840) — OK

---

## api/webhook.py

webhook.py — OK em todos os itens auditados:
- Media handler registra `MensagemProcessada` com message_id (linhas 1274-1280) — OK
- `_processar_status_updates()` atualiza `lida` e publica SSE `mensagem_lida` (linhas 1175-1221) — OK
- try/finally com `db.close()` em `_processar_status_updates` — OK

---

## services/whatsapp.py

whatsapp.py — OK em todos os itens auditados:
- `_post_com_retry()` trata 429 com Retry-After header + fallback 5s (linhas 27-33) — OK
- `response.json()` em try/except ValueError → (False, None) (linhas 47-53) — OK
- Todas as funções de envio retornam (bool, wamid_or_None) — OK

---

## core/prompts.py

prompts.py — OK:
- "use EXCLUSIVAMENTE o CONTEXTO TEMPORAL injetado" (linha 14) — OK
- Exemplos de horário usam [HORA_ABERTURA]/[HORA_FECHAMENTO] (linhas 158, 161, 164, 174, 188) — OK
- Nenhum "14:00", "21:00", "09:00" hardcoded nos exemplos — OK

---

## Resumo de achados

| Severidade | Qtd | Items |
|---|---|---|
| CRÍTICO | 0 | — |
| BUG | 1 | sse.js:16 — dot.className nunca recebe 'failed' |
| WARN | 1 | index.html:787 — #messages-area background hardcoded #0b141a diverge de --bg-chat |
| INFO | 2 | index.html:1139-1140 metric tokens sem var(); app.js:1930 state.views fora do objeto |

**Total: 4 achados. Nenhum crítico.**
