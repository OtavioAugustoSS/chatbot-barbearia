# QA Audit — Redesign Dashboard Fases 0-2

> **VERIFICAÇÃO FINAL (pós RD-7) — 2026-05-25 (3ª passada).** **APROVADO: P0=0 · P1=0.** Resultado na seção "## VERIFICAÇÃO FINAL" logo abaixo. Passadas anteriores (RD-6 e 1ª) preservadas para rastreabilidade.

---

## VERIFICAÇÃO FINAL (pós RD-7)

**Auditor:** qa-agent · **Branch:** redesign/admin-interface · **Método:** estático (sem Playwright — render/console runtime ficam com o usuário). Comparado contra `mockup-spec.md` + `mockup-reference.css`. `node --check` OK nos 3 JS.

### Contagem: **P0 = 0 · P1 = 0 · P2 = 1 (backlog)** → **APROVADO**

O loop FECHA (P0=0 ∧ P1=0). RD-7 resolveu o P1-R1 e os P2 prioritários. Resta só P2-R4 (indigo residual fora do escopo do redesign) como backlog não-bloqueante.

### Verificação das correções RD-7
| Item | Antes | Agora | Evidência |
|---|---|---|---|
| **P1-R1** metric cards | sem barra, 18px, label lowercase | **FECHADO** — fiel ao mockup | `index.html:953-985`: bg #233138, `::before` barra 3px com `--metric-color` (aguardando #ef4858 / atendendo #00a884 / bot #2481cc), value 22px/700/-0.02em, label uppercase + letter-spacing 0.05em. Container grid repeat(3) gap 6px (`:1070`). = `mockup-reference.css:92-117`. |
| **P2-R1** label do bot | chip "IA" + "Bot" | **FECHADO** | `app.js:806-818`: `_ICO_BOT` SVG + " Bolshoi Bot" (sem chip); cliente/humano com `_ICO_USER` inline. Ticks SVG upados pro path exato `check` do mockup (`20 6 9 17 4 12`), 1-tick (backend sem "lido"). |
| **P2-R2** avatar operador | roxo #6c5ce7 | **FECHADO** | `index.html:1030`: 40px `linear-gradient(135deg,#2481cc,#1a5a8f)`. |
| **P2-R3** identidade no header | estava no footer | **FECHADO** | `index.html:1027-1053`: `.sidebar-header` no topo com avatar 40px + nome 15px/600 + papel "Atendente · Bolshoi" 12px + ações (menções/config). Search-row também reconstruída pro spec (`:1055-1067`). |

### Regras rígidas (re-verificadas — todas OK)
- Vanilla JS: sem framework; RD confinado a static/admin.
- `\n` vs `<br>`: `app.js:826` escapa + `\n`→`<br>` (XSS-safe).
- Contrato/SSE: `sse.js`/`api.js` intactos; `totais_por_estado` consumido pelos metric cards existe em `admin.py:292-382`.
- Migrations 0008-0011 presentes. `node --check` OK em app.js/api.js/sse.js. Nenhum `.py` nas tasks RD.

### Pendência (backlog, NÃO bloqueia)
- **P2-R4** — indigo `#6366f1` residual em `settings.html:110,278-279,488,520,545-546` e defaults de cor de label em `app.js:453,461,1372` (+ `#6c5ce7` no array `_CORES:65`). Fora do escopo do redesign do dashboard (settings.html é outra página; os defaults são cor de etiqueta). Alinhar à paleta quando houver folga.

### Veredito
**APROVADO.** Dashboard fiel ao mockup nos 5 eixos auditados (layout 2-col, identidade+métricas, bolhas cauda+grupo+ticks, drawer slide-over, label+cores) com regras rígidas intactas. **Caveat permanente:** sem Playwright aqui — render visual e console runtime no browser só o usuário confirma (servidor `MODO_OPERACAO=hibrido` + rodar migration 0008 no MySQL para o bug das conversas legadas).

---

## (HISTÓRICO) RE-AUDITORIA RD-6 (pós-correções, 2ª passada)

**Auditor:** qa-agent · **Branch:** redesign/admin-interface · **Método:** estático (sem Playwright — render/console runtime ficam com o usuário). Comparado contra `.claude/wiki/qa/mockup-spec.md` + `mockup-reference.css`. `node --check` OK nos 3 JS.

### Contagem: **P0 = 0 · P1 = 1 · P2 = 4**

O loop NÃO fecha ainda (exige P1=0). O único P1 é estilo dos cards de métrica divergindo do mockup; os P2 são polish. Todas as 5 correções estruturais (RD-1..RD-5) foram aplicadas com sucesso e as regras rígidas seguem intactas.

### Status das correções RD-1..RD-5
| Task | Resultado | Evidência |
|---|---|---|
| RD-1 layout 2-col | OK | `index.html:925` body `grid-template-columns: 360px 1fr`; icon-rail removido (0 refs); nav movida pro `#sidebar-footer:1051`. Responsivo coerente (`:204` colapsa p/ 1fr + conv-panel drawer <1024px). |
| RD-2 identidade + métricas | OK funcional (1 P1 + 2 P2) | `.metric-card` x3 (`:982-994`) com `#metric-val-*` ligados a `totais_por_estado` em `atualizarBadges` (`app.js:582-588`); contrato confirmado em `admin.py:292-295,382`. Identidade do operador em `#sidebar-footer` (`:1055-1057`, `app.js:2169-2175`). |
| RD-3 bolhas cauda+grupo+ticks | OK | Caudas clip-path exatas (`:869-885`), grouping 5-min com classes `grouped`/`grouped-row` (`app.js:851-866`,`:888-891`), ticks SVG `_SVG_TICK_OK`/`_FAIL` (`app.js:809-811`), branco na bolha humana (`:895`). |
| RD-4 info drawer slide-over | OK | `#info-panel:1235` `position:absolute; right:0; width:380px; transform:translateX(100%)`; toggle `abrir/fecharInfoPanel` translateX(0)/(100%) (`app.js:1899-1909`). |
| RD-5 label + indigo | OK (CSS) / parcial (JS — vira P2) | Indigo-alvo do status-filter ZERADO. `.bolha-label` CSS agora = mockup `.bubble-author` (11.5px/600 não-uppercase, inline-flex gap, cores #e9b884/#7fe3c4/#d6e8fa em `:183-195`). Pendência menor no JS (chip "IA") → P2-R1. |

### P0 — Quebrado / erro de runtime
Nenhum (estaticamente). `node --check` OK em app.js/api.js/sse.js. **Ressalva mantida:** erros de runtime/console no browser não verificados — exigem o usuário rodar o servidor híbrido.

### P1 — Diverge do design (mockup)

**P1-R1 — Cards de métrica: estilo simplificado vs mockup**
- **Arquivo:** `index.html:897-922` (CSS `.metric-card`)
- **Problema:** Mockup (`mockup-reference.css:92-117`) tem: card bg `--bg-elev-2 #233138`, **barra colorida 3px à esquerda** (`.metric::before`), count **22px/700**, label **uppercase + letter-spacing 0.05em**. Atual: layout coluna centralizada, **sem barra à esquerda**, cor aplicada ao número (não barra), count **18px**, label **10px não-uppercase**, bg `--bg-card`. Reconhecível, mas não fiel (decisão do usuário foi fidelidade).
- **Fix sugerido:** `.metric-card { background: var(--bg-elev-2,#233138); position:relative; overflow:hidden; align-items:flex-start; padding:8px 10px; }` + `::before` barra 3px com cor por id; `.metric-value{font-size:22px;font-weight:700;letter-spacing:-0.02em}`; `.metric-label{text-transform:uppercase;letter-spacing:0.05em;font-size:10.5px}`. Cor na BARRA (não no número): aguardando #ef4858 / atendendo #00a884 / bot #2481cc.
- **Dono:** frontend-agent

### P2 — Polish

**P2-R1 — Label do bot: chip "IA" no JS em vez de ícone inline do mockup**
- **Arquivo:** `app.js:807`
- **Problema:** CSS correto (P1 antigo resolvido), mas markup do bot ainda emite `<span ...>IA</span> Bot`. Mockup (`comp4.jsx:30-31`) = ícone SVG `bot` (size 11, #7fe3c4) + " Bolshoi Bot", sem chip. Cliente/humano também deveriam ter ícone inline.
- **Fix sugerido:** Trocar `labelTxt` do bot por `<svg ...bot...></svg> Bolshoi Bot`; adicionar ícone `user` ao humano. Paths em `mockup-spec.md §6`.
- **Dono:** frontend-agent

**P2-R2 — Avatar do operador não usa o gradiente azul do mockup**
- **Arquivo:** `index.html:1057` (`background:#6c5ce7` roxo antigo); `app.js:2171` só seta texto/title.
- **Problema:** Mockup `.me-avatar` (`mockup-reference.css:69-75`) = `linear-gradient(135deg,#2481cc,#1a5a8f)`.
- **Fix sugerido:** Trocar inline para o gradiente.
- **Dono:** frontend-agent

**P2-R3 — Identidade do operador no footer, não no header da sidebar**
- **Arquivo:** `index.html:1051-1058` (footer) vs header `:966-979`.
- **Problema:** Mockup põe avatar+nome+papel no topo da sidebar (`comp3.jsx:64-77`); o atual pôs no rodapé. Funcionalmente equivalente; diverge da composição. Aceitável se lead/usuário ok.
- **Fix sugerido:** Mover identidade pro header se quiser fidelidade plena; SSE fica no footer.
- **Dono:** frontend-agent (após ok)

**P2-R4 — Indigo `#6366f1` residual fora do escopo RD**
- **Arquivo:** `settings.html:110,278-279,488,520,545-546`; `app.js:453,461,1372` (defaults de cor de label); `_CORES:65`.
- **Problema:** Defaults de cor de etiqueta + settings.html (fora do escopo do redesign do dashboard). Não é o accent-leak alvo (esse foi corrigido). Cosmético.
- **Fix sugerido:** Backlog — alinhar à paleta nova quando houver folga.
- **Dono:** frontend-agent (backlog)

### Regras rígidas (re-verificadas — todas OK)
| Regra | Status | Evidência |
|---|---|---|
| Vanilla JS (sem React/Vue) | OK | Nenhum framework; RD confinado a static/admin (HTML/CSS/JS puro). |
| Operador `\n` vs IA `<br>` | OK | `app.js:815` escapa + `\n`→`<br>` (XSS-safe); reconversões intactas. |
| Contrato dados/SSE | OK | `sse.js` inalterado; `api.js` mantém endpoints/shapes; `totais_por_estado` existe em `admin.py`. |
| Redesign frontend-only | OK | RD-1..RD-5 só em `static/admin/`. (`.py` modificados na working tree são backend pré-existente da branch, não das tasks RD.) |
| Migrations existem | OK | 0008/0009/0010/0011 com conteúdo válido. |
| `node --check` nos JS | OK | app.js/api.js/sse.js sem erro de sintaxe. |

### Recomendação ao lead
Falta só **P1-R1** (estilo dos metric cards) pra fechar o loop (P0=0 ∧ P1=0) — fix de CSS pequeno e especificado acima. P2-R1/P2-R2 são baratos e elevam fidelidade; recomendo agrupar com o P1-R1 numa rodada só. Após aplicar, faço a verificação final. **Continua valendo:** render/console runtime só o usuário confirma no browser (sem Playwright aqui).

---

## (HISTÓRICO) 1ª passada de auditoria

**Auditor:** qa-agent
**Data:** 2026-05-25
**Branch:** redesign/admin-interface
**Escopo:** Fidelidade visual ao mockup `Bolshoi_Atendente_standalone_.html` + ausência de erros + regras rígidas.
**Método:** Playwright MCP **não disponível** no ambiente — sem render real do browser. Auditoria feita por análise estática: decodifiquei o bundle React do mockup (manifest base64+gzip → 7 componentes JSX + CSS de 23KB, a fonte autoritativa do design) e comparei contra `static/admin/index.html` + `js/app.js` + `js/sse.js` + `js/api.js`. `node --check` rodado nos 3 JS. **Render visual e console runtime NÃO foram verificados** — isso exige o usuário abrir o servidor no browser.

---

## Veredito resumido

A camada de **dados/funcional está sólida** (Fase 0 bem resolvida, contrato SSE intacto, `\n`/`<br>` correto, migrations existem, JS sem erro de sintaxe). Porém a **fidelidade visual ao mockup diverge de forma significativa**: o frontend-agent **re-skinou a estrutura existente** (layout Chatwoot de 4 zonas) com a paleta do mockup, em vez de **reconstruir a estrutura do mockup** (2 colunas + drawer slide-over, com header de sidebar rico em métricas). As cores batem; a arquitetura de layout e vários elementos-assinatura não.

**Importante — divergência no próprio plano:** o plano (`happy-crunching-balloon.md`) e o briefing falam em "layout 3 colunas (conv-panel 320 / chat / info 280)". O **mockup real NÃO é 3 colunas estáticas** — é um grid de **2 colunas** (`grid-template-columns: 360px 1fr`) com o painel de info sendo um **drawer slide-over absoluto** (380px, `transform: translateX(100%)`), acionado por clique no cliente. Não há icon-rail de navegação no mockup. O dashboard atual implementou 4 zonas estáticas (icon-rail 64px + conv 320 + chat + info 280). Quem define o alvo final (mockup literal vs. o layout atual) é decisão do usuário — sinalizado como **P1 que precisa de ruling**.

Contagem: **P0 = 0 · P1 = 7 · P2 = 6**

---

## P0 — Quebrado / erro de runtime

Nenhum erro estrutural detectável estaticamente. `node --check` passou em `app.js`, `api.js`, `sse.js`. **Ressalva:** erros de runtime no browser (ex.: exceção em `renderConvList`, evento SSE com shape inesperado, falha de auth real) **não foram verificados** — exigem abrir o dashboard no browser com o servidor `MODO_OPERACAO=hibrido` rodando e inspecionar o console. Recomendo que o usuário faça esse passo antes de fechar a auditoria.

---

## P1 — Diverge do design (mockup)

### P1-1 — Layout não reproduz a estrutura do mockup (decisão de produto necessária)
- **Arquivo:** `static/admin/index.html:932-1243` (body: `#icon-sidebar` 64px · `#conv-panel` 320 · `#chat-panel` · `#info-panel` 280)
- **Problema:** Mockup = grid 2 colunas `360px 1fr` (`mockup CSS .app:42-50`) + drawer slide-over (`.drawer:632-644`). Atual = 4 zonas estáticas com icon-rail (que não existe no mockup) e info-panel estático (no mockup é slide-over).
- **Fix sugerido:** Decidir com o usuário: (a) reconstruir fiel ao mockup (remover icon-rail, fundir nav no header da sidebar, info vira drawer), ou (b) manter o layout atual como evolução intencional. Se (a), é trabalho grande de markup.
- **Dono:** frontend-agent (após ruling do usuário/PO)

### P1-2 — Header da sidebar sem identidade do operador
- **Arquivo:** `static/admin/index.html:1018-1032` (header = só título "Conversas" + busca)
- **Problema:** Mockup tem header com avatar do operador (gradiente azul, iniciais), nome ("Diego Martins"), papel ("Atendente · Bolshoi") e botão sair (`comp3.jsx:64-77`, CSS `.me`/`.me-avatar`/`.me-name`/`.me-role`:68-79).
- **Fix sugerido:** Adicionar bloco de identidade do operador no topo da sidebar usando `state.eu`. Hoje o avatar do operador está escondido no rodapé do icon-rail (`#my-avatar`:987).
- **Dono:** frontend-agent

### P1-3 — Ausência dos 3 cards de métricas
- **Arquivo:** `static/admin/index.html` (conv-panel não tem bloco de métricas)
- **Problema:** Mockup tem 3 cards no topo da sidebar: Aguardando (vermelho `#ef4858`), Atendendo (verde `#00a884`), Com bot (azul `#2481cc`), com contagem grande (22px/700) e barra colorida à esquerda (`comp3.jsx:79-83`, CSS `.metrics`/`.metric`/`.metric-count`:92-117). O atual mostra contagens só como pequenos badges nas filter-tabs.
- **Fix sugerido:** Adicionar `.metrics` grid 3-col no topo da sidebar, alimentado por `data.totais_por_estado`.
- **Dono:** frontend-agent

### P1-4 — Bolhas sem "cauda" (tail) WhatsApp
- **Arquivo:** `static/admin/index.html:430-449` (`.bolha-base` — sem `::before` de tail) · `js/app.js:806-814` (markup da bolha)
- **Problema:** Mockup tem cauda triangular na primeira bolha de cada grupo (`mockup CSS [data-tails="1"] .bubble::before`:429-445) e agrupa bolhas do mesmo remetente. Atual usa cantos uniformemente arredondados, sem tail e sem agrupamento visual.
- **Fix sugerido:** Adicionar `::before` clip-path nas bolhas + lógica de "primeira do grupo". Médio esforço.
- **Dono:** frontend-agent

### P1-5 — Delivery ticks como texto, não ícone SVG
- **Arquivo:** `js/app.js:801,811` (`entregueIcon = ' ⚠'/' ✓'`)
- **Problema:** Mockup usa ícone SVG check/check-double com cor de "lido" (`--tick-read: #54a4d4`) — `comp4.jsx:4-13` (`DeliveryTicks`). Atual usa caractere ✓/⚠ monocromático, sem distinção entregue vs. lido.
- **Fix sugerido:** Trocar por SVG single/double-check; aplicar `--tick-read` para lido. Hoje o backend não expõe "lido" — pode ficar só entregue/não-entregue.
- **Dono:** frontend-agent (backend-agent se quiser status "lido" real)

### P1-6 — Label do remetente: estilo diverge
- **Arquivo:** `static/admin/index.html:441-448` (`.bolha-sender-badge` UPPERCASE + letter-spacing) e `js/app.js:799` usa `.bolha-label`
- **Problema:** Mockup: `.bubble-author` é 11.5px/600, **não** uppercase, com ícone inline (bot/user) e gap (`comp4.jsx:30-31,45-46`, CSS `.bubble-author`:465-474). Há duas convenções no atual (`.bolha-label` vs `.bolha-sender-badge` UPPERCASE) — inconsistência interna. O bot no atual usa um chip "IA" custom (`app.js:799`) que não existe no mockup (mockup usa só ícone + "Bolshoi Bot").
- **Fix sugerido:** Unificar para o estilo `.bubble-author` do mockup (não-caps, ícone inline). Remover o chip "IA" ou alinhá-lo ao mockup.
- **Dono:** frontend-agent

### P1-7 — Drawer de perfil do cliente não corresponde ao do mockup
- **Arquivo:** `static/admin/index.html:1243+` (`#info-panel` estático 280px)
- **Problema:** Mockup tem drawer rico (`comp5.jsx` + CSS `.drawer*`:620-779): hero com avatar 120px, telefone, 3 botões de ação rápida, seções de stats (grid 2-col), tags, notas (amarelo `#ffd54f`), histórico com dots coloridos. Atual é painel estático lateral mais simples.
- **Fix sugerido:** Avaliar com PO se quer o drawer completo do mockup. Depende do ruling de P1-1.
- **Dono:** frontend-agent (após ruling)

---

## P2 — Polish

### P2-1 — Vazamento da cor indigo antiga (pré-redesign)
- **Arquivo:** `static/admin/index.html:1058` (`background: rgba(99, 102, 241, 0.15)`) e `js/app.js:728` (mesmo valor)
- **Problema:** `#6366f1` (indigo) é o accent do tema antigo. O accent novo é `#2481cc` (azul WhatsApp). O status-filter ativo usa o azul errado.
- **Fix sugerido:** Trocar por `var(--accent-subtle)` em ambos os pontos.
- **Dono:** frontend-agent

### P2-2 — Tailwind CDN como dependência de runtime
- **Arquivo:** `static/admin/index.html:7` (`<script src="https://cdn.tailwindcss.com">`)
- **Problema:** O mockup NÃO usa Tailwind — é CSS puro com tokens. O atual depende do compilador JIT do Tailwind via CDN (runtime, rede externa, não cacheável offline). Não viola ADR-007 ao pé da letra (não é React/Vue), mas é um runtime de framework CSS e dependência de CDN externa — vale ruling do architect-agent.
- **Fix sugerido:** Architect decide se mantém (pragmático) ou migra utilitários usados para CSS local. Não-bloqueante.
- **Dono:** architect-agent (ruling) → frontend-agent (se migrar)

### P2-3 — Fonte: Inter vs. system stack do mockup
- **Arquivo:** `static/admin/index.html:8,932` (carrega e usa `'Inter'`)
- **Problema:** Mockup tem default `fontFamily: "system"` → `Segoe UI, "Helvetica Neue", Roboto, system-ui` (`comp6.jsx:11,96`; CSS `--font-stack`:19). Inter é opção, não default. Divergência leve e defensável (Inter é boa escolha), mas não é o default do mockup.
- **Fix sugerido:** Manter Inter (decisão de design ok) ou alinhar ao system stack. Cosmético.
- **Dono:** frontend-agent

### P2-4 — Filter chips: estilo pílula divergente
- **Arquivo:** `static/admin/index.html:289-301,1036-1045` (`.filter-tab` rounded-lg)
- **Problema:** Mockup usa chips totalmente arredondados (`border-radius: 16px`) com fundo `--bg-base` e ativo em `accent 18%` (CSS `.chip`/`.chip-active`:141-154). Atual usa `rounded-lg` (10px) com `.active-tab` em `--bg-card`. Diferença sutil de raio/cor.
- **Fix sugerido:** Ajustar raio para 16px e cor ativa para accent-subtle.
- **Dono:** frontend-agent

### P2-5 — Avatar do operador: tamanho/estilo
- **Arquivo:** `static/admin/index.html:987` (`#my-avatar` 36px, cor fixa `#6c5ce7`)
- **Problema:** Mockup: `.me-avatar` 40px, gradiente `135deg, #2481cc, #1a5a8f` (CSS:69-75). Atual usa roxo fixo `#6c5ce7` (cor do tema antigo) e está no rodapé do icon-rail, não no header.
- **Fix sugerido:** Junto com P1-2, usar gradiente azul do mockup.
- **Dono:** frontend-agent

### P2-6 — Status dot da conversa: posição/animação
- **Arquivo:** `static/admin/index.html:397-405` (`.avatar-status-badge`)
- **Problema:** Mockup: `.status-dot` 12px, bottom/right:1px, borda 2px na cor da sidebar, com `pulse-red` animado no estado waiting (CSS:189-202). Atual tem `.avatar-status-badge` similar mas sem a animação de pulse no avatar (o pulse existe só em outro contexto). Cores semânticas: mockup waiting=`#ef4858`, mine=`#2481cc`, bot=`#00a884`.
- **Fix sugerido:** Alinhar cores e adicionar pulse no dot do avatar em waiting.
- **Dono:** frontend-agent

---

## Validação de regras rígidas

| Regra | Status | Evidência |
|---|---|---|
| Vanilla JS (sem React/Vue) — ADR-007 | OK | Nenhum React/Vue no dashboard. Tailwind CDN é CSS-runtime (ver P2-2, ruling architect). |
| Operador `\n` vs IA `<br>` no render | OK | `app.js:802` escapa e converte `\n`→`<br>` para display; `:861,938` reconvertem `<br>`→`\n` para preview/edição. XSS-safe (escapeHtml antes). |
| Contrato de dados/SSE intacto | OK | `sse.js` dispara `sse:${ev.tipo}` (eventos do contrato preservados); `api.js` mantém todos endpoints `/admin/*` com shapes originais (`getConversasFiltradas` → `data.items`/`totais_por_estado`). |
| Migrations referenciadas existem | OK | `scripts/migrations/`: 0008 (backfill idempotente), 0009 (índice status), 0010 (intencao VARCHAR50), 0011 (reativado_por_timeout) — todas com conteúdo válido. |
| Nenhum `.py` alterado na Fase 0-2 frontend | OK | Mudanças confinadas a `static/admin/`. |
| Bug "conversas não mostram" | RESOLVIDO (defensivo) | Causa raiz = migration 0008 não aplicada (status NULL). FE-0b `app.js:711-746` detecta e faz fallback automático para `status=todas` + toast orientando rodar a 0008. Fix definitivo continua sendo rodar a 0008 no MySQL (ação do usuário). |

---

## Recomendações ao lead (ordem sugerida)

1. **Ruling de produto/arquitetura (bloqueante para P1-1/P1-7):** o alvo é o mockup literal (2-col + drawer, sem icon-rail) ou o layout atual de 4 zonas é evolução aceita? Sem isso, P1-1/P1-7 ficam parados. Envolver PO + architect.
2. **Quick wins independentes de ruling (frontend-agent):** P2-1 (indigo→accent, 2 linhas), P1-3 (métricas), P1-2 (header operador), P1-5 (ticks SVG), P1-6 (label remetente), P2-4/P2-5/P2-6 (polish).
3. **Verificação de runtime no browser (usuário):** abrir o dashboard com servidor híbrido, conferir console por erros, validar fluxo lista→abrir→enviar com SSE ao vivo. P0 só pode ser fechado assim.
4. **P2-2 Tailwind CDN:** ruling do architect (manter vs migrar).

## Limitações desta auditoria
- Sem Playwright/browser: nenhuma verificação de render real, layout computado, ou erros de console em runtime. Tudo acima é análise estática de código vs. o CSS/JSX autoritativo extraído do bundle do mockup.
- Componentes do mockup decodificados em `%TEMP%\mockup_jsx\` (comp0=tweaks scaffold, comp1=icons, comp2=mock data, comp3=sidebar, comp4=thread, comp5=drawer, comp6=app) e CSS em `%TEMP%\mockup_style1.css` (efêmero).
