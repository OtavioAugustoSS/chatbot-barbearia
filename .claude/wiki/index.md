# index.md — Catálogo Mestre da Memória do Time

## Convenções
- Toda nota persistente criada por qualquer teammate **DEVE** ser registrada aqui
- Formato: `- [Título](caminho/relativo.md) — domínio — uma-linha sobre o conteúdo`
- Manter agrupado por domínio (business-rules, decisions, backend, frontend)
- Sem limite de tamanho; é o índice canônico

## Business Rules (PO)
- [BR-AUDIT-001: Auditoria de Cobertura — User Stories e Regras de Negocio](business-rules/BR-AUDIT-001-coverage-gaps.md) — PO — lista completa de gaps: stories PARCIAL/NAO IMPLEMENTADO, regras hardcoded sem BR formal, problemas visuais sem story de correcao
- [BR-AUDIT-002: Avaliacao de Valor — Funcionalidades Chatwoot nao Implementadas](business-rules/BR-AUDIT-002-chatwoot-backlog.md) — PO — avaliacao Alto/Medio/Baixo das 6 funcionalidades Chatwoot; top 3 recomendacoes priorizadas
- [BR-001: Anti-Agendamento Absoluto](business-rules/BR-001-anti-agendamento.md) — PO — bot NUNCA agenda, cancela ou remarca; sempre redireciona AppBarber; 6 camadas de proteção no código incluindo regex anti-appointment
- [BR-002: Contato Pessoal do Fred](business-rules/BR-002-contato-fred.md) — PO — numero (38) 99897-0661 compartilhado SOMENTE se cliente perguntar explicitamente por Fred; intencao=tirar_duvida (nunca chamar_recepcao)
- [BR-003: Formatacao de Mensagens](business-rules/BR-003-formatacao-mensagens.md) — PO — IA e canonicas usam `<br>`; operador humano usa `\n` direto; _normalizar_texto_envio() converte antes do envio Meta API
- [BR-004: Handoff Humano — Gatilhos e Reativacao](business-rules/BR-004-handoff-triggers.md) — PO — dois gatilhos: chamar_recepcao e transbordo_falha; despedida ANTES de reativar bot; auto-reativacao apos BOT_REATIVAR_APOS_HORAS; caso Fred nao aciona handoff
- [BR-005: Modos de Operacao bot_only vs hibrido](business-rules/BR-005-modo-bot-only-vs-hibrido.md) — PO — diferencias de comportamento: handoff real, dashboard admin, SSE, variante de canonica de agendamento, oferta de recepção em perguntas de slot
- [BR-006: Escopo de Conteudo do Bot](business-rules/BR-006-escopo-bot-conteudo.md) — PO — bot responde APENAS sobre Barbearia Bolshoi; topicos proibidos; frase padrao de recusa com intencao tirar_duvida
- [BR-007: Mecanismo Anti-Drift (Ancora de Regras)](business-rules/BR-007-anti-drift-ancora.md) — PO — ANCORA_ANTI_DRIFT injetada em conversas >= 4 turnos; posicao antes da mensagem do usuario; custo ~200 tokens; threshold reduzido de 6 para 4 no QW-B4
- [BR-008: Servicos Nao Oferecidos e Nomes Populares de Corte](business-rules/BR-008-servicos-nao-oferecidos.md) — PO — recusa sem prometer servico futuro; mapeamento canônico de 16 estilos populares para servico "Corte"; caso especial "Corte com Desenho"
- [BR-009: Injecao de Servicos e Barbeiros na IA](business-rules/BR-009-injecao-servicos-barbeiros-ia.md) — PO — formato de injecao com separador ref:; dados primarios vs referencia interna; cache 5 min; categorias barbearia vs estetica; sanitizacao QW-B2
- [BR-010: Gestao de Horarios de Funcionamento](business-rules/BR-010-horarios-db-vs-hardcoded.md) — PO — tabela horarios e fonte primaria; dict hardcoded e fallback; sincronizacao obrigatoria em 4 arquivos ao mudar horario; limitacao de feriados pontuais
- [BR-011: Decisoes sobre GAP-06 e GAP-08](business-rules/BR-011-gap06-gap08-decisoes.md) — PO — GAP-06: sem auto-atribuicao, alerta visual de tempo de espera (Sprint 0.3.0); GAP-08: reativacao silenciosa mantida + frase de contexto na primeira msg apos timeout
- [BR-012: Personalizacao por Nome do Cliente](business-rules/BR-012-personalizacao-nome-cliente.md) — PO — nome injetado via sistema quando disponivel; usar com moderacao; apenas primeiro nome; origem do dado: contacts[].profile.name do Meta
- [BR-013: Cobertura de FAQ pelas Respostas Canonicas](business-rules/BR-013-canonicas-cobertura-faq.md) — PO — auditoria de 6 gaps; acoes: expandir regex FAQ_ESTRUTURA para "crianca", adicionar regra de feriados ao prompt; telefone comercial pendente de confirmacao

## Decisões Arquiteturais — ADRs (Architect)

- [ADR-001: Convenções de Schema do Banco de Dados](decisions/ADR-001-schema-naming-conventions.md) — architect — naming, tipos, nullability, migrations, timestamps naive
- [ADR-002: Padrão de Tratamento de Erros HTTP](decisions/ADR-002-http-error-handling-pattern.md) — architect — mapeamento de situações para status codes, regras de logging, diferença webhook vs admin
- [ADR-003: Política de Retry e Ausência de Circuit Breaker para NVIDIA NIM](decisions/ADR-003-nvidia-nim-retry-policy.md) — architect — tenacity 3 tentativas, backoff exponencial, ausência de circuit breaker documentada e aceita
- [ADR-004: Estratégia de Paginação — Offset/Limit](decisions/ADR-004-pagination-offset-limit.md) — architect — offset/limit escolhido sobre cursor pagination, justificativa de volume, envelope padronizado
- [ADR-005: Contrato SSE — Formato de Eventos e Heartbeat](decisions/ADR-005-sse-contract.md) — architect — catálogo completo dos 9 tipos de evento SSE, heartbeat 25s, política de drop-oldest
- [ADR-006: Sanitização Pré-Parse de JSON da IA e Política de Fallback](decisions/ADR-006-ai-json-fragility-sanitization.md) — architect — strip de markdown, validação de enum, anti-agendamento regex, fallback transbordo_falha
- [ADR-007: Frontend — Vanilla JS, Estrutura de Arquivos e Proibição de Frameworks](decisions/ADR-007-frontend-vanilla-js-structure.md) — architect — sem bundler, sem frameworks, estrutura de 3 arquivos JS, regras para bibliotecas via CDN; addendum FASE3: desvios QW-F1 (backoff estático) e SP-1 (prompt() não removidos) documentados
- [ADR-008: Padrão Promise-based para Modais de Confirmação e Input](decisions/ADR-008-promise-based-modal-pattern.md) — architect — elimina window.prompt() com modais vanilla JS assíncronos; padrão de implementação e CSS; substitui SP-1 não entregue na FASE 3
- [ADR-009: Atomicidade Parcial em Bulk Actions e Ordem de SSE](decisions/ADR-009-bulk-action-atomicity.md) — architect — documenta comportamento intencional de atomicidade parcial no bulk_acao; addendum ADR-005 sobre bulk_aplicado com falhas parciais
- [ADR-010: Tratamento de Exceções em Background Tasks do Webhook](decisions/ADR-010-background-task-exception-handling.md) — architect — política de captura de exceção raiz em tarefa_em_segundo_plano_ia; documenta risco de starvation de lock e mitigação futura (TD-013)
- [ADR-011: Ausência de RBAC nos Endpoints Admin](decisions/ADR-011-rbac-absence-admin-endpoints.md) — architect — documenta 5 categorias de endpoints sem restrição de role; aceita débito com mitigações compensatórias; define critérios para implementar RBAC
- [ADR-012: Fix Compositor Layout + Mídia Async + Assume/Devolver Gaps](decisions/ADR-012-compositor-layout-midia-async.md) — architect — 5 decisões: renomear CSS #composer-area→#composer (D1); mídia endpoint sync confirmado correto (D2); canned popover position:fixed+JS (D3); remover double border attach-preview (D4); uniformizar botões compositor 36px (D5)

## Análises Técnicas (Architect)

- [TECH-DEBT-001: Débito Técnico Priorizado](decisions/TECH-DEBT-001.md) — architect — 16 itens de débito técnico (revisão 2026-05-22: +TD-011 _auto_unsnooze sem índice, +TD-012 NOT IN ineficiente, +TD-013 lock sem timeout, +TD-014 dedupe TTL curto, +TD-015 intencao String(30), +TD-016 SSE status inválido — corrigido)
- [CHATWOOT-VIABILITY: Análise de Viabilidade Técnica](decisions/CHATWOOT-VIABILITY.md) — architect — análise de RBAC, analytics, automation rules e audit trail; esforços, riscos e ordem de implementação recomendada

## Backend (Backend Developer)
- [AI Quality Audit](backend/AI-QUALITY-AUDIT.md) — backend — Auditoria completa IA + pre-AI layers: 14 problemas mapeados (2 críticos, 3 médios, 9 baixos), evidência de erro real confirmada em erro_ia_debug.txt
- [Quick Wins](backend/QUICK-WINS.md) — backend — 5 melhorias mais impactantes ordenadas por esforço crescente (10–30min cada)
- [SPRINT-FIXES](backend/SPRINT-FIXES.md) — backend — Fase 3: QW-B1 JSON fallback, QW-B2 strip ref, QW-B3 booking regex, QW-B4 anti-drift, SP-2 endpoint reativar atendente

## Frontend (Frontend Developer)
- [DASHBOARD-AUDIT](frontend/DASHBOARD-AUDIT.md) — frontend — Auditoria completa: bugs confirmados, cobertura de US, responsividade, performance (2026-05-21)
- [CHATWOOT-FEATURES-FRONTEND](frontend/CHATWOOT-FEATURES-FRONTEND.md) — frontend — 6 funcionalidades Chatwoot avaliadas: viabilidade vanilla JS + esforço estimado (2026-05-21)
- [SPRINT-FIXES](frontend/SPRINT-FIXES.md) — frontend — FASE 3: QW-F1 backoff SSE, QW-F2 badge título aba, QW-F3 limpar bulk ao trocar filtro, QW-F4 separadores handoff com nome+hora, SP-1 modais datepicker/input substituindo 3x prompt()

## User Stories (PO)
- [US-GAP-01: Reativar Atendente Desativado](../docs/user-stories/US-GAP-01-reativar-atendente.md) — PO — backend IMPLEMENTADO (SP-2); CA-07 frontend PENDENTE (botao na UI de gestao de atendentes)
- [US-GAP-02: Mensagem de Contexto apos Reativacao por Timeout](../docs/user-stories/US-GAP-02-reativacao-timeout.md) — PO — derivada de BR-011/GAP-08; backend PENDENTE; necessita migration + logica em webhook.py
- [US-AD-001 a US-AD-015: User Stories Assume/Devolver](../docs/user-stories/assume-devolver-US.md) — PO — 15 cenarios de handoff humano-bot; 1 bug (snoozed_until) + 5 gaps documentados

## QA (QA Engineer)
- [QA ui-ux-enhancements-2026-05-26](qa/ui-ux-enhancements-2026-05-26.md) — qa — Auditoria das 15 melhorias UI/UX (Tasks #1/#2/#3): 3 bugs corrigidos, 5 infos, APROVADO
- [FINAL_REPORT](qa/FINAL_REPORT.md) — qa — Relatório final QA full sweep: 43 testes PASS, 11 achados (5 resolved, 2 open decisão humana, 4 open doc P3), veredicto CONDICIONAL p/ prod
- [FINDINGS](qa/FINDINGS.md) — qa — Achados incrementais completos (Blocos 1–4): análise estática, harness pytest, E2E Playwright, loop fix Fase D

## Releases
- [Release 0.1.0](../docs/release/0_1_0.md) — lead — Sprint 0.1.0: 5 backend quick wins + 5 frontend quick wins + 2 sprint items + 8 ADRs + 5 BRs
- [Release 0.2.0](../docs/release/0_2_0.md) — architect — Sprint 0.2.0: 10/10 goals PASS (design tokens, mobile, chips fix, JWT warning, draft save, CA-07, retry, bulk UI, finish_reason, devolver status, SSE bulk)
