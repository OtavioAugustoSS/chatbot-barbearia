# ADR-012: Fix Compositor Layout + Mídia Async + Assume/Devolver Gaps

Status: proposto
Data: 2026-05-25
Decisor: architect-agent
Stakeholders consultados: frontend-agent (implícito via código), backend-agent (implícito via código)

## Contexto

A branch `redesign/admin-interface` introduziu um compositor de mensagens redesenhado no dashboard admin (`static/admin/index.html`) e um novo endpoint de upload de mídia (`api/admin.py`). Diagnóstico técnico revelou cinco problemas distintos que afetam layout, comportamento async e UX do compositor.

## Diagnóstico Técnico

### D1 — CSS Selector Mismatch (root cause do compositor "torto")

**Problema confirmado:**

- O elemento HTML é `<footer id="composer" ...>` (linha 1497)
- O CSS V7 define regras em `#composer-area` (linha 601) e a media query mobile também usa `#composer-area` (linha 318)
- O seletor `#composer-area` nunca bate em nenhum elemento do DOM — todas as regras V7 (border-top, background, padding) são ignoradas pelo browser

**Consequência:** o footer `#composer` herda apenas estilos inline (`background: var(--bg-composer); border-top: 1px solid var(--border)`) sem o padding e configuração de layout definidos no CSS. Isso causa o desalinhamento visual.

**Decisão: renomear o CSS `#composer-area` → `#composer` em todas as ocorrências.**

Justificativa: o HTML `id="composer"` é o identificador semântico correto (`<footer>` é o elemento estrutural certo). Há apenas 2 ocorrências CSS (`#composer-area` no bloco V7, linha 601, e na media query mobile, linha 318) — mudança cirúrgica, zero risco de colisão.

Alternativa rejeitada: renomear o HTML `id="composer"` → `id="composer-area"` exigiria atualizar todas as referências JS (`document.getElementById('composer')` etc.), risco de regressão maior.

### D2 — Media Endpoint Async

**Problema confirmado:**

- Endpoint `POST /admin/enviar-midia/{telefone}` é `def enviar_midia(...)` — função síncrona normal (linha 980)
- Usa `file.file.read()` — leitura síncrona de I/O (linha 988)
- `upload_midia_whatsapp()` e `enviar_mensagem_midia()` em `services/whatsapp.py` são síncronos (`def`, usam `requests.post`) (linhas 242, 259)

**Diagnóstico:** não há problema de async aqui. FastAPI trata `def` endpoints rodando-os em um thread pool executor, isolando o event loop. O `file.file.read()` síncrono é correto para `def` endpoints. Se o endpoint fosse `async def` com `file.file.read()` haveria bloqueio do event loop — mas não é o caso.

**Decisão: nenhuma mudança necessária no endpoint de mídia em relação a async.**

O padrão atual (tudo síncrono, endpoint `def`) é correto para esta stack. Manter como está.

Nota de risco: `upload_midia_whatsapp()` pode demorar vários segundos em redes lentas, bloqueando uma thread do pool. Para o volume atual (barbearia local, poucos atendentes simultâneos), o pool padrão do Uvicorn (40 threads) é suficiente. Não justifica refatoração.

### D3 — Canned Popover Clipping

**Problema confirmado:**

O `#canned-popover` usa `position: absolute; bottom-full; left-0; z-index: 20`. A cadeia de ancestrais é:

```
<footer id="composer">          — sem overflow
  <div class="flex items-end gap-2 p-3">   — sem overflow
    <div class="relative flex-shrink-0">   — PAI IMEDIATO, position:relative
      <button id="canned-btn">
      <div id="canned-popover" class="... absolute bottom-full ...">
```

O pai imediato (`div.relative`) não tem `overflow:hidden`, portanto o clipping vem de ancestrais. O `#chat-panel` tem `overflow:hidden` explícito (linha 1380: `class="flex flex-col overflow-hidden"`). O `<body>` também tem `overflow:hidden` (linha 1200).

Com `position:absolute` e `z-index:20`, o popover é contido pelo bloco de formatação de `#chat-panel` (`overflow:hidden`). O popover abre "para cima" (`bottom-full`) dentro de um flex container com `overflow:hidden` — se o compositor estiver na base, `bottom-full` pode ser clipado pela borda do `#chat-panel`.

Adicionalmente, o próprio `#canned-popover` tem `overflow-hidden` na classe Tailwind (linha 1524: `class="... overflow-hidden"`), o que é correto para bordas arredondadas, mas `overflow-y: auto` no style inline é redundante com `overflow-hidden`.

**Decisão: substituir `position:absolute` por `position:fixed` no `#canned-popover`, calculando posição via JS.**

Alternativas consideradas:
- `overflow:visible` no `#chat-panel`: quebra o layout de scroll de mensagens — rejeitado
- `z-index` maior: não resolve clipping por `overflow:hidden` — rejeitado
- `position:fixed` com JS: o JS já gerencia abertura/fechamento do popover; adicionar posicionamento dinâmico (calcular `bottom` a partir do `getBoundingClientRect()` do botão) é a solução padrão para este problema

Implementação recomendada para o frontend-agent:
```js
// ao abrir o popover, calcular posição a partir do botão
const btnRect = document.getElementById('canned-btn').getBoundingClientRect();
const popover = document.getElementById('canned-popover');
popover.style.position = 'fixed';
popover.style.bottom = (window.innerHeight - btnRect.top + 8) + 'px';
popover.style.left = btnRect.left + 'px';
```
Remover as classes `absolute bottom-full left-0 mb-2` e substituir por `fixed` sem classes de posição — posição 100% via JS.

### D4 — Double Border

**Problema confirmado:**

Quando `#attach-preview-area` está visível, há dois borders adjacentes:
1. `#attach-preview-area` tem `border-top:1px solid var(--border)` no style inline (linha 1502)
2. `<footer id="composer">` tem `border-top: 1px solid var(--border)` no style inline (linha 1497) — e quando o bug D1 for corrigido, o CSS `#composer { border-top: 1px solid var(--border-muted) }` também estará ativo

O `#attach-preview-area` é o primeiro filho visível do footer quando ativo — o border-top do footer já separa o compositor do chat. O border-top do preview area cria uma linha duplicada interna desnecessária.

**Decisão: remover o `border-top` do `#attach-preview-area`.**

Justificativa: o border do footer (`#composer`) já estabelece a separação visual do compositor. O preview area é interior ao compositor — não precisa de separador. Quando a preview está oculta (default), o border do footer é suficiente.

Alternativa rejeitada: remover o border do footer — quebraria a separação visual entre área de mensagens e compositor quando preview não está ativa.

### D5 — Attach + Canned Button Layout

**Problema confirmado:**

O CSS define `#btn-tag, #btn-info-toggle, #canned-btn { min-width: 44px; min-height: 44px; }` (linha 877) mas o `#canned-btn` no HTML tem `class="w-8 h-8 ..."` (32px × 32px) e não tem a classe `btn-icon`. A regra CSS `min-width/min-height` sobrepõe o tamanho do botão de 32px para 44px, criando um botão maior que o `#attach-btn` (que é `w-8 h-8` sem override de min-size).

Isso gera inconsistência visual: `#attach-btn` = 32px, `#canned-btn` = 44px efetivo.

O flex container usa `items-end`, que alinha botões na base — correto para o comportamento WhatsApp-style (botões ficam na base quando textarea cresce).

**Decisão: uniformizar os botões do compositor para 36px × 36px e remover o override de min-size do `#canned-btn`.**

Justificativa: 36px é adequado para desktop (onde este dashboard é primariamente usado). O override `min-width/min-height: 44px` em `#canned-btn` foi adicionado como regra F1 de touch targets, mas o dashboard admin não é uma interface mobile-first. A media query mobile já trata touch targets adequadamente. Remover o override da regra global e manter apenas na media query (`@media (max-width: 768px)`).

Alternativa: manter 44px em ambos os botões — aumentaria o compositor verticalmente sem benefício em desktop.

## Decisões Sumarizadas

| # | Problema | Decisão |
|---|---|---|
| D1 | CSS `#composer-area` não bate no HTML `#composer` | Renomear CSS `#composer-area` → `#composer` (2 ocorrências) |
| D2 | Endpoint mídia async | Nenhuma mudança — `def` + `requests` síncrono é correto |
| D3 | Canned popover clipado por `overflow:hidden` | `position:fixed` + posicionamento JS via `getBoundingClientRect()` |
| D4 | Double border quando attach preview visível | Remover `border-top` do `#attach-preview-area` |
| D5 | `#canned-btn` 44px vs `#attach-btn` 32px | Uniformizar para 36px, remover override min-size da regra global |

## Arquivos a Modificar

| Arquivo | Agente | Mudança |
|---|---|---|
| `static/admin/index.html` | frontend-agent | D1: renomear CSS `#composer-area`→`#composer` (linhas 318, 601); D3: trocar classes position do `#canned-popover`; D4: remover `border-top` do `#attach-preview-area`; D5: ajustar regra CSS `#canned-btn` |
| `static/admin/js/app.js` | frontend-agent | D3: adicionar lógica de posicionamento JS no handler de abertura do canned popover |
| `api/admin.py` | backend-agent | Nenhuma mudança de async necessária (D2 confirmado como não-problema) |

## API Contract Changes

Nenhuma. O endpoint `POST /admin/enviar-midia/{telefone}` permanece com a mesma assinatura e comportamento.

## Consequências

- Positivo: compositor renderizará com padding, background e border-top corretos após D1
- Positivo: canned popover não será mais clipado após D3
- Positivo: visual do footer limpo (um único border, botões uniformes) após D4+D5
- Neutro: D2 confirmou que o código de mídia está correto — zero churn desnecessário
- Risco baixo: D3 (position:fixed + JS) requer teste em diferentes tamanhos de tela para garantir que o popover não saia da viewport

## Alternativas Consideradas

Ver seção de cada decisão acima.
