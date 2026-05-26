# Release Visual 1.0 — 2026-05-22

## Sprint Visual 1.0 — Redesign Drástico do Dashboard

Validação arquitetural: **14/14 PASS** (12/14 na primeira passagem; V1 e V2 corrigidos na segunda rodada).

---

## Goals Implementados

| Goal | Descrição | Status |
|---|---|---|
| **V1** | Design tokens CSS expandidos (espaçamento, tipografia, radius, sombras, duração/easing) em `index.html`, `login.html`, `settings.html` | PASS |
| **V2** | Logo placeholder com SVG navalha + texto "Bolshoi" em 3 locais: sidebar, login, settings | PASS |
| **V3** | Sidebar: tooltips via `[data-tooltip]::after`, `.presence-dot` com variantes online/away/offline, borda ativa `3px var(--accent)` | PASS |
| **V4** | Conv-cards: `.avatar-status-badge`, `tempoRelativo()`, `.waiting-badge`, animação `fadeSlideIn` em novos cards | PASS |
| **V5** | Message bubbles: `.bolha-base` 14px leading-relaxed, `.bolha-sender-badge`, `.bolha-timestamp`, `.bolha-falha` com borda vermelha | PASS |
| **V6** | Thread header: `.header-btn-group`, `.header-action-btn`, `data-tooltip` nos 7 botões de ação | PASS |
| **V7** | Composer: `_autoResizeComposer()` (max 120px), `#char-counter` com warn >80% e danger >95% | PASS |
| **V8** | Info panel: `.info-section` accordion via `_initInfoAccordion()`, `.nota-card`, `.nota-add-fab`, `.stats-grid` | PASS |
| **V9** | 7 keyframes globais: `fadeSlideIn`, `msgSlideLeft`, `msgSlideRight`, `skeletonPulse`, `spinOnce`, `popIn`, `slideDown`, `backdropIn` | PASS |
| **V10** | Skeleton loading: `renderSkeletonList(container, count=5)` em `app.js`, `.skeleton-card` CSS, integrado em `carregarConversas(showSkeleton=true)` | PASS |
| **V11** | Empty states SVG: `.empty-state`, `renderEmptyConvList()` com SVG inline, `#empty-state` no thread area | PASS |
| **V12** | Login redesign: split layout (esq=branding 42%, dir=form 58%), inputs com SVG inline, `fadeSlideIn` no `.login-card`, `@media` mobile empilhado | PASS |
| **V13** | Sistema `.btn` unificado: hover `brightness+translateY(-1px)`, active `scale(0.96)`, focus-visible outline, disabled `opacity:0.38`, variantes primary/ghost/danger/success | PASS |
| **V14** | Mobile: `.drawer-backdrop`, `.hamburger-btn` com animação →X, `@media (max-width:767px)` drawer layout, 44px touch targets em bottom nav | PASS |

---

## Arquivos Modificados

| Arquivo | Mudanças |
|---|---|
| `static/admin/index.html` | V1-V14 (CSS tokens, logo, sidebar, cards, bubbles, header, composer, info-panel, animações, skeletons, empty states, btn system, mobile) |
| `static/admin/js/app.js` | V4 (`tempoRelativo`), V7 (`_autoResizeComposer`), V8 (`_initInfoAccordion`), V10 (`renderSkeletonList`), V11 (`renderEmptyConvList`), V14 (drawer/backdrop JS) |
| `static/admin/login.html` | V1 (tokens completos), V2 (logo+branding), V12 (split layout redesign completo) |
| `static/admin/settings.html` | V1 (tokens + `--ease-in-out`), V2 (logo placeholder + texto "Bolshoi") |

---

## Paleta Dark Adotada

```
--bg-base:    #0d1117   (fundo mais escuro)
--bg-surface: #161b22   (panels/sidebar)
--bg-card:    #1c2128   (cards)
--accent:     #2481cc   (ações primárias)
--success:    #238636 / text #3fb950
--danger:     #6e1c1c / text #f85149
--warning:    #9e6a03 / text #d29922
```

Referência visual: GitHub dark mode + WhatsApp Web layout + Linear micro-animações.

---

## Compatibilidade Preservada

- Todos os event listeners (SSE, DOM) preservados intactos
- Todas as chamadas de API não alteradas
- JWT localStorage flow preservado
- Regra `\n` operador / `<br>` IA não alterada
- Nenhuma lib externa nova introduzida

---

## Logo Placeholder

Para substituir pelo logo real da Barbearia Bolshoi, troque os 3 elementos:
- **Sidebar** (`index.html` linha ~730): substituir `<svg>` interno por `<img src="/static/admin/logo.svg" alt="Bolshoi" ...>`
- **Login** (`login.html` linha ~238): substituir bloco `#logo-placeholder-login`
- **Settings** (`settings.html` linha ~90): substituir bloco `#logo-placeholder-settings`

---

## Migrations

Nenhuma migration de schema necessária nesta release. Mudanças puramente de frontend.

---

## Resumo Executivo

O dashboard de atendentes recebeu uma reformulação visual completa. A interface adota agora uma paleta dark inspirada no GitHub com hierarquia visual clara, animações fluídas em todos os elementos interativos, e estado de carregamento skeleton que substitui os textos "Carregando…" anteriores. A tela de login foi completamente redesenhada com layout split (branding à esquerda, formulário à direita). Todos os botões possuem estados visuais completos (hover, active, disabled, focus). A interface é responsiva com drawer animado e navegação bottom em mobile.
