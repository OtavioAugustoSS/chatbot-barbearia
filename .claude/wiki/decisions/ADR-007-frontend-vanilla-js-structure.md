# ADR-007: Frontend — Vanilla JS, Estrutura de Arquivos e Proibição de Frameworks
Status: aceito
Data: 2026-05-21
Decisor: architect-agent
Stakeholders consultados: frontend-agent (código existente como fonte de verdade)

## Contexto

O dashboard admin em `static/admin/` é servido como arquivos estáticos pelo FastAPI (apenas em `MODO_HIBRIDO`). A escolha de vanilla JS foi feita como regra rígida do projeto mas nunca documentada em ADR. A estrutura atual de arquivos também precisa ser formalizada.

## Decisão

### Estrutura atual de arquivos

```
static/admin/
  index.html        — tela principal do dashboard (conversas, chat)
  login.html        — tela de login
  settings.html     — tela de configurações (atendentes, canned responses, labels)
  js/
    app.js          — lógica principal: renderização de conversas, chat, estado global
    api.js          — funções de chamada à API REST (fetch wrappers com auth header)
    sse.js          — gerenciamento do EventSource SSE (reconexão, dispatch de eventos)
```

### Regras de estrutura

1. **Arquivo único por responsabilidade**: sem `bundle.js` monolítico. Cada `.js` tem responsabilidade clara.
2. **Sem módulos ES**: arquivos JS são incluídos via `<script src="...">` em ordem. Não usar `type="module"` — simplifica deploy sem bundler.
3. **Estado global**: objeto JS global por namespace (`window.App`, `window.API`, `window.SSE`) em vez de closures — compatível com a abordagem de múltiplos `<script>` tags.
4. **CSS**: inline ou em `<style>` dentro do HTML. Sem arquivo `.css` separado por enquanto — a interface é suficientemente compacta.

### Proibição de frameworks

A introdução de qualquer framework JavaScript (React, Vue, Angular, Svelte, etc.) ou biblioteca de estado (Redux, Zustand, MobX) requer:
1. ADR com status `proposto`
2. Aprovação explícita do usuário humano (não pode ser decidido unilateralmente por frontend-agent ou architect-agent)
3. Justificativa de que 3+ funcionalidades concretas identificadas não podem ser implementadas razoavelmente em vanilla JS

### Bibliotecas JavaScript permitidas sem novo ADR

- Bibliotecas sem bundler (CDN via `<script>`), com escopo limitado:
  - Formatação de data: `dayjs` (se necessário)
  - Markdown rendering: não necessário atualmente
- Qualquer biblioteca que exija `npm install` ou `node_modules` constitui mudança de toolchain — requer ADR

### Bundler / build step

Atualmente inexistente. Arquivos são servidos diretamente pelo FastAPI. Adicionar `esbuild`, `vite`, `webpack` etc. constitui mudança de arquitetura — requer ADR aprovado.

## Consequências

- Positivo: zero dependências de build, deploy trivial (apenas `python main.py`)
- Positivo: qualquer desenvolvedor consegue modificar o frontend sem configurar toolchain
- Negativo: sem type checking (TypeScript), sem hot reload de desenvolvimento
- Negativo: à medida que `app.js` cresce, a manutenção fica mais difícil sem módulos
- Risco: `app.js` já está em dimensão que justifica refatoração em módulos ES se o browser-target permitir (Chrome moderno no dashboard de atendente — aceitável)

## Alternativas consideradas

- ES Modules com `type="module"`: simplificaria organização sem bundler, mas requer CORS e servidor adequado para imports relativos. Poderia ser adotado sem ADR se apenas reorganizando arquivos existentes.
- Vue 3 via CDN (sem build): meio-termo entre vanilla e framework completo. Rejeitado — mesmo via CDN, introduz paradigma reativo que muda fundamentalmente como o código é organizado.

---

## Addendum — FASE 3 (2026-05-21) — Validação architect-agent (1ª passagem)

> Entradas de FAIL desta passagem foram superadas pela 2ª validação abaixo. Mantidas apenas para rastreabilidade histórica de que os itens estavam pendentes quando o frontend-agent iniciou a implementação.

**QW-F1**: FAIL inicial — `sse.js` usava `setTimeout(conectar, 3000)` fixo; backoff não implementado.

**QW-F3**: FAIL inicial — `bulkSelecionadas` não era limpa ao trocar de filtro.

**SP-1**: FAIL inicial — 3x `window.prompt()` permaneciam (linhas 845, 1172, 1279); ADR-008 criado para guiar implementação.

---

## Addendum — FASE 3 (2026-05-21) — Re-validação architect-agent (2ª passagem)

Frontend-agent implementou os 3 itens FAIL após a 1ª validação. Re-validação cirúrgica executada lendo os arquivos diretamente.

### QW-F1 — SSE backoff exponencial (`sse.js`)

- `_retryDelay = 1000` declarado na linha 3; `_MAX_DELAY = 30000` na linha 5.
- Jitter ±20%: `const jitter = (_retryDelay * 0.2) * (Math.random() * 2 - 1)` — linha 20.
- Dobramento: `_retryDelay = Math.min(_retryDelay * 2, _MAX_DELAY)` — linha 24.
- Reset em conexão bem-sucedida: `_retryDelay = 1000` na linha 48, dentro do bloco `if (res.ok && res.body)`.
- `setTimeout(conectar, 3000)` fixo: **ausente**. Único `setTimeout` é `setTimeout(conectar, delay)` na linha 25, onde `delay` carrega o jitter calculado.

**Veredicto: PASS.**

### QW-F3 — Bulk clear ao trocar filtro (`app.js`)

- Handler `#filter-tabs`: `state.bulkSelecionadas.clear()` na linha 1750, seguida de `atualizarBulkBar()` na linha 1751.
- Handler `#status-filter-row`: `state.bulkSelecionadas.clear()` na linha 1929, seguida de `atualizarBulkBar()` na linha 1930.
- Ambos os sites têm comentário `// QW-F3: limpa seleção bulk ao trocar filtro`.

**Veredicto: PASS.**

### SP-1 — Modal snooze e remoção de `window.prompt()` (`index.html` + `app.js`)

- `#modal-snooze` presente em `index.html` linha 509. Presets: `data-hours="1"` (l.514), `data-hours="4"` (l.515), `data-hours="24"` (l.516), `data-hours="168"` = 1 semana (l.517). Campo `datetime-local` id=`snooze-custom-dt` na linha 520.
- `abrirModalSnooze()` declarada como `function abrirModalSnooze()` retornando `new Promise` — linha 176 de `app.js`. É chamada com `await` nas linhas 989 (`alterarStatus`) e 1424 (`bulkSnooze`).
- `#modal-input-text` presente em `index.html` linha 529; usado por `abrirModalInputTexto()` (`app.js` l.252–258) para o caso `salvarViewAtual()` (l.1312).
- `window.prompt()` como chamada real: **ausente**. Grep retorna apenas comentários de rastreabilidade nas linhas 169, 988, 1311, 1423 — todos com prefixo `// SP-1: ... substitui window.prompt()`.

**Veredicto: PASS.**
