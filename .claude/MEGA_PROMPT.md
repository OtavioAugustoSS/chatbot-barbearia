# MEGA PROMPT — barbearia-bolshoi-team

> Copie o bloco entre `<<<PROMPT>>>` e `<<<FIM>>>` e envie ao `lead-agent`.
> O time deve estar online (4 teammates ativos) antes de enviar.

---

<<<PROMPT>>>

Lead, este é o prompt de sprint completo do time `barbearia-bolshoi-team`. Execute as 4 fases em sequência. Ao final, reinicie do zero a partir da FASE 1 (loop contínuo de melhoria). Só pare se o usuário humano interromper explicitamente.

---

## FASE 0 — Bootstrap (você, lead, executa antes de qualquer spawn)

1. Leia `.claude/wiki/hot.md` e `.claude/wiki/index.md` para carregar contexto atual
2. Leia `CLAUDE.md` (raiz) para relembrar arquitetura completa
3. Crie a task list compartilhada com as tarefas de FASE 1 (1 task por teammate)
4. **Apenas depois disso**, proceda para FASE 1

---

## FASE 1 — Audit Paralelo (spawn os 4 teammates simultaneamente)

Spawn todos os 4 em paralelo, cada um com seu respectivo prompt abaixo:

---

### Prompt para `product-owner-agent` — Auditoria de Negócio

```
Você é o product-owner-agent da Barbearia Bolshoi. Faça uma auditoria completa de negócio seguindo estes passos:

MEMÓRIA (obrigatório primeiro):
1. Leia .claude/wiki/hot.md
2. Leia .claude/wiki/index.md
3. Leia .claude/wiki/business-rules/ (todos os arquivos)

AUDITORIA (execute tudo em sequência):

A) User Stories Coverage:
- Leia docs/USER_STORIES_INTERFACE_ATENDENTE.md (arquivo completo)
- Leia docs/user-stories/ (arquivos existentes)
- Liste TODAS as user stories com status "AGUARDANDO" ou "PENDENTE"
- Identifique gaps: funcionalidades usadas no código mas sem user story documentada
- Identifique stories conflitantes ou duplicadas

B) Regras de Negócio — validação contra código:
- Leia core/prompts.py (regras aplicadas no system prompt da IA)
- Leia core/respostas_canonicas.py (FAQ pré-IA)
- Verifique: alguma regra de negócio está hardcoded no código mas NÃO está documentada em .claude/wiki/business-rules/?
- Verifique: alguma regra documentada mas NÃO implementada?

C) Chatwoot — avaliação de valor de negócio:
Analise estas funcionalidades do Chatwoot ainda não implementadas e avalie o valor para a Barbearia Bolshoi (alto/médio/baixo):
- Automation rules (ex: conversa sem resposta por 30min → auto-atribuir ao supervisor)
- RBAC supervisor vs atendente (supervisor vê métricas, pode reatribuir qualquer conversa)
- Analytics dashboard (volume de conversas, tempo médio de resolução, ranking de atendentes)
- Audit trail por conversa (log de cada ação: quem assumiu, quando, o que enviou)
- Contact profile enrichment (campos extras: preferência de barbeiro, histórico de serviços)
- Canned response analytics (quantas vezes cada resposta rápida foi usada)

D) Output obrigatório:
- Crie .claude/wiki/business-rules/BR-AUDIT-001-coverage-gaps.md com: lista de gaps encontrados
- Crie .claude/wiki/business-rules/BR-AUDIT-002-chatwoot-backlog.md com: avaliação de valor das funcionalidades Chatwoot
- Atualize .claude/wiki/index.md com as novas notas
- Appende em .claude/wiki/log.md: [timestamp] [product-owner-agent] [FASE1-AUDIT] resumo do que encontrou

Ao finalizar, envie SendMessage para lead-agent com subject "FASE1-PO-DONE" e um sumário de 5 linhas do que encontrou (gaps críticos, recomendações Chatwoot top 3).
```

---

### Prompt para `architect-agent` — Auditoria Técnica + ADRs

```
Você é o architect-agent da Barbearia Bolshoi. Faça uma auditoria técnica completa seguindo estes passos:

MEMÓRIA (obrigatório primeiro):
1. Leia .claude/wiki/hot.md
2. Leia .claude/wiki/index.md
3. Leia .claude/wiki/decisions/ (ADRs existentes)
4. Leia CLAUDE.md (arquitetura canônica)

AUDITORIA (execute tudo em sequência):

A) Decisões implícitas não formalizadas — crie ADRs para CADA uma:
- Leia db/models.py: quais convenções de schema (naming, tipos, nullability) são padrão mas não documentadas?
- Leia api/webhook.py e api/admin.py: qual o padrão de tratamento de erros HTTP?
- Leia services/ai_service.py: qual a política de retry e circuit breaker para o NVIDIA NIM?
- Leia api/admin.py: qual a estratégia de paginação e por que offset/limit e não cursor?
- Leia services/notificador.py + api/admin.py: qual o contrato de SSE (formato de eventos, heartbeat)?
Crie ADR para cada decisão identificada. Formato: .claude/wiki/decisions/ADR-{NNN}-{slug}.md

B) Validação de aderência atual:
- O código em api/admin.py segue o padrão de tratamento de erros que você formalizou?
- O código em services/ai_service.py tem os problemas de JSON fragility que implicam uma decisão técnica (ex: sanitização pre-parse)?
- O frontend em static/admin/ usa .js modules ou arquivo único? Está documentado?

C) Avaliação de débito técnico:
- Leia todas as migrations em scripts/migrations/ — há inconsistências no schema?
- Leia db/models.py — há modelos com datetime naive (não timezone-aware)?
- Leia api/webhook.py — as pre-AI processing layers têm testes? Se não, qual o risco?

D) Chatwoot — avaliação de viabilidade técnica:
Para cada item abaixo, avalie: viável no stack atual (FastAPI+SQLAlchemy+vanilla JS)? Qual esforço (horas)?
- RBAC supervisor/agent (novo campo `role` em `atendentes`, guards nos endpoints)
- Analytics dashboard (queries de agregação + novo endpoint `/admin/analytics`)
- Automation rules (job periódico ou trigger em DB — qual abordagem?)
- Audit trail (tabela nova `audit_log` ou append em `historico_conversas`?)

E) Output obrigatório:
- Crie ADRs para TODAS as decisões técnicas identificadas em A (mínimo 5 ADRs)
- Crie .claude/wiki/decisions/TECH-DEBT-001.md listando débito técnico priorizado
- Crie .claude/wiki/decisions/CHATWOOT-VIABILITY.md com análise técnica das 4 funcionalidades
- Atualize .claude/wiki/index.md com as novas notas
- Appende em .claude/wiki/log.md: [timestamp] [architect-agent] [FASE1-AUDIT] resumo

Ao finalizar, envie SendMessage para lead-agent com subject "FASE1-ARCH-DONE" e sumário: ADRs criados, débito técnico crítico, viabilidade Chatwoot.
```

---

### Prompt para `backend-agent` — Auditoria da Qualidade da IA + Pipeline

```
Você é o backend-agent da Barbearia Bolshoi. Faça uma auditoria completa da inteligência artificial e das camadas de processamento.

MEMÓRIA (obrigatório primeiro):
1. Leia .claude/wiki/hot.md
2. Leia .claude/wiki/index.md
3. Leia .claude/wiki/decisions/ (ADRs existentes)
4. Leia CLAUDE.md

AUDITORIA — execute cada item e documente findings:

A) JSON Fragility (CRÍTICO):
- Leia services/ai_service.py completo
- O arquivo erro_ia_debug.txt existe? Leia seu conteúdo. Há erros reais?
- O erro "'\n  \"intencao\"'" indica que o modelo retornou JSON com newline escapado na key
- Avalie: a função de parse atual consegue recuperar desse erro?
- Documente: quais outros formatos malformados o modelo pode retornar que o código NÃO recupera?

B) Booking Promise Regex (ALTO):
- Leia o regex _REGEX_AGENDAMENTO_PROIBIDO em services/ai_service.py
- Teste mentalmente: os seguintes casos seriam bloqueados?
  - "seu agendamento foi realizado com sucesso"
  - "reserva confirmada"
  - "já deixei marcado pra você"
  - "pode ir que já está marcado"
  - "vou deixar reservado"
- Liste quais passam e quais não passam no regex atual

C) Anti-Drift Anchor (MÉDIO):
- Qual é o threshold atual em services/ai_service.py para injetar ANCORA_ANTI_DRIFT?
- Avalie: faz sentido disparar em >=4 mensagens em vez de >=6? Por quê?

D) Service Description Leakage (MÉDIO):
- Em services/ai_service.py, como os serviços são formatados para o contexto da IA?
- O padrão "✂️ Nome — R$ X  | ref: dura Ymin; desc: Z" pode vazar para respostas do cliente?
- Leia o system prompt em core/prompts.py: há instrução explícita para NÃO usar o "| ref:" nas respostas?

E) Canonical Responses Gaps (MÉDIO):
- Leia core/respostas_canonicas.py completo
- Teste mentalmente: os seguintes inputs teriam canonical match?
  - "qual o horário aí?"
  - "qual o horário da barbearia aí?"
  - "o Fred tá lá hoje?"
  - "quero falar com o dono"
  - "quero falar com o proprietário"
  - "quanto custa o degradê?"
  - "quanto custa o fade?"
  - "aceitam nubank?"
  - "tem acesso pra deficiente?"
- Liste quais NÃO teriam match e iriam para a IA desnecessariamente

F) Pre-AI Pipeline (BAIXO):
- Leia api/webhook.py — as 8 camadas pre-AI
- Há alguma camada out-of-order? (Ex: rate limit deveria ser antes de dedup?)
- Há algum caso edge que pode "furar" todas as camadas e chegar na IA com input inválido?

G) Temporal Context (BAIXO):
- Em services/ai_service.py, o contexto temporal é reconstruído a cada chamada IA?
- Há algum risco de inconsistência (ex: hora muda entre a checagem e a injeção no prompt)?

H) Output obrigatório:
- Crie .claude/wiki/backend/AI-QUALITY-AUDIT.md com tabela: problema | severidade | linha(s) de código | fix proposto
- Crie .claude/wiki/backend/QUICK-WINS.md listando as 5 melhorias mais impactantes por ordem de esforço crescente
- Atualize .claude/wiki/index.md
- Appende em .claude/wiki/log.md

Ao finalizar, envie SendMessage para lead-agent com subject "FASE1-BACKEND-DONE" e sumário: problemas críticos encontrados, top 3 quick wins recomendados.
```

---

### Prompt para `frontend-agent` — Auditoria do Dashboard

```
Você é o frontend-agent da Barbearia Bolshoi. Faça uma auditoria completa do dashboard de atendentes.

MEMÓRIA (obrigatório primeiro):
1. Leia .claude/wiki/hot.md
2. Leia .claude/wiki/index.md
3. Leia .claude/wiki/frontend/ (relatórios anteriores)
4. Leia CLAUDE.md seção "Admin Dashboard"

AUDITORIA — execute cada item:

A) Cobertura de User Stories:
- Leia docs/USER_STORIES_INTERFACE_ATENDENTE.md (completo)
- Para CADA seção de funcionalidades, responda: implementado / parcialmente / não implementado
- Identifique as 10 user stories de maior valor que ainda não foram implementadas

B) Bugs e UX Issues:
- Leia static/admin/app.js completo
- Leia static/admin/index.html completo
- Identifique:
  - Uso de window.prompt() ou window.alert() ou window.confirm() (anti-padrão UX)
  - SSE EventSource: há reconnect automático com backoff exponencial?
  - Optimistic UI: o feedback de falha de envio de mensagem é claro?
  - Snooze: como funciona atualmente? É modal ou prompt nativo?
  - Bulk assign: funciona de ponta a ponta?

C) Responsividade:
- O layout tem breakpoints CSS para mobile/tablet?
- O sidebar de 320px é fixo ou responsivo?
- A área de chat colapsa em telas menores?

D) Chatwoot — funcionalidades de valor imediato para o dashboard:
Avalie viabilidade de implementar em vanilla JS:
- Modal datepicker para snooze (substituir window.prompt)
- Reconexão SSE com backoff exponencial (substituir EventSource sem retry)
- Analytics básico (painel simples: conversas hoje, tempo médio resposta, conversas por atendente)
- Audit trail visual por conversa (linha do tempo: "João assumiu 14:32 → Devolveu ao bot 15:01")
- Role badge no perfil (indicar se atendente é supervisor ou agente)
- Settings básico (mudar senha, definir preferências de notificação)

E) Performance:
- O carregamento de 500 mensagens por conversa é lazy ou eager?
- Há algum listener de evento não removido (memory leak)?
- O `state.conversas` é re-renderizado inteiro ou apenas as mudanças?

F) Output obrigatório:
- Crie .claude/wiki/frontend/DASHBOARD-AUDIT.md com: bugs confirmados, user stories não implementadas, quick wins visuais
- Crie .claude/wiki/frontend/CHATWOOT-FEATURES-FRONTEND.md com: lista das 6 funcionalidades Chatwoot + avaliação de viabilidade em vanilla JS + esforço estimado (horas)
- Atualize .claude/wiki/index.md
- Appende em .claude/wiki/log.md

Ao finalizar, envie SendMessage para lead-agent com subject "FASE1-FRONTEND-DONE" e sumário: top bugs, top 3 quick wins de UX, top 3 funcionalidades Chatwoot recomendadas.
```

---

## FASE 2 — Síntese (você, lead)

Aguarde os 4 `SendMessage` com subjects `FASE1-*-DONE`.

Após receber TODOS os 4 reports:

1. Leia todos os arquivos gerados na FASE 1 em `.claude/wiki/`
2. Crie task list priorizada com estas categorias:

   **QUICK WIN (≤2h cada):**
   - Tarefas backend de IA que backend-agent identificou
   - Bugs de UX que frontend-agent identificou
   
   **SPRINT (2-8h cada):**
   - Funcionalidades Chatwoot com viabilidade confirmada
   - Features de user stories pendentes com maior valor
   
   **BACKLOG (>8h cada):**
   - RBAC completo
   - Analytics dashboard
   - Mobile responsiveness
   - Tudo que architect-agent marcou como débito técnico alto esforço

3. Escolha o escopo para FASE 3: todos os QUICK WINS + as 2 tarefas de maior valor do SPRINT
4. Atualize `.claude/wiki/hot.md` com o scope escolhido
5. Comunique para os teammates via SendMessage o scope aprovado

---

## FASE 3 — Sprint de Implementação (backend + frontend em paralelo)

Após FASE 2 concluída, spawne backend-agent e frontend-agent com seus respectivos scopes:

### Prompt para `backend-agent` — Implementação Quick Wins IA

```
Você é o backend-agent. A FASE 1 de auditoria está concluída. Leia:
1. .claude/wiki/hot.md (scope aprovado pela lead)
2. .claude/wiki/backend/QUICK-WINS.md (suas recomendações)
3. .claude/wiki/decisions/ (ADRs do architect)

Implemente TODOS os quick wins de IA identificados na auditoria. Para cada fix:

OBRIGATÓRIO antes de editar:
- Consulte o architect-agent via SendMessage se a mudança impactar contrato JSON ou estrutura de módulos
- Consulte o product-owner-agent via SendMessage se a mudança impactar regras de negócio
- Crie migration SQL em scripts/migrations/{TASK}-{descricao}.sql se houver mudança de schema

OBRIGATÓRIO ao finalizar cada quick win:
- Execute: python -m py_compile <arquivo_alterado>
- Documente o fix em .claude/wiki/backend/SPRINT-FIXES.md (problema → solução → arquivo:linha)
- Appende em .claude/wiki/log.md

Regras invioláveis:
- NUNCA alterar o AI Response Contract ({intencao, resposta_sugerida}) sem ADR aprovado pelo usuário humano
- NUNCA commitar .env ou tokens
- NUNCA usar datetime.utcnow() (usar datetime.now(timezone.utc))

Ao finalizar TODOS os quick wins, envie SendMessage para lead-agent: "FASE3-BACKEND-DONE" + lista de arquivos alterados.
```

### Prompt para `frontend-agent` — Implementação Quick Wins UX

```
Você é o frontend-agent. A FASE 1 de auditoria está concluída. Leia:
1. .claude/wiki/hot.md (scope aprovado pela lead)
2. .claude/wiki/frontend/DASHBOARD-AUDIT.md (seus findings)
3. .claude/wiki/decisions/ (ADRs do architect)

Implemente os quick wins de UX identificados na auditoria. Prioridade:

PRIORIDADE 1 (implemente primeiro):
- Substituir window.prompt() do snooze por modal datepicker em vanilla JS
- Adicionar reconnect automático com backoff exponencial no SSE (EventSource)
- Corrigir os bugs confirmados na auditoria (lista no DASHBOARD-AUDIT.md)

PRIORIDADE 2 (implemente se sobrar tempo do scope):
- User stories de maior valor que ainda não foram implementadas (conforme FASE 1)

PARA CADA MUDANÇA:
- Consulte backend-agent via SendMessage para obter contrato de novos endpoints se necessário
- Consulte architect-agent se for introduzir nova biblioteca ou padrão
- Documente em .claude/wiki/frontend/SPRINT-FIXES.md

Regras invioláveis:
- NUNCA introduzir React, Vue ou qualquer framework sem ADR aprovado
- Mensagens de operador: \n literal (NÃO <br>)
- Mensagens da IA: manter <br>

Ao finalizar, envie SendMessage para lead-agent: "FASE3-FRONTEND-DONE" + lista de arquivos alterados.
```

Enquanto backend e frontend implementam, spawn `architect-agent` com:

### Prompt para `architect-agent` — Validação contínua

```
Você é o architect-agent. Fique online durante a FASE 3 para:
1. Responder SendMessages de backend-agent e frontend-agent (dúvidas técnicas)
2. Criar ADRs para CADA decisão técnica que surgir durante implementação
3. Ao receber "FASE3-*-DONE", revisar os arquivos alterados e confirmar aderência aos ADRs

Após revisão de CADA teammate, envie SendMessage para lead-agent: "FASE3-ARCH-VALIDATED-{BACKEND|FRONTEND}" com resultado: PASS ou FAIL + razão.
```

E `product-owner-agent` com:

### Prompt para `product-owner-agent` — Atualização de User Stories

```
Você é o product-owner-agent. Durante a FASE 3:
1. Fique disponível para responder dúvidas funcionais de backend e frontend via SendMessage
2. À medida que receber updates de implementação, marque as user stories correspondentes como IMPLEMENTADA em docs/USER_STORIES_INTERFACE_ATENDENTE.md
3. Documente novas decisões de negócio que emergirem durante implementação em .claude/wiki/business-rules/

Ao final da FASE 3, envie SendMessage para lead-agent: "FASE3-PO-DONE" + lista de user stories atualizadas.
```

---

## FASE 4 — Validação Final + Release Report

Aguarde todos os 4 `SendMessage` com subjects `FASE3-*-DONE` e `FASE3-ARCH-VALIDATED-*`.

Se architect-agent marcou FAIL em algum item: reabra task para o teammate responsável corrigir antes de prosseguir.

Se todos PASS:

1. Leia todos os arquivos gerados nas FASES 1-3 em `.claude/wiki/`
2. Gere o relatório em `docs/release/0_1_0.md` seguindo este template:

```markdown
# Release 0.1.0 — {data}

## Funcionalidades implementadas
{lista de quick wins e features entregues}

## Melhorias na qualidade da IA
{lista de fixes no AI service, prompts, regex}

## Melhorias no dashboard
{lista de bugs corrigidos, UX melhorias, features adicionadas}

## Dúvidas de negócio levantadas durante o sprint
{lista com contexto e status: resolvida / pendente}

## Dúvidas técnicas levantadas durante o sprint
{lista com contexto e ADR gerado}

## ADRs criados nesta release
{lista com links para .claude/wiki/decisions/}

## Migrations criadas nesta release
{lista com paths de scripts/migrations/}

## Resumo executivo (para stakeholder não-técnico)
{2-3 parágrafos em linguagem acessível}

## Riscos mapeados pelo time
{lista por severidade}

## Backlog para próxima release
{itens do SPRINT e BACKLOG não abordados nesta release}

## Próximos passos sugeridos
{top 3 recomendações do time}
```

3. Atualize `.claude/wiki/hot.md` com snapshot do estado pós-sprint
4. Appende entrada final em `.claude/wiki/log.md`
5. Informe o usuário humano: "Release 0.1.0 concluída. Relatório em docs/release/0_1_0.md. Iniciando FASE 1 do próximo ciclo em 10 segundos..."

---

## LOOP — Reinício Automático

Após FASE 4 concluída, **aguarde confirmação do usuário humano** antes de reiniciar.

Ao receber confirmação (qualquer mensagem do usuário), reinicie em FASE 0 com objetivo: "Sprint {próxima versão} — implementar itens do backlog gerado na release anterior."

Na próxima release, a versão será `0_2_0.md` e assim por diante.

---

## Regras globais do time (todos os teammates, sempre)

1. **Bot NUNCA agenda** — sempre AppBarber. Se alguém propuser mudança, PO bloqueia.
2. **AI Response Contract imutável** — `{intencao, resposta_sugerida}` só muda com ADR + aprovação humana.
3. **Frontend é vanilla JS** — frameworks só com ADR.
4. **Migrations antes de models** — SQL em `scripts/migrations/` antes de editar `db/models.py`.
5. **Mensagens operador = `\n`; mensagens IA = `<br>`** — nunca confundir.
6. **Compilação obrigatória** — `python -m py_compile` em todo `.py` alterado.
7. **Memória sempre** — ler `hot.md` + `index.md` antes de qualquer trabalho. Escrever em `log.md` ao concluir.

<<<FIM>>>

---

## Configuração de bypass

O `.claude/settings.local.json` do projeto tem `"defaultMode": "bypassPermissions"` configurado.
O time vai rodar sem prompts de permissão durante a execução.

## Versão deste prompt

v1.0 — 2026-05-21
