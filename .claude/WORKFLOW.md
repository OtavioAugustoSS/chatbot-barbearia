# Multi-Agent Workflow — Barbearia Bolshoi

Protocolo de comunicação entre agentes. Leia antes de iniciar qualquer tarefa multi-agente.

## Agentes Disponíveis e Seus Papéis

```
orchestrator     → coordena todos, tem tool Agent, define ordem de execução
po-agent         → valida regras de negócio (leitura, sem escrita de código)
dev-agent        → implementa código (FastAPI, SQLAlchemy, WhatsApp, IA)
db-agent         → migrações SQL e schema (MySQL + SQLAlchemy models)
qa-agent         → revisa qualidade, checklists, edge cases
prompt-engineer  → otimiza comportamento da IA (core/prompts.py, respostas_canonicas.py)
```

## Fluxos de Trabalho

### Feature com impacto no cliente
```
orchestrator
  → po-agent: "feature X está alinhada com negócio?"
  ↓ (se aprovado)
  → dev-agent: "implemente X"
  ↓
  → qa-agent: "revise implementação X"
  ↓ (se PASS)
  → atualiza AGENT_STATE.md
```

### Feature com mudança de schema
```
orchestrator
  → po-agent: "valida requisito"
  ↓
  → [em paralelo]:
      db-agent: "cria migration"
      dev-agent: "implementa lógica (assumindo schema novo)"
  ↓
  → qa-agent: "revisa tudo junto"
```

### Bug de comportamento da IA
```
orchestrator
  → po-agent: "confirma comportamento esperado"
  → prompt-engineer: "diagnóstica e corrige"
  → qa-agent: "valida cenário específico do bug"
```

### Mudança técnica sem impacto no cliente
```
dev-agent → qa-agent
(PO não precisa ser consultado)
```

## Arquivos de Estado

| Arquivo | Propósito | Quem escreve | Quem lê |
|---------|-----------|--------------|---------|
| `AGENT_STATE.md` | Log permanente de tarefas | orchestrator | todos |
| `.claude/handoff-context.md` | Contexto temporário entre agentes no mesmo ciclo | agente atual | agente seguinte |

## Protocolo de Handoff (`.claude/handoff-context.md`)

Formato padrão que cada agente deve escrever ao passar trabalho para o próximo:

```markdown
## Handoff: [agente-origem] → [agente-destino]
**Tarefa**: [o que foi pedido]
**O que foi feito**: [resumo]
**Decisão/Aprovação**: [aprovado/reprovado/condicionalmente aprovado]
**Contexto para o próximo agente**: [o que ele precisa saber]
**Arquivos modificados**: [lista de arquivos, se aplicável]
**Bloqueios**: [se houver]
```

## Regras de Comunicação

1. **PO deve aprovar antes de Dev implementar** qualquer mudança com impacto no cliente
2. **QA deve revisar antes de fechar** qualquer task (exceto mudanças de documentação pura)
3. **DB migration antes do código** que depende do novo schema
4. **Paralelo OK** quando não há dependência de dados entre as tarefas
5. **Agentes não escrevem código de outros domínios** — DB não altera lógica Python, Dev não cria migrations sem DB-agent

## Status de Tarefas

| Status | Significado |
|--------|-------------|
| `pending` | Aguardando início |
| `in_progress` | Agente trabalhando |
| `pending_qa` | Dev terminou, aguarda QA |
| `done` | QA aprovou |
| `blocked` | Problema impedindo progresso |

## Custo × Benefício

Antes de invocar um agente, pergunte:
- **Opus (PO, orchestrator, prompt-engineer)**: use para decisões complexas, ambíguas, ou críticas ao negócio
- **Sonnet (dev, qa)**: use para implementação e revisão — maioria das tarefas
- **Haiku (db)**: use para SQL e schema — tarefas bem definidas e mecânicas

Evite chamar agentes grandes para tarefas triviais. Um bugfix de uma linha não precisa de po-agent.
