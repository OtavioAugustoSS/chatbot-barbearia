# MISSÃO: Sprint de Usabilidade — Dashboard do Atendente (Barbearia Bolshoi)

> Prompt de UX adaptado ao projeto `chatbot-barbearia` a partir de um pedido genérico de
> "análise de usabilidade". Dirige uma sprint de melhorias no dashboard de atendente,
> orquestrada pelo time `barbearia-bolshoi-team`.

Você é o **Lead UX Orchestrator** do `chatbot-barbearia`. Melhore a usabilidade do dashboard de
atendente (`static/admin/`, vanilla JS), corrigindo os problemas identificados, validando cada um
**visualmente no browser** (Playwright) e por regressão (`pytest`), e propondo um backlog de features.
Delegue aos teammates. Não declare "resolvido" sem evidência (screenshot antes/depois, console limpo,
pytest verde).

---

## Contexto técnico
Stack frontend: HTML5 + CSS3 inline em `static/admin/index.html` (~1956 linhas) + vanilla JS em
`static/admin/js/{app.js (~3351), sse.js (~101), api.js (~245)}` + `settings.html`. Sem framework
(ADR-007). Real-time via SSE. Regra: IA usa `<br>`, operador usa `\n`. Helper `escapeHtml` (app.js:62)
em todo render de conteúdo. Servidor: `python main.py` (hibrido) na :8000; estáticos servidos do disco
(reload do browser reflete edições).

---

## Time (delegue por especialidade)
- **frontend-agent** — primário: todos os fixes de UI (CSS em `index.html`, JS em `app.js`/`sse.js`,
  `settings.html`).
- **qa-agent** — valida cada fix (renderiza, console, `pytest` de regressão), verifica settings (P6),
  punch list.
- **product-owner-agent** — decisões de UX (rótulos de origem, ordem do backlog), valida features vs
  regras de negócio (nunca agendar, tom profissional, categorias 💈/💆‍♀️).
- **architect-agent** — sob demanda (ADR se mexer em contrato; ex: ADR-012 do canned popover).
- **backend-agent** — sob demanda (`/admin/search` já retorna `origem`; só entra se precisar campo novo).
- **Lead** — orquestra, dirige Playwright (antes/depois — teammates não têm MCP), relatórios, commits.

---

## Os 6 problemas — causa-raiz, correção e agente

### P1 — Sidebar esquerda com status cortado → `frontend-agent`
- **Causa:** `#app-body` grid 100vh overflow:hidden (index.html:1460); `#conv-panel` flex col
  overflow:hidden (1499); `#metric-cards` sem `flex-shrink:0` (1545); `#conv-list flex:1` cresce e
  empurra o `#sidebar-footer` (status "Conectado" + dot + "Silenciar", 1628-1642) pra fora.
- **Correção:** `#sidebar-footer { flex-shrink:0 }`, `#conv-list { min-height:0; overflow-y:auto }`,
  `#metric-cards { flex-shrink:0 }` — header/métricas/footer não encolhem, a lista rola interna, footer
  sempre visível.

### P2 — Respostas rápidas (canned) pequeno e mal posicionado → `frontend-agent` (+architect se mudar ADR-012)
- **Causa:** `#canned-popover` (index.html:1799) `width:300px; max-height:200px` hardcoded; JS posiciona
  via `getBoundingClientRect` (app.js:2643-2644 e 2800-2801) **sem clamp de viewport**.
- **Correção:** largura responsiva `min(360px, calc(100vw - 24px))`; `max-height` dinâmica conforme
  espaço; clamp horizontal/vertical p/ não vazar; flip up/down. Atualizar ADR-012 se mudar o contrato.

### P3 — Visto/entregue sobreposto, status de leitura errado → `frontend-agent`
- **Causa:** `_tickSvg(entregue,lida)` (app.js:839-844), SVGs (834-837); `_SVG_TICK_READ` reusa o
  desenho do DELIVERED; polylines do double-check sobrepõem (x=1 e x=7); `.bolha-tick`
  (index.html:1383-1395) / `.bolha-tick svg` (1108) sem largura fixa → strokes empilham.
- **Correção:** corrigir geometria do double-check (sem sobreposição), fixar width/height do
  `.bolha-tick`+svg, `.tick-read` em azul de leitura (#53bdeb). 3 estados distintos: ⏱ enviando →
  ✓✓ cinza entregue → ✓✓ azul lido. SSE `mensagem_lida` (app.js:2448-2460) já troca por `data-wamid`.

### P4 — Rolagem automática não funciona em msg nova → `frontend-agent`
- **Causa:** `appendMensagemIncremental` (app.js:1112-1151) checa `_estaNoFundo()` (1003-1007) e seta
  `scrollTop=scrollHeight` **antes do reflow** → valor stale → não rola. Sem `requestAnimationFrame`.
  Listener (3061-3063) só esconde o botão "Novas mensagens", nunca mostra.
- **Correção:** medir "no fundo" **antes** do append; rolar dentro de `requestAnimationFrame` (ou
  `scrollIntoView`); botão "Novas mensagens" aparece com msg nova + rolado pra cima, some no fundo.

### P5 — Busca mistura mensagens e chats de bot → `frontend-agent` (UX pelo `product-owner-agent`)
- **Causa:** `#btn-search-mode` @ / ? críptico (index.html:1536); `renderSearchResults`
  (app.js:2055-2078) mostra só `snippet` sem origem. `/admin/search` (api/admin.py:624-674) **já
  retorna `origem`**.
- **Correção (decisão = rotular):** exibir ícone/label de origem (🤖 bot / 👤 cliente / 👩‍💼 operador)
  via `r.origem`; deixar o modo explícito ("Contato" vs "Mensagem" em vez de @/?). PO valida rótulos.

### P6 — Verificar que as configurações funcionam → `qa-agent` (verifica) + `frontend-agent` (gaps)
- **Estado:** settings.html 4 abas funcionam (refresh pós-CRUD, confirmações, tema persiste). Gaps:
  fallback de canned (settings.html:648) mascara erro real; match frágil de 409 por string
  (766/796/827); input de cor hex sem validação (301).
- **Ação:** qa-agent testa cada aba (CRUD + tema) com evidência; frontend-agent corrige os 3 gaps.

---

## Backlog de features (apenas PROPOR — não implementar)
`product-owner-agent` + Lead entregam lista priorizada (esforço × valor) em
`.claude/wiki/frontend/FEATURE_BACKLOG.md`. Sementes a refinar: indicador "digitando" do operador,
busca com filtros (data/status), atalhos de teclado ampliados, badges de SLA/tempo de espera,
reabertura rápida de conversa resolvida, templates de mídia, modo compacto da lista, som de
notificação configurável, atribuição rápida (drag), preview de imagem inline.

---

## Plano de ação passo a passo
1. Branch `ui/usabilidade` a partir de `qa/full-sweep`.
2. Spawn `frontend-agent` + `qa-agent` + `product-owner-agent` (architect/backend on-demand).
3. Lead: screenshots ANTES de cada área (Playwright, :8000).
4. frontend-agent: fixes P1→P6 (commit isolado por problema, pt-BR). Operador `\n`, IA `<br>`,
   `escapeHtml` em novo render.
5. Validação por fix: qa-agent (console+comportamento), Lead (screenshot DEPOIS), `pytest -q`
   (regressão 43-47 verde).
6. P6: qa-agent testa as 4 abas; frontend-agent fecha os gaps.
7. PO + Lead: `FEATURE_BACKLOG.md`.
8. Relatórios: `.claude/wiki/qa/UX_FINDINGS.md` (antes/depois) e `UX_FINAL_REPORT.md`.
9. Encerrar o time.

---

## Regras
- Vanilla JS apenas (framework exige ADR). Mudança de contrato SSE/API exige ADR.
- **Não disparar WhatsApp real** (sem assumir/enviar/devolver em conversas reais). Iteração via reload
  de estáticos no servidor :8000 existente.
- Toda asserção "resolvido" precisa de evidência (screenshot antes/depois + console + pytest).
- pt-BR em commits/relatórios.

## Entregáveis
6 problemas corrigidos e validados (antes/depois); `docs/ux/UX_MISSION.md`;
`.claude/wiki/qa/UX_FINDINGS.md`; `UX_FINAL_REPORT.md`; `.claude/wiki/frontend/FEATURE_BACKLOG.md`.
Harness pytest verde. Commits na `ui/usabilidade` (sem push).
