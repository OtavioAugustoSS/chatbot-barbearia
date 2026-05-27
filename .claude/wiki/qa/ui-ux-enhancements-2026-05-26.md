---
name: ui-ux-enhancements-2026-05-26
description: QA audit das 15 melhorias UI/UX implementadas em Tasks #1/#2/#3 — animações, acessibilidade, glassmorphism, presença e interações no admin dashboard
metadata:
  type: qa
---

# QA — UI/UX Enhancements 2026-05-26

Auditoria das 15 melhorias implementadas pelo frontend-agent em Tasks #1, #2 e #3.
Arquivos auditados: `static/admin/index.html`, `static/admin/js/app.js`, `static/admin/js/sse.js`.

---

## Punch List

### P0 — CRITICAL

```
static/admin/index.html:1155-1168 + 1310: CRITICAL: @keyframes toastSlideOut declarado duas vezes.
  Bloco Gap 2 (linhas 1154-1168) define toastSlideOut com `to { translateX(100%) }` e aplica-o
  em `.toast-item.toast-exit`. TASK 2.1 (linha 1310) redefine toastSlideOut com
  `to { translateX(120%) }` e aplica-o em `.toast-leaving`.
  JS usa `.toast-leaving` (app.js:140), nunca `.toast-exit` — o bloco Gap 2 e dead code conflitante.
  O browser usa a ULTIMA declaracao do keyframe (TASK 2.1, 120%), mas a regra `.toast-item.toast-exit`
  do Gap 2 continua existindo e aponta para o keyframe reescrito, divergindo do esperado.
  Fix: remover o bloco Gap 2 inteiro (linhas 1154-1168). Dono: frontend-agent.
```

---

### P1 — WARNING

```
static/admin/index.html:228-234: WARNING: Bloco prefers-reduced-motion duplicado e incompleto.
  Linha 228 (bloco original) nao inclui `scroll-behavior: auto`. Linha 1144 (TASK 1.1) e completo.
  O bloco da 228 e redundante.
  Fix: remover bloco das linhas 228-234. Dono: frontend-agent.

static/admin/index.html:1403-1419: WARNING: .bubble-action-btn altura ~24px, abaixo de 44px.
  padding: 3px 6px + font-size: 11px resulta em ~24px de altura.
  Checklist exige area minima de toque; dentro de bolha 32px e o minimo aceitavel.
  Fix: adicionar min-height: 32px ou documentar excecao em ADR. Dono: frontend-agent.

static/admin/index.html:1433-1435: WARNING: presencePulse usa cor hardcoded rgba(0,168,132,...).
  --success em light mode e #059669, nao #00a884 — pulse diverge em light mode.
  Fix: usar variavel CSS ou overlay com opacidade relativa ao token --success-text.
  Dono: frontend-agent.

static/admin/index.html:1208: WARNING: #typing-indicator HTML estatico sem aria-label.
  Apenas o elemento criado dinamicamente por JS (app.js:1004) recebe aria-label="Processando...".
  O elemento estatico na linha 1208 nao tem aria-label — screen readers nao anunciam o estado
  quando o CSS apenas adiciona a classe .visible sem recriar o elemento.
  Fix: adicionar aria-label="Cliente digitando" no HTML estatico (index.html:1208). Dono: frontend-agent.
```

---

### P2 — INFO

```
static/admin/index.html:1204: INFO: typingBounce duracao 1.2s, checklist especifica loops >= 1.5s.
  floatIdle (3s), presencePulse (2s) e floatBounce (1.8s) estao corretos.
  typingBounce esta em 1.2s — abaixo do minimo de 1.5s especificado.
  Fix: ajustar para 1.5s ease-in-out infinite. Dono: frontend-agent.
```

---

## PASS — Itens verificados e aprovados

- `prefers-reduced-motion` bloco completo existe (linha 1144) e cobre todos os keyframes via `*`
- Nenhum keyframe novo anima width/height/top/left — apenas transform/opacity/stroke-dashoffset
- Micro-interactions (badgePop 320ms, tickReveal 300ms, textFadeThrough 220ms): 120-300ms — PASS
- floatIdle 3s, presencePulse 2s, floatBounce 1.8s: >= 1.5s — PASS
- `floatBounce` em `.btn-novas-msgs.visible.bounce-active` usa `ease-in-out` (linha 1336) — PASS
- `#conn-status` tem `aria-live="polite"` (index.html:1554) — PASS
- `.bubble-action-btn` tem texto visivel "Copiar" (app.js:865) — PASS
- `#chat-empty-state` descritivo com `<p>` e `<span>` (index.html:1651-1654) — PASS
- `[data-theme="light"] #composer` existe com background e border (index.html:1365-1368) — PASS
- Novos elementos usam variaveis CSS (excecao presencePulse reportada em P1) — PASS
- Nenhum `import`/`require` introduzido — PASS
- `_countUp()` usa `requestAnimationFrame` (app.js:1025-1034) — PASS
- `_dismissToast()` usa `setTimeout(remove, 280)` apos `.toast-leaving` (app.js:140-142) — PASS
- `_atualizarTabIndicator()` chamada no init (setTimeout 50ms, app.js:2424) e em mudancas de tab (app.js:2416) — PASS
- Animacoes existentes (fadeInUp, slideIn, modalEnter, staggerReveal, pulseRing, shimmerSlide) presentes — PASS
- Variaveis CSS (--bg-base, --accent, etc.) nao alteradas — PASS
- Regra operador `\n` / IA `<br>` nao confundida no JS de copiar bubble (app.js:858, 945) — PASS
- SSE `sse:connection_status` dispatched em sse.js:8 — PASS
- Handler `sse:connection_status` em app.js:2401 atualiza `#conn-status[data-state]` — PASS

---

## Sumario

| Severidade | Count |
|---|---|
| P0 CRITICAL | 1 |
| P1 WARNING | 4 |
| P2 INFO | 1 |
| PASS | 20+ |

Bloqueador principal: P0 bloco CSS duplicado (linhas 1154-1168) quebra animacao de saida do toast.
P1s sao melhorias de qualidade sem quebrar funcionalidade core.
