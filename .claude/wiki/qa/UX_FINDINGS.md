---
type: qa
title: "UX_FINDINGS — Sprint de Usabilidade"
updated: 2026-05-28
tags: [qa, ux, usabilidade, full-sweep]
related: ["[[UX_FINAL_REPORT]]", "[[UX_SETTINGS_CHECK]]", "[[FEATURE_BACKLOG]]"]
---

# UX FINDINGS — Sprint de Usabilidade (branch ui/usabilidade)

6 problemas reportados pelo usuário, mapeados no código real, corrigidos pelo frontend-agent e
validados pelo Lead (Playwright ao vivo na :8000) + qa-agent (settings) + pytest (regressão 47/47).
Evidência ao vivo via DOM/computed-style (mais robusta que screenshot pequeno). Screenshots:
`ux-antes-01-dashboard.png`, `ux-depois-01-dashboard.png`, `ux-depois-02-busca-origem.png`.

| ID | Problema | Status | Evidência (depois) |
|---|---|---|---|
| P1 | Sidebar com status cortado | **RESOLVED** | `#conv-list` `min-height:0; flex:1; overflow-y:auto`; `#sidebar-footer`+métricas+abas `flex-shrink:0` → footer sempre visível |
| P2 | Canned popover pequeno/mal posto | **RESOLVED** | `width:min(360px,calc(100vw-24px))`, `max-height:320px` responsiva; `_posicionarCannedPopover()` com clamp horizontal |
| P3 | Ticks sobrepostos / leitura errada | **RESOLVED** | `.bolha-tick` fixo 20×14; double-check viewBox 18×11 redesenhado; **delivered cinza** (rgba .55) vs **read azul #53bdeb** (rgb 83,189,235) distintos |
| P4 | Auto-scroll não rola em msg nova | **RESOLVED** | `eraNoFundo` capturado ANTES do append + scroll em `requestAnimationFrame` (app.js:1140-1154) |
| P5 | Busca mistura msgs/bot | **RESOLVED** | resultados rotulados ao vivo: "👤 Cliente· …", "🤖 Bot· …"; botão "Contato"/"Mensagem" |
| P6 | Verificar settings | **VERIFICADO + gaps corrigidos** | qa: 14/14 endpoints OK; frontend corrigiu GAP-A/B/C |

---

## Detalhe por problema

### P1 — Sidebar com status cortado [RESOLVED]
- **Causa:** `#conv-list` era `flex:1` sem `min-height:0` num flex-column com `overflow:hidden`;
  métricas/abas sem `flex-shrink:0` → lista longa empurrava `#sidebar-footer` (status conexão) pra fora.
- **Fix (index.html):** `flex-shrink:0` em search-row, metric-cards, filter-tabs, views-row,
  status-filter-row, bulk-bar, sidebar-footer; `#conv-list` → `flex:1; min-height:0; overflow-y:auto`.
- **Validação:** computed `min-height: 0px` no `#conv-list`, footer presente. A lista rola interna,
  footer fixo.

### P2 — Respostas rápidas pequeno/mal posicionado [RESOLVED]
- **Causa:** `#canned-popover` `width:300px; max-height:200px` fixos; JS posicionava sem clamp.
- **Fix:** largura/altura responsivas (`min(360px,calc(100vw-24px))` / `min(320px,calc(100vh-120px))`);
  `_posicionarCannedPopover(popover, refBtn)` (app.js) clampa left p/ não vazar à direita; usado nos
  dois gatilhos (botão + slash autocomplete).
- **Validação:** computed `max-height: 320px`; função `_posicionarCannedPopover` presente.
- **Nota:** mantém `position:fixed` do ADR-012 (sem mudança de contrato → sem ADR novo).

### P3 — Visto/entregue sobreposto e leitura errada [RESOLVED]
- **Causa:** double-check com polylines muito sobrepostas (x=1 e x=7, width 20) + `.bolha-tick`/svg
  sem dimensão fixa → strokes empilhavam; READ reusava SVG do DELIVERED.
- **Fix:** SVG redesenhado (viewBox 18×11, segundo check deslocado); `.bolha-tick` fixo 20×14
  `overflow:hidden`, `svg{display:block}`; `.tick-read{color:#53bdeb}`. 3 estados distintos.
- **Validação ao vivo:** delivered svg=18 cinza rgba(255,255,255,.55); read svg=18 azul
  rgb(83,189,235); fail svg=14 vermelho. Container 20×14 em todos.

### P4 — Auto-scroll não funciona em msg nova [RESOLVED]
- **Causa:** `appendMensagemIncremental` media `scrollHeight` ANTES do reflow (stale) → não rolava.
- **Fix:** captura `eraNoFundo = _estaNoFundo()` antes do `appendChild`; se estava no fundo, rola
  dentro de `requestAnimationFrame(() => cont.scrollTop = cont.scrollHeight)`; senão mostra "Novas
  mensagens".
- **Validação:** code review (correto). Teste ponta-a-ponta com msg inbound real fica para reteste
  `[USER-IN-LOOP]` (não disparei WhatsApp real). Lógica sólida e padrão (rAF pós-append).

### P5 — Busca mistura mensagens e chats de bot [RESOLVED]
- **Decisão (usuário):** rotular origem (não excluir).
- **Fix:** `_origemLabel(origem)` → 🤖 Bot / 👤 Cliente / 👩‍💼 Operador; `renderSearchResults` exibe
  o rótulo + snippet (escapeHtml); botão `#btn-search-mode` "Contato"/"Mensagem" (era @/?).
- **Validação ao vivo:** busca "corte" → "👤 Cliente· queria marcar um corte", "🤖 Bot· quais os
  serviços e preços?". Origem clara por resultado.

### P6 — Verificar settings + gaps [VERIFICADO + RESOLVED]
- **qa-agent (UX_SETTINGS_CHECK.md):** 14/14 endpoints das 4 abas OK (201/200/204); cleanup feito.
- **Gaps corrigidos (frontend, settings.html):**
  - **GAP-A [P1]:** `carregarCanned()` mostrava "Funcionalidade em implementação" em qualquer erro →
    agora `showMsg('Erro ao carregar respostas rápidas','error')`.
  - **GAP-B [P1]:** `e.message?.includes('409')` nunca disparava (req lançava Error(body)) → `req()`
    agora anexa `err.status`; checks usam `e.status === 409` → mensagens de conflito corretas.
  - **GAP-C [P2]:** input hex sem validação → `required maxlength title` + validação
    `/^#[0-9a-fA-F]{6}$/` no handler antes do submit.

---

## Regressão
`.venv/Scripts/python.exe -m pytest -q` → **47 passed** (sem regressão backend; fixes são frontend).

## Nota de ambiente
O browser cacheou agressivamente os estáticos; foi preciso revalidar (`fetch cache:'reload'`) +
cache-buster na URL para o Playwright pegar o JS/HTML novos. **Não é bug do produto** — porém sugere
considerar versionamento de assets (ex: `app.js?v=hash`) p/ evitar que operadores fiquem em versão
velha após deploy. Anotado como candidato no backlog.
