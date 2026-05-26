# ADR-001: Convenções de Schema do Banco de Dados
Status: aceito
Data: 2026-05-21
Decisor: architect-agent
Stakeholders consultados: backend-agent (código existente como fonte de verdade)

## Contexto

O projeto acumulou 16 migrations manuais e 13 modelos SQLAlchemy sem que as convenções de schema fossem documentadas formalmente. Novos teammates e migrations futuras precisam de referência canônica para manter consistência.

## Decisão

As seguintes convenções estão implicitamente estabelecidas no codebase e são agora formalizadas:

### Naming
- Tabelas: `snake_case` plural (ex: `usuarios`, `historico_conversas`, `atendentes`)
- Colunas: `snake_case` (ex: `nome_cliente`, `bot_ativo`, `criado_em`)
- FKs: `{tabela_referenciada_singular}_id` (ex: `atendente_id`, `label_id`)
- Índices: `idx_{tabela_abreviada}_{coluna(s)}` (ex: `idx_historico_telefone_data`)
- Constraints FK: `fk_{tabela}_{coluna}` (ex: `fk_resolved_por`, `fk_notas_editado_por`)

### Tipos canônicos por uso
| Caso de uso | Tipo SQLAlchemy | Tipo MySQL |
|---|---|---|
| Timestamps de auditoria | `DateTime` com `default=lambda: datetime.now(timezone.utc)` | `DATETIME` |
| Texto curto / enum-like | `String(N)` | `VARCHAR(N)` |
| Texto longo (mensagens) | `Text` | `TEXT` |
| Flags booleanas | `Boolean` | `TINYINT(1)` |
| PKs inteiras | `Integer, primary_key=True, autoincrement=True` | `INT AUTO_INCREMENT` |
| Preços | `Numeric(10, 2)` | `DECIMAL(10,2)` |
| JSON em texto (compat MySQL 5.7) | `Text` com `json.dumps/loads` manual | `TEXT` |

### Nullability
- Colunas de auditoria (`criado_em`) são `NOT NULL`
- Colunas opcionais (`editado_em`, `snoozed_until`) são `NULL` com `default=None`
- FKs com `ondelete='SET NULL'` são sempre `nullable=True`
- Campos de negócio críticos (`nome_servico`, `preco`, `senha_hash`) são `NOT NULL`

### Soft delete
- Entidades que precisam de desativação usam coluna `ativo BOOLEAN NOT NULL DEFAULT TRUE`
- Hard delete é usado em entidades derivadas com `CASCADE` (ex: `HistoricoConversa`, labels de usuario)

### Timestamps
- Todos os `DateTime` são gravados em UTC usando `datetime.now(timezone.utc)`
- MySQL armazena como naive (sem tz info) — `api/admin.py/_iso_utc()` reaplica `timezone.utc` na serialização
- **Problema documentado**: naive datetime no DB pode causar confusão se o servidor mudar de fuso (ver TECH-DEBT-001)

### Migrations
- Prefixo sequencial: `TASK{NNN}` (legacy) ou `{NNNN}` com zero-fill (novo padrão)
- Uma migration por arquivo SQL
- Idempotência: usar `IF NOT EXISTS` e `ON DUPLICATE KEY UPDATE` quando possível

## Consequências

- Positivo: consistência garantida em migrations futuras
- Positivo: teammates podem adicionar colunas sem perguntar ao architect para cada detalhe
- Negativo: não há validação automatizada das convenções — depende de review manual
- Risco: TASK017 e TASK015 foram criados antes do padrão `0NNN` — convivem no mesmo diretório sem problema funcional, mas a ordem não é óbvia

## Alternativas consideradas

- Alembic para migrations: rejeitado por regra rígida do projeto (migrations manuais)
- JSON type nativo do SQLAlchemy: rejeitado por compatibilidade com MySQL 5.7 (FiltroSalvo.criterios usa Text explicitamente)
