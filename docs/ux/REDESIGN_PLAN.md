# Bolshoi Dashboard — Plano de Redesign

**Branch:** `ui/redesign-stitch`
**Iniciado:** 2026-05-28
**Stack atual:** Tailwind via CDN + vanilla JS + HTML estático em `static/admin/`
**Stack alvo:** mesmo (sem framework — BR-vanilla-only do Architect)
**Mockups:** Stitch project `8248944352976355122` · design system `assets/558847645356488795`

---

## Objetivo

Repaginar visualmente o dashboard de atendimento sem mexer em comportamento. Critérios:
- **Não parecer "feito por IA"** — sem indigo/violet padrão, sem cards retangulares sem alma, sem ícones emoji estruturais
- **Moderno** — tipografia variável, motion intencional, micro-interactions com causa-efeito
- **Fluido** — transições de painel coerentes com direção (drawer vem do lado correto, modais vêm do trigger)
- **Bonito sob pressão operacional** — operador olha por 4 horas seguidas, não pode cansar

## Princípios de design

1. **Confiança operacional > hype visual.** Status do bot (ativo / aguardando / humano) precisa ser identificável em 200ms.
2. **Movimento expressa causa-efeito.** Bolha de cliente entra pela esquerda. Bolha de operador entra pela direita. Painel de info desliza de onde foi chamado.
3. **Mono para dados técnicos.** Geist Mono em timestamps, telefones, IDs, badges numéricos. Plus Jakarta Sans em prosa.
4. **Densidade respiratória.** 8pt grid, gaps de 12-16px entre seções, hierarquia clara entre 3 níveis de elevação.
5. **Glassmorphism só em overlays.** Modais, popovers e drawers mobile podem ter blur. Conteúdo de leitura prolongada (mensagens) nunca.

## Design system

| Token | Valor |
|---|---|
| Color mode | Dark (light opcional via toggle existente) |
| Color seed | `#2481CC` (brand Bolshoi mantido) |
| Color variant | VIBRANT (Material 3 dynamic) |
| Headline font | Plus Jakarta Sans 600 |
| Body font | Plus Jakarta Sans 400/500 |
| Label font | Geist Mono 500 (timestamps, telefones, badges) |
| Roundness | 12px (cards), 9999px pill (chips/badges) |
| Spacing | 4 / 8 / 12 / 16 / 20 / 24 / 32 (8pt grid) |
| duration-fast | 120ms (hover, press) |
| duration-normal | 200ms (panel, modal enter) |
| duration-slow | 320ms (drawer slide) |
| ease-out | `cubic-bezier(0.16, 1, 0.3, 1)` |
| ease-spring | `cubic-bezier(0.34, 1.56, 0.64, 1)` (CTA, conv ativa) |

## Layout

### Desktop ≥1024px (4 colunas)
```
┌────┬──────────────┬────────────────────────┬─────────────┐
│ 72 │ 360          │ flex-1                 │ 320 (slide) │
│    │              │                        │             │
│ S  │ Conv list    │ Chat                   │ Info panel  │
│ I  │ - busca      │ - header com status    │ - cliente   │
│ D  │ - filters    │ - msgs (dot pattern    │ - tags      │
│ E  │ - cards 15   │   bg opacity 0.04)     │ - notas     │
│    │              │ - composer fixo        │ - stats     │
└────┴──────────────┴────────────────────────┴─────────────┘
```

### Tablet 768–1023px (2 colunas)
- Conv-list vira drawer overlay com backdrop blur (swipe da esquerda)
- Info-panel vira drawer da direita

### Mobile <768px (1 coluna por vez)
- Bottom-nav fixo 4 ações: conversas / filas / busca / config
- Swipe direita = abrir conv-list, swipe esquerda = abrir info-panel
- Composer com safe-area inset bottom

## Tipos de bolha (mensagens)

| Tipo | Direção | Canto squared | Background | Label color | Quando |
|---|---|---|---|---|---|
| Cliente (incoming) | esquerda | top-left | `surface-container-low` | sépia/copper | sempre que cliente envia |
| Bot (outgoing) | direita | top-right | tertiary-container verde profundo | mint claro | IA respondeu |
| Operador (outgoing humano) | direita | top-right | primary azul vibrante | azul claro | operador enviou |
| Sistema | centralizado | pill | accent-subtle | text-muted | "Otávio assumiu", "Conversa encerrada" |

**Tick double-check:** 18x11 viewBox. Cinza = entregue. Azul accent `#53BDEB` = lido. **Nunca verde** — não somos WhatsApp.

## Cores funcionais semânticas

| Token | Cor | Uso | Acompanhar de |
|---|---|---|---|
| `--success` | `#00A884` | bot ativo, SSE conectado | ícone check/bot |
| `--warning` | `#D29922` | aguardando humano, atraso SLA | ícone clock/alert |
| `--danger` | `#F85149` | falha envio, bot off | ícone X/alert-triangle |
| `--accent` | `#2481CC` | CTAs, bordas ativas | — (brand) |

**Regra:** cor nunca é único indicador. Sempre + ícone ou + texto.

## Anti-patterns (proibido absoluto)

- ❌ Emoji como ícone estrutural — usar Lucide SVG
- ❌ Gradiente roxo→rosa genérico de SaaS
- ❌ Glassmorphism em conteúdo de leitura prolongada
- ❌ Cor única como único indicador de status
- ❌ Sombras hex hardcoded — sempre via tokens
- ❌ Animação de loading >300ms sem skeleton
- ❌ Ícones flat coloridos estilo Material 2014
- ❌ Estética de landing page (este é app operacional)

## Contratos invioláveis

- **SSE `/admin/eventos/stream`** — formato de eventos não muda
- **REST `/admin/*`** — endpoints intactos
- **Regra `<br>` vs `\n`** — IA usa `<br>`, operador usa `\n`. `_normalizar_texto_envio()` em `api/webhook.py` continua único ponto de conversão.
- **AI Response Contract** `{intencao, resposta_sugerida}` intocado (mudança requer ADR)
- **BR-001** — nenhuma feature de agendamento no dashboard (PO bloqueia)
- **Vanilla JS** — nada de React/Vue/Svelte (Architect bloqueia)

## Escopo de implementação

### Fase 1 — Tokens e tipografia (baixo risco)
- [ ] Trocar font import: Fira Sans → Plus Jakarta Sans + Geist Mono
- [ ] Atualizar `--font-body`, `--font-heading`, criar `--font-mono` separado
- [ ] Aplicar Geist Mono em `.bolha-ts`, `#thread-telefone`, `#badge-total`, badges numéricos
- [ ] Ajustar variant: trocar `--accent-subtle` opacity 0.15→0.12, melhorar contraste WCAG

### Fase 2 — Surfaces e elevação (médio risco)
- [ ] 3 níveis de surface explícitos: `--surface-base`, `--surface-container`, `--surface-container-high`
- [ ] Bordas 1px low-contrast separando colunas (substitui sombras pesadas)
- [ ] Roundness 12px nos cards (atual usa mix de 8/10/14)
- [ ] Sidebar acionável: avatar do operador no topo + presence dot, navegação centralizada

### Fase 3 — Conv cards refinados (médio risco)
- [ ] Card layout: avatar 40px + nome 14/600 + preview line-clamp-2 + ts mono direita
- [ ] Active state: border-left accent 3px + bg accent-subtle + glow `box-shadow: 0 0 0 1px var(--accent-border)` sutil
- [ ] Hover: `transform: translateX(2px)` smooth
- [ ] Avatar status badge: bot=verde, aguardando=amarelo, humano=azul, outro=warning

### Fase 4 — Chat refinado (alto risco)
- [ ] Header: avatar + nome + telefone mono + status badge fluido + grupo de ações com tooltips
- [ ] Mensagens área: dot pattern opacity 0.04 (já existe mas otimizar)
- [ ] Bolhas: ajustar squared corners + labels + tick redesenhado
- [ ] Composer: textarea auto-resize, char counter sutil, send button spring animation
- [ ] System messages (handoff, encerramento): pill centralizado accent-subtle

### Fase 5 — Info panel accordion (baixo risco)
- [ ] Slide-in da direita, backdrop sutil em mobile
- [ ] Accordion sections: cliente / tags / notas / stats
- [ ] FAB "+ nota" sticky bottom do painel

### Fase 6 — Motion polish (baixo risco)
- [ ] Stagger reveal nos cards de conversa (30ms entre items)
- [ ] Spring physics no send button + active conv
- [ ] prefers-reduced-motion: TODAS as decorativas off, só funcionais ≤100ms
- [ ] Modal enter/exit: 200ms / 140ms (exit 70% do enter — MD motion)

### Fase 7 — Mobile bottom-nav (médio risco)
- [ ] Substituir drawer hamburger por bottom-nav 4 ações
- [ ] Swipe gestures pra abrir/fechar painéis
- [ ] Safe-area insets

## Validação pré-merge

- [ ] Renderização side-by-side: mockup Stitch vs implementação (qa-agent)
- [ ] Contraste WCAG 4.5:1 em todos pares texto/fundo (light + dark)
- [ ] `prefers-reduced-motion` respeitado
- [ ] Keyboard nav: tab order = visual order
- [ ] Smoke test no Playwright: login → assumir conversa → enviar mensagem → devolver
- [ ] pytest 47/47 sem regressão (contratos REST/SSE intactos)
- [ ] Versionamento de assets (`app.js?v=hash`) — mitigar cache agressivo

## Riscos conhecidos

| Risco | Mitigação |
|---|---|
| Plus Jakarta Sans + Geist Mono = +200kb font payload | preload críticos, `font-display: swap`, opcional self-host posterior |
| Cache agressivo de estáticos | versionar URLs com `?v=` ou hash de build |
| Operadores acostumados com layout atual | migração visual sem mudar fluxo; manter atalhos teclado |
| Stitch gera React/Tailwind — porte vanilla é manual | mockup é referência visual, não código diretamente reutilizável |

## Próximas etapas

1. Aguardar Stitch gerar mockups (desktop / login / mobile)
2. Revisar mockups, ajustar prompts se necessário
3. Capturar screenshots dos mockups em `docs/ux/redesign/mockups/`
4. Delegar Fase 1+2 pro frontend-agent
5. QA visual lado-a-lado a cada fase concluída
