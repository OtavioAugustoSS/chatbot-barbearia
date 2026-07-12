---
active: true
iteration: 1
session_id: a63348f8-1be4-4344-a2d5-609fba126267
max_iterations: 8
completion_promise: "IMPLEMENTACAO_COMPLETA"
started_at: "2026-05-27T02:56:29Z"
---

ORQUESTRAÇÃO DO TIME BARBEARIA-BOLSHOI — implementar todos os fixes da mega auditoria.

CONTEXTO: Você é o lead do time barbearia-bolshoi-team. O arquivo .claude/wiki/qa/fixes-status.md lista todos os fixes a implementar com status PENDENTE/FEITO. Trabalho: ler estado atual, atribuir próximo lote ao time, aguardar conclusão, QA valida, atualizar status, repetir.

PROTOCOLO DE CADA ITERAÇÃO:

1. LEIA O ESTADO ATUAL
   - Leia .claude/wiki/qa/fixes-status.md para identificar fixes PENDENTES
   - Leia .claude/wiki/log.md para ver o que já foi concluído

2. SE TODOS OS FIXES ESTIVEREM FEITOS:
   - Peça ao qa-agent validação final completa dos 3 arquivos principais
   - Se QA aprovar: output exato: <promise>IMPLEMENTACAO_COMPLETA</promise>
   - Se QA encontrar problemas: adicione-os ao fixes-status.md e continue

3. CRIAR O TIME SE NÃO EXISTIR
   - Use TeamCreate para criar barbearia-bolshoi-team
   - Agents definidos em .claude/agents/: frontend-agent, backend-agent, qa-agent, architect-agent, product-owner-agent

4. ATRIBUIR PRÓXIMO LOTE DE TASKS
   Prioridade: P0 completo → P1 completo → P2 (DS-* depois BE-*)

   Se P0 tem PENDENTES → atribua todos P0 em paralelo:
     frontend-agent: P0-1 (remover font-family Inter inline do body style), P0-3 (adicionar presence:{} ao state inicial), P0-4 (mover stroke-dasharray:30 de .bolha-tick svg para .bolha-tick.tick-animate svg), P0-5 (mudar .entregue-status.delivered para color:rgba(255,255,255,0.55))
     backend-agent: P0-2 (adicionar log.critical em main.py se META_APP_SECRET vazio)

   Se P0 done e P1 tem PENDENTES:
     frontend-agent: P1-1 (light theme messages-area bg), P1-2 (unread badge em conv assumida), P1-3 (transbordo_em em vez de ultima_mensagem_em), P1-4 (abrirConversa após mídia), P1-5 (classe avatar em renderConvList), P1-6 (empty state tablet), P1-10 (presence no state inicial)
     backend-agent: P1-7 (assumir dedup greeting), P1-8 (remover horários hardcoded de SYSTEM_PROMPT_BARBEARIA), P1-9 (data_ultima_interacao em bulk/assumir/devolver)

   Se P1 done e P2 tem PENDENTES:
     frontend-agent: DS-01 a DS-10 (tokens CSS)
     backend-agent: BE-01 a BE-06 (whatsapp retry, json try/except, bulk transaction, etc)

   USE TaskCreate para cada fix. USE SendMessage para notificar cada agent.

5. AGUARDE CONCLUSÃO
   - Agents escrevem em .claude/wiki/log.md ao terminar
   - Verifique o log

6. QA VALIDATION após cada lote
   - qa-agent lê arquivos modificados, confirma cada fix
   - Reporta [P0-1] APROVADO ou REPROVADO
   - Escreve em .claude/wiki/qa/validation-LOTE-N.md

7. ATUALIZE fixes-status.md: [ ] → [x] para aprovados

8. SE PENDENTES RESTAM: loop continua

REGRAS DO TIME:
- frontend-agent: vanilla JS apenas, sem frameworks
- backend-agent: SQLAlchemy ORM, migrations SQL antes de alterar models.py
- qa-agent: NÃO implementa, só valida
- Bot NUNCA agenda

ARQUIVOS: static/admin/index.html, static/admin/js/app.js, api/admin.py, api/webhook.py, services/whatsapp.py, core/prompts.py, main.py
