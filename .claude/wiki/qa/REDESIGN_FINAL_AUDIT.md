# Redesign Final Audit

**Branch:** ui/redesign-stitch
**Data:** 2026-05-28
**Auditor:** qa-agent
**Escopo:** Fases 1-7 do redesign (commits be85c9f → 9467e66)

---

## Sumário executivo

O redesign das Fases 1-7 está **aprovado com ressalvas** — não há P0. Todos os objetivos das 7 fases foram entregues: tokens unificados, paleta cool-toned #15161A/#4E7AE7, tipografia Plus Jakarta Sans + Geist Mono, bolhas redesenhadas, info panel rico, motion polish e settings refatorado. Três P1s de contraste WCAG e um P1 de divergência visual de mockup requerem fix antes do merge em `main`. pytest 47/47 PASS, Python compila limpo, JS sem erros de sintaxe.

---

## Findings

### P0 (bloqueante)

Nenhum.

---

### P1 (bug visual / WCAG)

**P1-01** — `static/admin/login.html:152-168` e `static/admin/index.html:877-889`
Botão primário (`login-btn` / `#send-btn`) usa `background: var(--accent)` = `#4E7AE7` com texto `color: white`. Contraste branco/#4E7AE7 = **3.99:1 — abaixo do mínimo WCAG AA (4.5:1)**. Para texto normal (14px/medium) o mínimo é 4.5:1; para large text (18px+ ou 14px bold) seria 3.0:1 — o botão "Entrar" (14px medium) e "Enviar" (ícone sem texto legível, ok) falham para texto interno.
Fix: escurecer accent do botão para `#3B6BDF` em dark mode (já usado como `accent-hover`), ou usar `font-weight: 700` para classificar como "large text bold" e atingir 3.0:1. Dono: frontend-agent.

**P1-02** — `static/admin/index.html:131-135` (light mode tokens)
No tema claro, `--text-muted: #94a3b8` sobre `--bg-card: #f1f5f9` = **2.34:1 — falha WCAG AA e mesmo WCAG AAA**. Afeta: `.stat-label`, `.metric-label`, timestamps de bolha, placeholders de nota, `.bolha-ts` em tema claro. Nenhum texto crítico (são labels secundários / timestamps), mas viola WCAG 1.4.3 para qualquer texto menor que 18pt.
Fix: elevar `--text-muted` no light theme de `#94a3b8` para `#64748b` (contraste ~4.6:1 sobre `#f1f5f9`). Dono: frontend-agent.

**P1-03** — `static/admin/index.html:2317-2337` (thread header)
O mockup `dashboard-v3-a32b.png` mostra badge "VOCÊ ESTÁ ATENDENDO" em verde (similar ao `badge-humano` accent azul do spec). O CSS define `#thread-status-badge.badge-humano` (linha 733-737) com estilos corretos, **mas o elemento `id="thread-status-badge"` não existe no HTML** — só existe `id="thread-status"`. O JS escreve `textContent` em `#thread-status`, que por sua vez tem o CSS de pill via `:not(:empty)` (linha 761-785). Resultado: o pill funciona mas **sempre usa o estilo "aguardando" (warning/yellow)** — não há variação de cor por estado (bot=verde, humano=azul accent). Diverge visualmente do mockup que mostra tint verde/accent conforme estado.
Fix: ou renomear `#thread-status` para `#thread-status-badge` no HTML e no JS, ou adicionar lógica no JS que troque classes `.badge-bot`/`.badge-humano`/`.badge-aguardando` em `#thread-status`. Dono: frontend-agent.

**P1-04** — `static/admin/index.html:2198-2207` vs mockup `dashboard-v3-a32b.png`
O mockup v3 mostra 3 sub-tabs na conv list: **"Todos / Não-lidos / Aguardando"**. A implementação tem **4 tabs: "Todos / Aguardando / Meus / Bot"**. Divergência de spec — "Não-lidos" ausente, "Meus" e "Bot" são adições não previstas no mockup v3 mas que existiam no design anterior. Esta pode ser uma decisão de produto deliberada (funcionalidade mais rica), mas não está documentada como desvio aprovado.
Fix: confirmar com PO/lead se "Meus" e "Bot" são features aprovadas post-mockup. Se sim, registrar ADR/BR. Se não, retirar as tabs excedentes. Dono: product-owner-agent / frontend-agent.

---

### P2 (polish)

**P2-01** — `static/admin/settings.html:931-932, 1238, 1266-1267`
O valor padrão do color picker de etiquetas (labels) usa `#2481cc` — a cor de accent **antiga** pré-redesign. Deveria usar `#4E7AE7` (novo accent). Impacto cosmético: toda nova etiqueta criada nasce com a cor velha por padrão.
Fix: substituir os 4 ocorrências de `#2481cc` por `#4E7AE7` em settings.html (linhas 931, 932, 1238, 1266, 1267). Dono: frontend-agent.

**P2-02** — `static/admin/login.html:409-410`
O mockup `login-stitch.png` mostra "Esqueceu?" como link inline ao lado do label "SENHA". A implementação não tem esse link. O footer diz "Não tem conta? Contate o gerente." que está correto, mas o link de recuperação de senha do mockup está ausente. Dado que não há endpoint de recuperação de senha, a ausência pode ser intencional — mas cria divergência visual com o mockup.
Fix: ou implementar o link "Esqueceu?" como texto estático linkando para instrução "Contate o gerente.", ou confirmar com PO que foi removido intencionalmente. Dono: product-owner-agent / frontend-agent.

**P2-03** — `static/admin/index.html:893-911` (AI Assist pill)
A pill `ai-assist-pill` tem `cursor: not-allowed; opacity: 0.7` e `disabled` no botão — correto. Porém, a regra CSS `.ai-assist-pill:not(:disabled):hover { opacity: 1; }` é tecnicamente inalcançável (botão tem `disabled` sempre). Inofensivo, mas CSS morto.
Fix: remover a regra hover do AI Assist pill. Dono: frontend-agent.

**P2-04** — `static/admin/index.html:2094-2095` (Modais de index.html — padrão de visibilidade)
Os modais `#modal-snooze`, `#modal-shortcuts`, `#modal-confirm`, `#modal-input-text`, `#cmd-palette` usam `class="hidden"` (Tailwind) + `class="flex"` via inline style, enquanto o check list pedia `.modal-overlay + .visible`. Esses modais funcionam corretamente porque o JS alterna `hidden` via `classList.remove/add('hidden')` e o Tailwind CDN está carregado. O padrão `.modal-overlay + .visible` foi aplicado corretamente **apenas em settings.html**. Há inconsistência entre os dois arquivos.
Fix: migrar os modais de index.html para `.modal-overlay`/`.visible` na próxima sprint de refatoração, ou aceitar o padrão Tailwind-`hidden` como padrão oficial para index.html e documentar no ADR-008. Dono: frontend-agent / architect-agent.

---

### P3 (nice-to-have)

**P3-01** — `static/admin/index.html:1202-1209` (`#info-panel-backdrop`)
O CSS define `.show` para `display: block` mas o comentário inline diz "inset 0 0 0 360px" (cobre apenas a área de chat). A implementação usa `inset: 0 0 0 0` (cobre tudo), contradizendo o comentário do spec. Efeito prático: o backdrop cobre a sidebar quando o info-panel abre em desktop, o que pode ser indesejado.
Fix: corrigir `inset` para `0 0 0 360px` para que o backdrop só cubra a área de chat e não a sidebar. Dono: frontend-agent.

**P3-02** — `static/admin/index.html:759-785` (`#thread-status:not(:empty)`)
O CSS aplica o estilo de pill em `#thread-status:not(:empty)` com estilo fixo "aguardando/warning" sem mecanismo de override por classe. Há CSS definido para `#thread-status-badge.badge-bot` / `.badge-humano` (linhas 728-737) que nunca é aplicado por nenhum elemento HTML existente. CSS órfão.
Fix: ou remover o bloco CSS `#thread-status-badge.*` (linhas 709-745) como código morto, ou implementar a troca de classes no JS (ver P1-03). Dono: frontend-agent.

**P3-03** — `static/admin/index.html:1586` (empty state mobile)
`@media (max-width: 1023px) { #chat-empty-state { display: none !important; } }` conflita com `@media (max-width: 1023px) { #empty-state { display: flex !important; } }` na mesma media query (linhas 1585-1586). Os dois estados de empty-state existem em paralelo — o `#chat-empty-state` animado (Task 1.5) e o `#empty-state` legado. Em mobile, o animado é forçado a ocultar e o legado a mostrar. O comportamento está correto, mas o HTML mantém dois elementos sobrepostos.
Fix: considerar remover `#chat-empty-state` ou unificar os dois em um único elemento. Dono: frontend-agent.

**P3-04** — `static/admin/settings.html` (ausência de logo Bolshoi na topbar)
A página de settings tem topbar com título "Configurações" e botão "Voltar". Mockup implícito de settings (ausente, derivado do padrão da app) sugeriria logo Bolshoi na topbar, mas não há mockup explícito de settings. Puramente cosmético — se a branding consistente for exigida.
Fix: adicionar logo Bolshoi 28px na topbar do settings ao lado do título. Dono: frontend-agent.

---

## Testes executados

### pytest
- **47/47 PASS** — `pytest -x -q --tb=short` rodou sem falhas.

### Compilação Python
- Todos os arquivos `.py` alterados compilam sem erros: `api/webhook.py`, `api/admin.py`, `services/ai_service.py`, `services/whatsapp.py`, `db/models.py`, `db/database.py`, `core/prompts.py`, `core/respostas_canonicas.py`, `main.py`.

### Sintaxe JavaScript
- `node --check` em `js/app.js`, `js/api.js`, `js/sse.js` — todos **sem erros de sintaxe**.

### Contraste WCAG 4.5:1
- PASS: text-primary (#E5E7EB) sobre bg-surface dark — 13.59:1
- PASS: text-secondary (#9CA3AF) sobre bg-surface dark — 6.63:1
- PASS: warning-text (#FBBF24) sobre bg-surface dark — 10.08:1
- PASS: bubble-bot (#ECFDF5 sobre #064E3B) — 9.23:1
- PASS: light text-primary (#0f172a) sobre white — 17.85:1
- PASS: light text-secondary (#475569) sobre white — 7.58:1
- FAIL P1-01: white sobre accent #4E7AE7 — **3.99:1** (botão primário dark mode, texto 14px)
- FAIL P1-02: light text-muted #94a3b8 sobre bg-card #f1f5f9 — **2.34:1**

### prefers-reduced-motion
- `static/admin/index.html`: PRESENTE — linha 1433, cobertura universal via `* { animation-duration: 0.01ms }` + desligamento explícito de 10 classes decorativas.
- `static/admin/login.html`: PRESENTE — linha 301, cobertura correta.
- `static/admin/settings.html`: PRESENTE — linha 122, cobertura correta.

### Keyboard nav / focus-visible
- Todos os 3 arquivos definem `*:focus-visible { outline: 2px solid var(--accent); outline-offset: 2px }` com transição de `outline-offset`. PASS.

### Regra `<br>` (IA) vs `\n` (operador)
- `_normalizar_texto_envio` em `api/webhook.py:871-890` intacta — converte `<br>` para `\n` antes do envio. Operadores em `api/admin.py` enviam `\n` diretamente. Regra **preservada**.

### Logo Bolshoi PNG
- Arquivo `static/admin/img/logo-bolshoi.png` existe (16.1K).
- Referenciado em `index.html:2125` (sidebar) e `login.html:324` (painel esquerdo). PASS.
- `settings.html` **não referencia o logo** — cosmético (P3-04).

### Token consistency (--font-body, --font-heading, --font-mono)
- Todos 3 arquivos definem os 3 tokens de fonte. PASS.

### Paleta unificada (#15161A bg-base, #4E7AE7 accent)
- `index.html`: `--bg-base: #15161A`, `--accent: #4E7AE7`. PASS.
- `login.html`: `--bg-base: #15161A`, `--accent: #4E7AE7`. PASS.
- `settings.html`: `--bg-base: #15161A`, `--accent: #4E7AE7`. PASS.
- Resquícios de `#2481cc` em `settings.html` apenas como default value do color-picker de etiquetas (P2-01).

### AI Assist pill
- `#ai-assist-btn` tem atributo `disabled` no HTML e `cursor: not-allowed` no CSS. Não executa nenhuma ação. PASS.

### System pills centralizadas
- `.msg-system-pill`, `.bolha-sistema`, `.msg-evento` com `align-self: center`, `margin: 12px auto`. PASS.
- Compatibilidade retroativa com `.separadorEvento` via seletor CSS `#messages-area > .flex.items-center.gap-3.my-2 > span.text-xs.italic`. PASS.

### Settings modais
- Padrão `.modal-overlay` + `.visible` implementado corretamente em `settings.html:148-160`. PASS.

### Light mode
- Toggle de tema presente em `index.html:13-16` (pre-render via localStorage).
- CSS light mode em `index.html:102-155`, `settings.html:55-95`. PASS.

### Console errors esperáveis
- Nenhum `console.error` estático detectado — erros são apenas em catch blocks (comportamento correto).
- Fallbacks de `prompt()`/`confirm()` nativos existem apenas em safety branches quando elemento DOM ausente (linhas 206 e 328 do app.js) — não disparam em uso normal.

---

## Conclusão

O redesign das Fases 1-7 está funcionalmente correto e visualmente alinhado com os mockups em ~90% dos pontos de check. Não há P0. Os 4 P1s são corrigíveis em 1-2h de trabalho (contraste de cores e thread-status-badge) sem breaking changes. Recomendação: **segurar para fix dos P1-01, P1-02, P1-03 antes do merge em main**; P1-04 (tabs extras) requer decisão de PO. Os P2/P3 podem seguir em sprint dedicado de polish pós-merge.
