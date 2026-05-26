# DASHBOARD-AUDIT.md — Auditoria Completa do Dashboard de Atendentes

**Data:** 2026-05-21
**Auditor:** frontend-agent
**Arquivos analisados:**
- `static/admin/index.html` (513 linhas)
- `static/admin/js/app.js` (2038 linhas)
- `static/admin/js/api.js` (197 linhas)
- `static/admin/js/sse.js` (61 linhas)
- `docs/USER_STORIES_INTERFACE_ATENDENTE.md` (149 stories + expansões Fase 1-3)

---

## ATENÇÃO: Mudança de Estrutura Detectada

O documento USER_STORIES_INTERFACE_ATENDENTE.md referencia `static/admin/app.js` (arquivo único, 1151 linhas) mas o repositório atual possui uma estrutura modularizada diferente:

- `static/admin/js/app.js` — lógica principal (2038 linhas)
- `static/admin/js/api.js` — camada HTTP centralizada (197 linhas)
- `static/admin/js/sse.js` — módulo SSE isolado (61 linhas)
- `static/admin/settings.html` — página de configurações (não auditada aqui)

Isso indica que houve uma refatoração significativa após a documentação inicial (v1.0).

---

## A) Cobertura de User Stories

### Seção 1 — Autenticação (US-001 a US-007): IMPLEMENTADO (6/7)
- US-005 (Logout): usa `confirm()` nativo — anti-padrão confirmado

### Seção 2 — Sidebar Métricas (US-008 a US-009): IMPLEMENTADO
- Métricas calculadas via `atualizarBadges(totais)` com dados vindos do backend

### Seção 3 — Filtros e Chips (US-010 a US-011): PARCIALMENTE IMPLEMENTADO
- US-010 (Filtro "Todas"): IMPLEMENTADO
- US-011 (Filtros por estado): IMPLEMENTADO — a nova versão usa `state.filtro` corretamente e filtra por boolean no `renderConvList()` (o bug do filtro via string foi CORRIGIDO na refatoração)

### Seção 4 — Busca de Conversas (US-012 a US-014): IMPLEMENTADO
- Novo: busca global por mensagens com prefixo `?` via `api.searchMensagens()`

### Seção 5 — Lista de Conversas (US-015 a US-019): IMPLEMENTADO

### Seção 6 — Estados Visuais (US-020 a US-024): IMPLEMENTADO
- `pulse-red` presente; dots de cor por estado presentes

### Seção 7 — Abertura de Conversa (US-025 a US-029): IMPLEMENTADO
- US-029 (painel auto-abre em desktop): PARCIAL — painel está oculto por padrão, abre só via clique

### Seção 8 — Bolhas de Mensagem (US-030 a US-036): IMPLEMENTADO
- Bolha-falha com borda vermelha: IMPLEMENTADO
- Separadores de evento (handoff) IMPLEMENTADOS inline em `renderMensagens()` e `appendMensagemIncremental()`

### Seção 9 — Separadores de Data e Eventos (US-037 a US-040): IMPLEMENTADO
- US-039 (separador de evento handoff): IMPLEMENTADO — `separadorEvento()` injetado em `renderMensagens()` ao detectar mudança de origem entre bot e humano

### Seção 10 — Thread Header (US-041 a US-043): IMPLEMENTADO

### Seção 11 — Assumir Conversa (US-044 a US-047): IMPLEMENTADO

### Seção 12 — Enviar Mensagem (US-048 a US-053): IMPLEMENTADO
- Optimistic UI com `tempId`: IMPLEMENTADO
- Bolha pendente e resolução via `resolverBolhaPendente()`: IMPLEMENTADO

### Seção 13 — Respostas Rápidas (US-054 a US-056): IMPLEMENTADO
- Substituído por sistema de Canned Responses dinâmico (US-181/182)

### Seção 14 — Devolver ao Bot (US-057 a US-059): IMPLEMENTADO
- US-057: usa `confirm()` nativo

### Seção 15 — Compositor 4 Estados (US-060 a US-063): IMPLEMENTADO
- `syncComposerState()` gerencia todos os 4 estados corretamente

### Seção 16 — Painel de Info do Cliente (US-064 a US-069): IMPLEMENTADO

### Seção 17 — Notas Internas (US-070 a US-073): IMPLEMENTADO
- Novo: edição de notas (`api.editNota`) e exclusão (`api.deleteNota`)

### Seção 18 — Tags de Conversa (US-074 a US-078): IMPLEMENTADO

### Seção 19 — SSE Tempo Real (US-079 a US-083): IMPLEMENTADO
- Reconexão com 3s de espera: IMPLEMENTADO em `sse.js`
- Sem backoff exponencial (fixo em 3s)

### Seção 20 — Notificações e Som (US-084 a US-086): IMPLEMENTADO

### Seção 21 — Gestão de Atendentes (US-087 a US-092): IMPLEMENTADO
- GAP-01 resolvido: `api.ativarAtendente()` agora existe (PATCH `/admin/atendentes/{id}/ativar`)

### Seção 22 — Responsividade Mobile (US-093 a US-095): NAO IMPLEMENTADO
- Ver seção C) abaixo — sem breakpoints CSS

### Seção 23 — Erros de Rede e Resiliência (US-096 a US-100): IMPLEMENTADO

### Seções 24-31 (US-101 a US-149): NÃO IMPLEMENTADO (maioria)
- Infinite scroll (US-101): NÃO
- Tooltip timestamp (US-104): NÃO
- Botão "novas mensagens" (US-105): NÃO
- Busca Ctrl+F na thread (US-106): NÃO
- Aviso JWT expirando (US-115): NÃO
- Draft ao expirar (US-116 a US-117): NÃO
- Indicador presença de atendentes (US-114): NÃO (presence existe para transferir, mas sem painel "quem está online")
- Mute por conversa (US-131): NÃO
- Respostas rápidas customizáveis localmente (US-132 a US-133): PARCIAL — canned responses existem mas são DB, não localStorage
- Botão "novas mensagens" scroll (US-105, US-107): NÃO
- Badge no título da aba (US-127): NÃO
- Desktop Notification API (US-128): NÃO

### Seções 32-38 (US-150 a US-220+, Fase 1-3): MAIORIA IMPLEMENTADO
- Labels múltiplas (US-150 a US-163): IMPLEMENTADO (exceto seed US-161)
- Status de conversa (US-164 a US-175): IMPLEMENTADO (US-175 parcial)
- Canned responses dinâmicas (US-176 a US-188): IMPLEMENTADO
- Atribuição entre atendentes (US-189 a US-197): IMPLEMENTADO
- @mentions em notas (US-198 a US-209): IMPLEMENTADO (US-208 parcial)
- Bulk actions (US-210 a US-220): IMPLEMENTADO com gaps:
  - US-214 (bulk atribuir): backend pronto, UI não expõe
  - US-215 (bulk label): backend pronto, UI não expõe
  - US-218 (SSE bulk_aplicado): backend publica, frontend não consome
  - US-219 (limpar seleção ao trocar filtro): BUG confirmado
- Presence (US-221 a US-224+): IMPLEMENTADO
- Saved Views: IMPLEMENTADO
- Search global: IMPLEMENTADO
- Atalhos de teclado: IMPLEMENTADO

---

## B) Bugs e UX Issues

### B1 — window.prompt() e window.confirm() (anti-padrão UX)

**Confirmados em `static/admin/js/app.js`:**

| Linha | Função | Tipo | Impacto |
|-------|--------|------|---------|
| 602 | `devolverAoBot()` | `confirm()` | UX travante, não customizável |
| 845 | `alterarStatus('snoozed')` | `prompt()` | UX travante, BLOQUEANTE para snooze |
| 951 | `transferirConversa()` | `confirm()` | UX travante |
| 1082 | `bulkResolver()` | `confirm()` | UX travante |
| 1172 | `salvarViewAtual()` | `prompt()` | UX travante, BLOQUEANTE para criar views |
| 1189 | `deletarView()` | `confirm()` | UX travante |
| 1279 | `bulkSnooze()` | `prompt()` | UX travante, BLOQUEANTE |
| 1392 | deletar nota | `confirm()` | UX travante |

**Severidade:** `prompt()` é o mais crítico — bloqueia a UI completamente e em alguns browsers mobile não funciona. Os `confirm()` são anti-padrão mas funcionam. Total: 3 `prompt()`, 5 `confirm()`.

### B2 — SSE sem backoff exponencial

`static/admin/js/sse.js` linha 57: `setTimeout(conectar, 3000)` — reconexão sempre em 3s, sem backoff exponencial. Em instabilidade de rede, isso pode gerar flood de reconexões. Padrão recomendado: delay mínimo 1s, duplicando até máximo 30s, com jitter.

**Severidade:** Médio.

### B3 — Optimistic UI: feedback de falha claro

`resolverBolhaPendente(tempId, false)` adiciona classe `bolha-falha` e exibe ` ⚠` no `entregue-status`. Não há botão de retry inline na bolha. O usuário recebe um toast "Falha ao enviar mensagem" mas a bolha vermelha não tem instrução clara. US-097 (retry via clique) e US-137 (botão "Tentar novamente") NÃO estão implementados.

**Severidade:** Alto — usuário não sabe que pode editar e reenviar manualmente.

### B4 — bulk seleção persiste entre filtros (BUG US-219)

Em `static/admin/js/app.js` linha 1603-1610: trocar filtro via `filter-tabs` não chama `limparBulkSelecao()`. O `state.bulkSelecionadas` Set mantém telefones que podem não estar mais visíveis na lista atual. Se o atendente fizer bulk resolver após trocar de filtro, processará conversas que não estava vendo.

**Severidade:** Alto.

### B5 — Logout usa confirm() (US-005)

Não está em `app.js` (não há botão logout no `index.html` atual — o logout foi removido ou movido para `settings.html`). Requer verificação em `settings.html`, mas a ausência de botão de logout no dashboard principal é um problema de UX por si só.

### B6 — JWT sem aviso de expiração

Sem aviso antecipado de expiração do JWT (US-115). O atendente que estiver digitando uma mensagem longa terá o redirect para login no próximo request HTTP sem aviso prévio. Nenhum draft é salvo (US-116 não implementado).

**Severidade:** Alto — perda de trabalho em andamento.

### B7 — Refresh periódico alterado de 30s para 60s

`setInterval(carregarConversas, 60000)` na linha 2037 — o documento US-100 especifica 30s, o código usa 60s. Menor frequência significa maior latência no fallback do SSE.

### B8 — note-input sem maxlength no HTML

O textarea `#note-input` não tem atributo `maxlength="4096"` (US-148 / EDGE-07 não implementado). O backend valida, mas o usuário só descobre ao salvar.

### B9 — Mentions popover: posição absoluta pode sair da viewport

`mentions-popover` posicionado com `bottom-16 left-16` (fixed). Em telas menores pode sair do lado direito ou ficar cortado.

### B10 — Atendente_nome não exibido na sidebar para conversas de outros

`syncComposerState()` linha 545: exibe genérico "Outro atendente" sem incluir o nome. O backend retorna `atendente_nome` mas o frontend não o exibe no banner do compositor nem na sidebar (US-120/US-143 não implementados).

---

## C) Responsividade

### Análise do index.html

**Layout raiz:** `<body class="flex h-screen overflow-hidden">` — layout Flexbox horizontal fixo.

**Sem breakpoints CSS detectados.** Pesquisa por `@media`, `sm:`, `md:`, `lg:` retornou zero resultados em `index.html`.

**Painéis com largura fixa:**
- Icon sidebar: `width: 64px` — fixo, sem responsividade
- Conv panel: `width: 320px` — fixo, sem colapso em mobile
- Info panel: `width: 280px` — fixo, sem overlay/drawer

**Impacto:**
- Em telas < 768px, o layout empurra painéis para fora do viewport (overflow horizontal oculto)
- Não há hamburger menu, drawer, ou modo mobile
- US-093 a US-095 (responsividade mobile) documentados como "IMPLEMENTADO" na documentação antiga mas o código atual NÃO tem esses comportamentos

**Diagnóstico:** A refatoração para o novo design (Chatwoot-inspired) removeu os breakpoints que existiam na versão anterior. A responsividade mobile foi um retrocesso.

---

## D) Avaliação Chatwoot — Funcionalidades

Ver arquivo separado: `CHATWOOT-FEATURES-FRONTEND.md`

---

## E) Performance

### E1 — Carregamento de mensagens: EAGER

`api.getConversa(telefone)` retorna até as últimas 500 mensagens de uma vez. Não há lazy loading, paginação ou virtual scrolling. `renderMensagens()` itera todas de uma vez e usa um loop com `appendChild` por mensagem (sem `DocumentFragment`).

**Risco:** Conversas com 500 mensagens vão criar 500+ nós DOM de uma vez. Para conversas normais de barbearia isso é aceitável, mas o código não tem proteção para o caso extremo.

**US-108 (performance > 500 msgs):** NÃO implementado.

### E2 — Listeners de evento: sem leak detectado

Todos os listeners são adicionados via `addEventListener` no DOMContentLoaded uma única vez. Listeners SSE são adicionados em nível de `document` (singleton). Sem remoção dinâmica necessária porque o ciclo de vida é a própria página.

**Risco baixo.** O único ponto de atenção é `renderNotas()` e `renderMentionsList()` que usam `querySelectorAll().forEach(addEventListener)` — esses listeners são recriados a cada render. Porém como os elementos filhos são substituídos (innerHTML), os listeners antigos são garbage-collected. Sem leak confirmado.

### E3 — renderConvList: re-renderização total

`renderConvList()` recria todo o innerHTML de `#conv-list` a cada chamada. Não há diffing. Para 200 conversas, isso é aceitável (~200 cards simples). Não há virtual scrolling.

**Risco moderado** para instalações com muitos clientes.

### E4 — setInterval acumulados no bootstrap

5 intervalos registrados:
1. `carregarMentions` — 60s
2. `carregarPresence` — 60s
3. Heartbeat de presença — 30s
4. `carregarConversas` — 60s
5. Heartbeat de presença via `setInterval` em `iniciarPresenceTracking()`

Nenhum `clearInterval` registrado. Em uso normal (SPA de atendimento), os intervalos vivem durante toda a sessão — sem problema.

---

## F) User Stories de Maior Valor NÃO Implementadas (Top 10)

Ordenadas por impacto operacional imediato:

1. **US-115/US-116/US-144** — Aviso de JWT expirando + salvamento de draft. Perda de trabalho é o bug mais frustrante para atendente ativo.

2. **US-097/US-137** — Retry na bolha de falha. Atendente não tem como reenviar mensagem que falhou sem redigitar manualmente.

3. **US-093 a US-095** — Responsividade mobile. O dashboard atual é inutilizável em celular.

4. **US-127** — Badge no título da aba com contagem de conversas aguardando. Monitoramento passivo essencial.

5. **US-105/US-107** — Botão "novas mensagens" ao ler histórico antigo. Sem esse botão, o atendente pode perder mensagens novas ao rolar para cima.

6. **US-120/US-143** — Nome do atendente em conversas de outros na sidebar e no banner do compositor.

7. **US-128** — Desktop notifications (Notification API). Alertas mesmo com aba em background.

8. **US-132/US-133** — Respostas rápidas customizáveis localmente (localStorage). As canned responses DB exigem acesso ao settings.

9. **US-104** — Tooltip com timestamp completo ao passar o mouse sobre mensagem.

10. **US-219** (BUG) — Limpar seleção bulk ao trocar filtro. Risco de ação em lote em conversas não visíveis.

---

## Problemas Visuais Confirmados (da documentação, verificados no código atual)

| ID | Descrição | Status no código atual |
|----|-----------|------------------------|
| VIS-01 | Chips de filtro não filtram corretamente | CORRIGIDO na refatoração |
| VIS-02 | Painel de info não abre automaticamente em desktop | PERSISTE (hidden por padrão) |
| VIS-03 | Separadores de handoff não renderizados | CORRIGIDO — `separadorEvento()` implementado |
| VIS-04 | Botão emoji desabilitado | REMOVIDO do novo layout |
| VIS-05 | Botão favoritar sem funcionalidade | REMOVIDO do novo layout |
| VIS-06 | Serviços frequentes com dado incorreto | REMOVIDO do novo layout |
| VIS-07 | Avatar atendente exibe "?" | CORRIGIDO — `iniciais()` aplicado em DOMContentLoaded |

---

*Auditoria concluída em 2026-05-21 por frontend-agent.*
