# SPRINT-FIXES.md — Frontend FASE 3

**Data:** 2026-05-21
**Agente:** frontend-agent
**Arquivos alterados:**
- `static/admin/js/sse.js`
- `static/admin/js/app.js`
- `static/admin/index.html`
- `static/admin/login.html`

---

## QW-F1 — SSE Backoff Exponencial

**Bug:** `sse.js` linha 57 usava `setTimeout(conectar, 3000)` fixo. Sob instabilidade de rede, múltiplos atendentes reconectam simultaneamente (thundering herd).

**Solução:** Backoff exponencial com jitter ±20%.
- Variáveis de estado: `_retryDelay = 1000`, `_retryCount = 0`, `_MAX_DELAY = 30000`
- Função `_agendarReconexao()`: aplica jitter, incrementa `_retryCount`, dobra `_retryDelay` até 30s
- Reset em conexão bem-sucedida: `_retryDelay = 1000`, `_retryCount = 0`
- Log: `[SSE] Reconectando em ${delay}ms (tentativa ${_retryCount})`

**Arquivo:linha:** `static/admin/js/sse.js:21-30` (função `_agendarReconexao`)

---

## QW-F3 — Limpar bulkSelecionadas ao Trocar Filtro

**Bug:** `state.bulkSelecionadas` (Set) não era limpo ao trocar filtro via filter-tabs ou status-filter-row. Conversas selecionadas persistiam invisíveis — ações bulk agiriam em conversas que o atendente não estava vendo.

**Solução:** Adicionar `state.bulkSelecionadas.clear()` + `atualizarBulkBar()` em dois handlers:
1. Handler de `#filter-tabs` click — após trocar `state.filtro`
2. Handler de `#status-filter-row` click — após trocar `state.statusFiltro`

**Arquivo:linha:** `static/admin/js/app.js` — handler filter-tabs (~linha 1748) e status-filter-row (~linha 1929)

---

## QW-F2 — Badge Contagem no Título da Aba

**Feature:** US-127. Mostrar contagem de conversas aguardando no título da aba do browser para monitoramento passivo.

**Solução:** Na função `atualizarBadges(totais)`, adicionar ao final:
```js
const aguardando = totais.aguardando || 0;
document.title = aguardando > 0
  ? `(${aguardando}) Bolshoi — Atendimento`
  : 'Bolshoi — Atendimento';
```

Títulos padronizados:
- `index.html`: `<title>Bolshoi — Atendimento</title>` (padrão sem notificação)
- `login.html`: `<title>Bolshoi — Login</title>`

**Arquivo:linha:** `static/admin/js/app.js` — função `atualizarBadges` (~linha 265); `static/admin/index.html` linha 6; `static/admin/login.html` linha 6

---

## QW-F4 — Separadores de Handoff com Nome do Atendente (US-039)

**Estado anterior:** `separadorEvento()` já existia e era chamado em `renderMensagens()`, mas exibia texto genérico "Atendente assumiu" / "Bot retomou" sem nome do atendente nem horário.

**Solução:**
1. `separadorEvento(label, horario)` — assinatura extendida com parâmetro `horario` opcional que renderiza `horaCurta(horario)` inline no separador.
2. `renderMensagens()` — usa `m.atendente_nome` quando disponível; fallback "Atendente". Passa `m.criado_em` como horário. Texto: "João assumiu o atendimento HH:MM" ou "Bot retomou o atendimento HH:MM".
3. `appendMensagemIncremental(texto, origem, entregue, tempId, opts)` — assinatura extendida com `opts = {}`. Usa `opts.atendente_nome` nos separadores incrementais.
4. Handler `sse:nova_mensagem` — passa `ev.atendente_nome` para `appendMensagemIncremental`.

**Arquivo:linha:** `static/admin/js/app.js` — `separadorEvento` (~linha 310), `renderMensagens` (~linha 390), `appendMensagemIncremental` (~linha 414)

---

## SP-1 — Modal Datepicker para Snooze (substitui 3x window.prompt())

**Bug crítico:** 3 usos de `window.prompt()` confirmados — bloqueia a UI, não funciona em alguns browsers mobile, impossível de customizar.

| Localização original | Função | Substituído por |
|---------------------|--------|-----------------|
| linha ~845 | `alterarStatus('snoozed')` | `await abrirModalSnooze()` |
| linha ~1172 | `salvarViewAtual()` | `await abrirModalInputTexto()` |
| linha ~1279 | `bulkSnooze()` | `await abrirModalSnooze()` |

**HTML adicionado (`index.html` antes de `</body>`):**
- `#modal-snooze` — overlay com 4 preset buttons (1h, 4h, 24h, 1 semana), `<input type="datetime-local">`, botões confirmar/cancelar
- `#modal-input-text` — overlay genérico com `<input type="text">`, título e descrição configuráveis, botões confirmar/cancelar

**JS adicionado (`app.js` antes das Tag helpers):**

`abrirModalSnooze() → Promise<string|null>`
- Presets definem o datetime-local e resolvem a Promise imediatamente com ISO timestamp
- Confirmar valida que a data é no futuro
- Cancelar / ESC / click no overlay resolve com `null`
- Cleanup remove todos os listeners ao fechar

`abrirModalInputTexto(titulo, descricao, placeholder) → Promise<string|null>`
- Input genérico para qualquer texto
- Validação: não permite string vazia
- Enter confirma, ESC cancela, click no overlay cancela

**Correção auxiliar:** `bulkSnooze` toast substituiu `${h}h` (variável removida) por mensagem genérica com contagem de sucesso/falha.

**Arquivo:linha:** `static/admin/index.html` (~linha 509); `static/admin/js/app.js` — funções `abrirModalSnooze` e `abrirModalInputTexto` (~linha 172)

---

*Gerado em 2026-05-21 por frontend-agent — FASE 3.*
