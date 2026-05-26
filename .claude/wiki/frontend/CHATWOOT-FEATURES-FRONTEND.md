# CHATWOOT-FEATURES-FRONTEND.md — Avaliação de Funcionalidades Chatwoot

**Data:** 2026-05-21
**Auditor:** frontend-agent
**Contexto:** Avaliação de viabilidade para implementação em Vanilla JS sem build step

---

## 1. Modal Datepicker para Snooze (substituir window.prompt)

### Descrição
Substituir os 3 usos de `prompt()` (snooze individual, bulk snooze, salvar view) por modais HTML/CSS com inputs adequados. Para snooze, um seletor de duração (1h, 4h, 8h, 24h, 48h, custom) ou um `<input type="datetime-local">` nativo.

### Viabilidade em Vanilla JS
**Alta.** `<input type="datetime-local">` é nativo em todos os browsers modernos. Criar modal com overlay, opções de atalho e botão confirmar/cancelar é trivial em vanilla JS + CSS custom properties já existentes no projeto.

### Implementação proposta
- Modal reutilizável `#modal-snooze` com campo `<input type="datetime-local" id="snooze-datetime">` e botões de atalho rápido (1h, 4h, 24h, 1 semana)
- Função `abrirModalSnooze(callback)` que retorna uma Promise resolvida com o datetime escolhido
- Substituir as 3 chamadas `prompt()` por `await abrirModalSnooze()`
- Mesmo modal pode servir para "salvar view" (apenas com `<input type="text">`)

### Esforço estimado
**3 horas** — HTML do modal (1h), lógica JS + Promise-based API (1h), CSS e polimento (1h)

### Quick win: Sim
Impacto visual imediato, elimina o maior anti-padrão de UX do dashboard.

---

## 2. Reconexão SSE com Backoff Exponencial

### Descrição
Substituir `setTimeout(conectar, 3000)` em `sse.js` por um algoritmo de backoff exponencial com jitter: delays crescentes (1s, 2s, 4s, 8s... até 30s) e aleatorização para evitar thundering herd quando múltiplos atendentes reconectam simultaneamente.

### Viabilidade em Vanilla JS
**Alta.** Lógica pura de cálculo de tempo. Zero dependências externas.

### Implementação proposta
```
let _delay = 1000; // ms
const MAX_DELAY = 30000;
// Em cada reconexão:
const jitter = Math.random() * 0.3 * _delay;
setTimeout(conectar, _delay + jitter);
_delay = Math.min(_delay * 2, MAX_DELAY);
// Em conexão bem-sucedida:
_delay = 1000; // reset
```

### Esforço estimado
**0.5 hora** — Modificação cirúrgica de ~10 linhas em `sse.js`.

### Quick win: Sim
Mínimo esforço, máximo benefício em ambientes de rede instável.

---

## 3. Analytics Básico (Painel de Métricas)

### Descrição
Painel simples no dashboard mostrando: número de conversas resolvidas hoje, tempo médio de resposta por atendente (estimado), conversas por atendente, e conversas em aberto vs. resolvidas nas últimas 24h.

### Viabilidade em Vanilla JS
**Média.** O frontend pode calcular métricas simples a partir dos dados já presentes em `state.conversas`. Para métricas históricas (tempo médio de resposta, resolvidas hoje), é necessário novo endpoint no backend.

### Dependências de backend
- `GET /admin/analytics` retornando `{resolvidas_hoje, tempo_medio_resposta_min, por_atendente: [{nome, resolvidas, em_atendimento}]}`
- Ou extensão de `GET /admin/conversas` para incluir metadados temporais

### Implementação proposta
- Tab "Analytics" na icon-sidebar (`data-nav="analytics"`)
- Painel lateral que substitui a conv-list ao ativar
- Cards de métricas em grid 2x2: resolvidas hoje, aguardando agora, atendentes online, tempo médio
- Tabela simples de conversas por atendente
- Atualização a cada 60s (sem SSE necessário)

### Esforço estimado
**6 horas** — Backend endpoint (2h, backend-agent), HTML/CSS do painel (2h), lógica JS + polling (1h), polimento (1h)

### Quick win: Não (depende de backend)

---

## 4. Audit Trail Visual por Conversa (Linha do Tempo)

### Descrição
Dentro do painel de informações do cliente, uma seção "Histórico de Eventos" mostrando a linha do tempo: "Bot ativo → João assumiu (14:32) → Devolveu ao bot (15:01) → Maria assumiu (15:45) → Resolvida (16:00)".

### Viabilidade em Vanilla JS
**Média.** O frontend já detecta mudanças de origem em `renderMensagens()` e insere `separadorEvento()`. O problema é que o backend não retorna os eventos de handoff como entidades distintas — eles são inferidos pela mudança do campo `origem` nas mensagens.

### Dependências de backend
- Novo endpoint `GET /admin/conversa/{telefone}/eventos` retornando lista de eventos `[{tipo, atendente_nome, criado_em}]`
- Ou extensão do modelo de histórico para incluir mensagens com `intencao='transferencia'` já implementadas
- Os registros de transferência já são gravados em `HistoricoConversa` com `intencao='transferencia'` — pode ser aproveitado

### Implementação proposta
- Seção colapsável "HISTÓRICO DE EVENTOS" no `#info-panel`
- Linha do tempo CSS (vertical, com dots e linhas)
- Renderização a partir de mensagens com `intencao` especial, sem novo endpoint necessário se o backend incluir `intencao` nos dados de `GET /admin/conversa/{telefone}`

### Esforço estimado
**4 horas** — CSS da linha do tempo (1.5h), lógica JS de agrupamento (1.5h), adaptação do backend para incluir intencao (backend-agent, 1h)

### Quick win: Parcial (CSS pode ser feito antes do backend)

---

## 5. Role Badge no Perfil (Supervisor vs. Agente)

### Descrição
Exibir na icon-sidebar e no painel de atendentes um badge visual distinguindo supervisores de agentes. Supervisores teriam acesso a funcionalidades adicionais (ver conversas de outros, bulk atribuir, etc.).

### Viabilidade em Vanilla JS
**Alta** para o frontend. A lógica de UI é trivial: verificar `state.eu.papel` (ou `localStorage.getItem('atendente_papel')`) e renderizar badge condicionalmente.

### Dependências de backend
- Coluna `Atendente.papel` (migration necessária: `'agente'` | `'supervisor'`)
- Campo `papel` no payload de login: `{token, nome, atendente_id, papel}`
- Verificações de permissão no backend para endpoints admin-only

### Implementação proposta Frontend
- `localStorage.setItem('atendente_papel', data.papel)` no login
- `state.eu.papel` lido no bootstrap
- Badge no `#my-avatar`: anel dourado para supervisor
- Condicional em `syncComposerState()`: supervisores veem botão "Transferir forçado"
- Tab settings mostra opções extras para supervisor

### Esforço estimado
**4 horas** — Migration + backend (backend-agent, 2h), UI badges (1h), condicionais de funcionalidade (1h)

### Quick win: Não (requer migration de banco)

---

## 6. Settings Básico (Mudar Senha + Preferências de Notificação)

### Descrição
A página `settings.html` já existe para gerenciar labels e canned responses. Adicionar tab "Minha Conta" com: formulário de mudança de senha (senha atual + nova + confirmar), e toggle de preferências: notificações desktop ativas, som ativo, filtro de status padrão ao carregar.

### Viabilidade em Vanilla JS
**Alta.** A estrutura de `settings.html` já está modularizada por tabs. Adicionar nova tab é direto.

### Dependências de backend
- `PATCH /admin/atendentes/me/senha` com `{senha_atual, nova_senha}` — novo endpoint

### Implementação proposta
- Tab "Minha Conta" em `settings.html`
- Formulário de senha: `<input type="password">` x3, validação client-side (nova ≠ atual, min 8 chars, confirmação)
- Seção "Notificações": toggle para som, toggle para desktop notifications (chama `Notification.requestPermission()`)
- Seção "Preferências": select de status padrão ao carregar (persiste em localStorage)
- Preferências persistem em `localStorage('atendente_prefs')` como JSON

### Esforço estimado
**5 horas** — Backend endpoint mudança de senha (backend-agent, 1h), HTML/CSS tab (1.5h), lógica JS formulário + validação (1.5h), preferências localStorage (1h)

### Quick win: Parcial (preferências localStorage são 100% frontend, 1h)

---

## Resumo Comparativo

| # | Funcionalidade | Viabilidade | Depende de Backend | Esforço (h) | Quick Win |
|---|----------------|-------------|-------------------|-------------|-----------|
| 1 | Modal datepicker snooze | Alta | Não | 3h | Sim |
| 2 | SSE backoff exponencial | Alta | Não | 0.5h | Sim |
| 3 | Analytics básico | Média | Sim (novo endpoint) | 6h | Não |
| 4 | Audit trail linha do tempo | Média | Parcial | 4h | Parcial |
| 5 | Role badge supervisor | Alta | Sim (migration) | 4h | Não |
| 6 | Settings mudar senha + prefs | Alta | Sim (endpoint senha) | 5h | Parcial |

---

## Recomendação de Prioridade

### Implementar imediatamente (sprint 1):
1. **SSE backoff exponencial** — 30 min, zero risco, impacto em toda a operação
2. **Modal datepicker snooze** — 3h, elimina o pior anti-padrão de UX, zero dependências externas

### Implementar em sprint 2 (com backend-agent):
3. **Role badge** — desbloqueia separação supervisor/agente que já está parcialmente implementada no backend (Fase 2 das US)
4. **Settings mudança de senha** — funcionalidade básica esperada em qualquer sistema

### Roadmap (sprint 3+):
5. **Audit trail** — valor alto para supervisores, requer coordenação backend
6. **Analytics** — requer novo endpoint, mas entrega visibilidade operacional que hoje é zero

---

*Gerado em 2026-05-21 por frontend-agent.*
