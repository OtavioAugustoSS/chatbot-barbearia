# decisions/ — ADRs (Architecture Decision Records)

## Convenções
- **Owner:** `architect-agent`
- Naming: `ADR-{NNN}-{slug}.md` (ex: `ADR-001-migrations-manuais.md`)
- Numeração sequencial, NUNCA reutilizar número de ADR superseded
- Registrar no `../index.md` ao criar
- Template Michael Nygard:
  ```
  # ADR-NNN: {título}
  Status: proposto | aceito | substituído por ADR-XXX
  Data: YYYY-MM-DD
  Decisor: architect-agent
  Stakeholders consultados: {lista}

  ## Contexto
  ## Decisão
  ## Consequências
  ## Alternativas consideradas
  ```

## Decisões já implícitas no projeto (a formalizar quando relevante)
- Stack: FastAPI + SQLAlchemy + MySQL via pymysql
- IA: NVIDIA NIM (Llama 3.1 70B) via cliente OpenAI-compatible
- Contrato IA: JSON `{intencao, resposta_sugerida}` — mudança requer aprovação humana
- Migrations manuais (sem Alembic)
- Frontend admin: vanilla JS (sem framework)
- Modo de operação: `bot_only` (default) ou `hibrido` (com dashboard)
- Mensagens via background task (Meta 15s timeout)
- Deduplicação em `MensagemProcessada` (DB-level)
- Rate limit in-memory (não Redis)
