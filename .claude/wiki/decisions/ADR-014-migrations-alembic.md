# ADR-014: Gestão de Migrations com Alembic — Resolução do Schema Drift (P1-3)

Status: aceito
Data: 2026-06-08
Decisor: architect-agent
Stakeholders consultados: lead-agent (missão P1-3), backend-agent (consumidor), qa-agent (restrição de testes)

---

## Contexto

`db/models.py` define 13 models (+ 2 tabelas associativas) que representam o estado real do schema em produção/dev. O arquivo `barbearia_bot_db.sql` na raiz cobre apenas ~5 tabelas iniciais — está dessincronizado e não pode ser usado para restaurar o banco.

O sistema de migrations manual existente é composto de:
- `scripts/migrations/TASK001..TASK017` (7 arquivos referenciados no runner)
- `scripts/migrations/0001`–`0011` (11 arquivos não referenciados pelo runner)
- `scripts/migrations/TASK_FOTO_URL.sql` e `US-TICKS-01-lida-wamid.sql` (extras, também não no runner)
- `scripts/aplicar_migrations.py` com lista hardcoded de apenas 7 migrations e idempotência por string-match de erro — o próprio runner está drifted

O boot (`main.py:65`) executa `Base.metadata.create_all(bind=engine)`, que cria tabelas ausentes mas nunca altera colunas ou índices existentes.

A suíte de testes (`tests/conftest.py`) substitui `db.database.engine` por SQLite StaticPool antes de qualquer import e cria o schema via `Base.metadata.create_all(bind=engine_teste)`. Os 84 testes verdes não tocam Alembic e não devem ser alterados.

O banco de dev já existe com dados — a introdução de Alembic não pode exigir recriar o banco.

---

## Decisão

**Adotar Alembic com `autogenerate` a partir de `Base.metadata` como fonte única de verdade do schema.**

`db/models.py` continua sendo a fonte de verdade; Alembic apenas captura o diff entre os models e o DB real e o transforma em scripts SQL versionados e rastreáveis.

As decisões específicas são:

### D1 — Alembic com autogenerate (não consolidar .sql manual)

Adotar Alembic com `target_metadata = Base.metadata` e `autogenerate`. A alternativa de consolidar um único `.sql` canônico resolve o problema de restauração mas não resolve o tracking de versão: a próxima mudança de schema recriaria o drift. Alembic resolve ambos.

### D2 — Naming convention de constraints

Adicionar `naming_convention` ao `MetaData` em `db/database.py` antes de criar a revisão inicial. Sem isso, MySQL gera nomes de constraint implícitos que o autogenerate não consegue resolver deterministicamente, produzindo diffs ruidosos e falsos.

O dict canônico a usar:

```python
from sqlalchemy import MetaData

NAMING_CONVENTION = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}

Base = declarative_base(metadata=MetaData(naming_convention=NAMING_CONVENTION))
```

**Alerta importante:** a primeira execução de `alembic revision --autogenerate` vai querer renomear constraints que já existem no DB (criadas sem a convention). Para o banco de dev existente, a revisão inicial deve ser criada como **baseline vazia** (corpo `pass`) e carimbada com `alembic stamp head` — detalhado em D3. Isso evita que o Alembic tente renomear constraints já aplicadas. Novas migrations geradas depois da baseline usarão os nomes padronizados.

### D3 — Baseline para DB existente e DB do zero

**DB de dev existente (já tem todas as tabelas):**
1. Gerar a revisão inicial com `alembic revision -m "baseline"`.
2. Esvaziar o corpo de `upgrade()` e `downgrade()` (deixar apenas `pass`) — o estado atual já está aplicado.
3. Executar `alembic stamp head` no banco — isso registra a revisão na tabela `alembic_version` sem rodar SQL.
4. A partir daí, toda mudança de model vira `alembic revision --autogenerate`.

**DB do zero (novo ambiente ou restauração):**
Com baseline vazia (corpo `pass`), `alembic upgrade head` em banco limpo cria apenas a tabela `alembic_version` — nenhuma tabela da aplicação. Isso é consequência direta e intencional da baseline vazia: o Alembic registra o ponto de partida, não reconstrói o histórico anterior.

O bootstrap de um DB do zero é portanto **sempre** via `create_all`:
1. `Base.metadata.create_all(engine)` — cria todas as tabelas a partir dos models.
2. `alembic stamp head` — registra a revision baseline no banco recém-criado.

A partir desse ponto o banco recebe migrations normalmente via `alembic upgrade head`. `alembic upgrade head` sozinho só aplica **deltas pós-baseline** — nunca o schema base.

Essa é a única estratégia compatível com a baseline vazia. Não existe "Opção A via upgrade head puro" com esta configuração.

### D4 — Coexistência de `create_all` no boot

`Base.metadata.create_all(bind=engine)` em `main.py:65` é **mantido permanentemente, sem condição**.

Funções de cada mecanismo:

| Mecanismo | Papel | Contexto |
|---|---|---|
| `create_all` no boot | Cria tabelas ausentes a partir dos models (bootstrap + testes) | SQLite (testes) e MySQL novo |
| `alembic upgrade head` | Aplica deltas pós-baseline (novas colunas, índices, etc.) | MySQL em deploy |
| `alembic stamp head` | Registra revision sem rodar SQL (bootstrap de DB novo) | MySQL novo após `create_all` |

Em **testes**: `conftest.py` substitui o engine por SQLite antes do import de `main.py`; `create_all` cria o schema SQLite normalmente. Sem alteração em `conftest.py`.

Em **produção/staging MySQL com DB já existente**: `create_all` é inócuo (tabelas já existem, a chamada é no-op por tabela). `alembic upgrade head` aplica qualquer delta pendente. Ambos rodam no boot/deploy sem conflito.

Em **MySQL do zero**: `create_all` cria todas as tabelas; `alembic stamp head` registra a baseline (passo manual de setup, não automático no boot). Após isso, `alembic upgrade head` aplica deltas futuros normalmente.

`create_all` **não será removido do boot** — ele é a única fonte de bootstrap para DB do zero e para a suíte de testes. O runbook de deploy documenta `alembic upgrade head` como passo adicional, não substituto.

### D5 — Destino do legado

- `barbearia_bot_db.sql`: mover para `scripts/archive/barbearia_bot_db_legacy.sql` com comentário de que está desatualizado. Não deletar imediatamente — histórico útil.
- `scripts/migrations/TASK*` e `scripts/migrations/0001..0011` e demais `.sql`: mover para `scripts/archive/migrations_legacy/`. Todos os estados que eles representam já estão aplicados no banco de dev e serão capturados pela baseline.
- `scripts/aplicar_migrations.py`: remover (ou mover para `scripts/archive/`). Substituído inteiramente por `alembic upgrade head`.
- As migrations legadas **não devem ser re-aplicadas** — o `alembic stamp head` indica que o ponto de partida já engloba todo esse histórico.

### D6 — Localização dos arquivos Alembic

```
alembic.ini          ← raiz do projeto (junto de main.py)
alembic/
  env.py             ← configurado para ler URL do banco via db.database
  script.py.mako     ← template padrão
  versions/          ← revisions geradas
```

`alembic/env.py` importa `SQLALCHEMY_DATABASE_URL` de `db.database` e `Base.metadata` de `db.models` — sem duplicar credenciais. O `alembic.ini` define `sqlalchemy.url = ` vazio (ou placeholder); o `env.py` sobreescreve via `config.set_main_option()`.

---

## Consequências

**Positivas:**
- Schema drift resolvido: qualquer mudança em `db/models.py` gera uma migration rastreável e auditável.
- `barbearia_bot_db.sql` deixa de ser fonte de confusão — descontinuado formalmente.
- `scripts/aplicar_migrations.py` e sua lista hardcoded são eliminados.
- Novo ambiente provisionado com sequência clara: `create_all` + `stamp head` + `upgrade head` para futuros deltas.
- Deploy documentado: `alembic upgrade head` no runbook antes de `uvicorn` (aplica deltas pós-baseline).

**Negativas / riscos aceitos:**
- `create_all` e `alembic upgrade head` são dois mecanismos para o mesmo fim — mantidos separados por domínio (testes vs. prod). Risco: divergência silenciosa (ver seção Riscos).
- MySQL + autogenerate tem limitações: tipos como `ENUM`, `JSON`, charset `utf8mb4` por coluna, e precisão de `Numeric` às vezes produzem diffs falsos. Cada `autogenerate` deve ser revisado antes de aplicar.
- Constraints sem nome no banco existente: a baseline vazia contorna o problema para o estado atual, mas novas migrations geradas logo depois podem ainda querer renomear constraints implícitas remanescentes. Revisar o primeiro `autogenerate` pós-baseline com atenção.
- Curva de aprendizado: `alembic upgrade head` precisa ser conhecida por quem faz deploy.

**Mudança de política (CLAUDE.md):**
A política "Migrations manuais, SQL em `scripts/migrations/{TASK}-{descricao}.sql` ANTES de alterar `db/models.py`" é **substituída** pela política Alembic definida neste ADR (ver Passo 11 da implementação).

---

## Riscos específicos

**R1 — Divergência testes (create_all) vs. prod (alembic upgrade head).**
Este é o risco estrutural mais importante: os testes continuam criando o schema via `create_all(Base.metadata)`, enquanto produção usa `alembic upgrade head`. Se uma migration for escrita de forma que difira do model (ex.: tipo ligeiramente diferente), os testes não capturarão isso.

Mitigação pragmática: não vale a pena um teste de comparação `create_all` vs. `upgrade head` agora (overkill para este volume). A mitigação é disciplinar: toda migration deve ser gerada via `autogenerate` a partir dos models (não escrita à mão), garantindo que o SQL seja derivado do mesmo `Base.metadata` que os testes usam. Desvios detectáveis na revisão manual do script antes de aplicar.

**R2 — MySQL autogenerate e tipos problemáticos.**
SQLAlchemy/Alembic não detecta mudanças de charset por coluna, pode gerar diffs em `BOOLEAN` (mapeado como `TINYINT(1)`) e em `Numeric` com precisão. Adicionar `compare_type=True` no `env.py` para capturar mudanças de tipo, mas revisar cada diff antes de aplicar — especialmente na primeira geração pós-baseline.

**R3 — Primeira geração pós-baseline renomeia constraints.**
Se `naming_convention` for adicionado e o DB ainda tiver constraints com nomes implícitos, o primeiro `autogenerate` pode gerar `op.drop_constraint` / `op.create_constraint` para renomear. Isso é inócuo em semântica mas gera lock de tabela no MySQL. Avaliar e remover esses ops do script se o risco não compensar.

**R4 — `alembic stamp head` sem `create_all` prévio em banco novo.**
Com baseline vazia, `alembic stamp head` em banco limpo (sem tabelas) registra a revision como aplicada, mas o schema da aplicação não existe. O bootstrap correto de DB do zero é: `create_all` primeiro, depois `stamp head`. Nunca `stamp head` sozinho em banco sem tabelas. `alembic upgrade head` isolado também não cria o schema base (cria apenas `alembic_version`) — não usar como bootstrap.

---

## Alternativas consideradas

**Alternativa A — Consolidar um `.sql` canônico único.**
Criar um `schema_canonical.sql` com o dump atual completo, substituindo `barbearia_bot_db.sql`. Resolve a restauração mas não resolve tracking de versão. A próxima migration manual recriaria o drift. Rejeitado: resolve metade do problema.

**Alternativa B — Manter migrations manuais com runner melhorado.**
Corrigir `scripts/aplicar_migrations.py` para descoberta automática de arquivos (glob) e usar tabela de tracking própria. Resolve o tracking mas duplica o que Alembic já faz, e mantém o risco de SQL manual divergente dos models. Rejeitado: reinventa a roda com pior resultado.

**Alternativa C — Sqitch ou Flyway.**
Ferramentas de migration baseadas em SQL puro. Mais próximas do modelo manual atual. Não integram com `Base.metadata` — o autogenerate de diff não existe. Rejeitado: perde o principal benefício (derivar migrations dos models).

---

## Passos de implementação (para o lead)

Os passos abaixo devem ser executados em sequência. Nenhum altera comportamento em produção até o Passo 9.

**1. Instalar Alembic**
```
pip install alembic
```
Adicionar `alembic` ao `requirements.txt`.

**2. Adicionar `naming_convention` em `db/database.py`**
Substituir:
```python
Base = declarative_base()
```
Por:
```python
from sqlalchemy import MetaData

_NAMING_CONVENTION = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}
Base = declarative_base(metadata=MetaData(naming_convention=_NAMING_CONVENTION))
```
Rodar `pytest` após esta mudança — deve permanecer 84 PASS (naming_convention não afeta create_all).

**3. Inicializar Alembic**
Na raiz do projeto:
```
alembic init alembic
```
Isso cria `alembic.ini` e `alembic/` com `env.py`, `script.py.mako`, `versions/`.

**4. Configurar `alembic.ini`**
Deixar `sqlalchemy.url` vazio (será sobrescrito pelo `env.py`):
```ini
sqlalchemy.url =
```

**5. Configurar `alembic/env.py`**
Substituir o bloco de configuração de URL e metadata pelo seguinte (modo online e offline):

```python
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from db.database import SQLALCHEMY_DATABASE_URL, Base
from db import models  # garante que todos os models são importados

# vincula metadata ao autogenerate
target_metadata = Base.metadata

# --- configuração de URL ---
config.set_main_option("sqlalchemy.url", SQLALCHEMY_DATABASE_URL)

# offline mode
def run_migrations_offline() -> None:
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
    )
    with context.begin_transaction():
        context.run_migrations()

# online mode
def run_migrations_online() -> None:
    from sqlalchemy import engine_from_config, pool
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,
        )
        with context.begin_transaction():
            context.run_migrations()
```

O `import db.models` garante que todas as tabelas estejam registradas em `Base.metadata` no momento do autogenerate.

**6. Gerar a revisão baseline (corpo vazio)**
```
alembic revision -m "baseline_estado_atual"
```
Abrir o arquivo gerado em `alembic/versions/` e esvaziar `upgrade()` e `downgrade()`:
```python
def upgrade() -> None:
    pass

def downgrade() -> None:
    pass
```
Commitar este arquivo.

**7. Carimbar o banco de dev existente**
Com o banco de dev rodando (todas as tabelas já presentes):
```
alembic stamp head
```
Verificar: `SELECT * FROM alembic_version;` deve retornar a revision ID do baseline.

**8. Arquivar o legado**
```
mkdir scripts/archive
mkdir scripts/archive/migrations_legacy
# mover barbearia_bot_db.sql
# mover scripts/migrations/ para scripts/archive/migrations_legacy/
# remover (ou mover) scripts/aplicar_migrations.py
```
Adicionar cabeçalho em `scripts/archive/barbearia_bot_db_legacy.sql`:
```sql
-- LEGADO: schema inicial (~5 tabelas). Desatualizado desde Sprint 0.1.
-- Fonte de verdade atual: db/models.py + alembic/versions/
-- Mantido apenas como referência histórica.
```

**9. Workflow de mudanças de schema a partir daqui**
Para qualquer alteração futura em `db/models.py`:
```
# 1. Alterar db/models.py
# 2. Gerar migration:
alembic revision --autogenerate -m "descricao_da_mudanca"
# 3. REVISAR o script gerado em alembic/versions/ antes de aplicar
# 4. Aplicar no banco de dev:
alembic upgrade head
# 5. Commitar models.py + o arquivo de versão
```
Não mais criar arquivos `.sql` em `scripts/migrations/`.

**10. Atualizar o comentário de `create_all` em `main.py`**
`create_all` permanece no boot sem condição (ver D4). Apenas atualizar o comentário para refletir a decisão:

```python
# Base.metadata.create_all: cria tabelas ausentes a partir dos models.
# Papéis: (1) testes — conftest.py substitui engine por SQLite; create_all cria schema SQLite.
#         (2) MySQL do zero — cria o schema base; rodar `alembic stamp head` manualmente
#             após o primeiro boot para registrar a baseline. Depois disso, deltas via
#             `alembic upgrade head` no deploy.
#         (3) MySQL com tabelas existentes — no-op por tabela; inócuo.
# NÃO remover: é a fonte de bootstrap para DB do zero e para a suíte de testes. Ver ADR-014.
Base.metadata.create_all(bind=engine)
```

**11. Atualizar `CLAUDE.md` — nova política de migrations**
Substituir o parágrafo:
> "Migrations sempre manuais (sem Alembic) — `scripts/migrations/{TASK}-{descricao}.sql`"

Por:
> "Migrations via Alembic (ADR-014). Fluxo: alterar `db/models.py` → `alembic revision --autogenerate -m '<descricao>'` → revisar o script gerado → `alembic upgrade head`. Arquivos em `alembic/versions/`. Scripts `.sql` manuais legados estão em `scripts/archive/migrations_legacy/` — não usar."

Idem na seção "Regras rígidas" do sistema multi-agente em `CLAUDE.md`.

**12. Atualizar o runbook de deploy**
Duas situações distintas no runbook:

**Deploy normal (banco já existente com baseline carimbada):**
```
# Antes de subir a aplicação — aplica deltas pós-baseline:
alembic upgrade head
# (idempotente: no-op se já estiver no head)
uvicorn main:app ...
```

**Bootstrap de ambiente do zero (primeiro deploy ou restauração):**
```
# 1. Subir a aplicação uma vez para que create_all crie as tabelas:
uvicorn main:app ...   # (ou python main.py)
# 2. Parar a aplicação. Registrar a baseline no banco recém-criado:
alembic stamp head
# 3. Verificar: SELECT * FROM alembic_version; deve retornar a revision ID.
# 4. Subir normalmente — a partir daqui, deploy usa `alembic upgrade head` antes do uvicorn.
```

Documentar que `alembic upgrade head` sozinho em banco do zero cria apenas `alembic_version`, não o schema da aplicação.

**13. Atualizar `index.md`**
Registrar este ADR no catálogo.
