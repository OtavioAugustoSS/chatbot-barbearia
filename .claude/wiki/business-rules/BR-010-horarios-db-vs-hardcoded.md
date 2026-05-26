---
name: BR-010-horarios-db-vs-hardcoded
description: Horarios de funcionamento sao gerenciados na tabela `horarios` do banco de dados. O dict hardcoded em ai_service.py e fallback de emergencia apenas.
metadata:
  type: business-rule
---

# BR-010 — Gestao de Horarios de Funcionamento

Data: 2026-05-22
Stakeholders: product-owner-agent (auditoria autonoma — modelo Horario sem BR formal; fonte da verdade ambigua entre banco e hardcoded)

## Contexto

O sistema tem dois lugares onde os horarios de funcionamento da Barbearia Bolshoi estao definidos:

1. **Tabela `horarios`** no banco de dados (modelo `Horario` em `db/models.py`) — fonte primaria
2. **Dict `_HORARIOS`** em `services/ai_service.py` — fallback hardcoded

Alem disso, os horarios aparecem literalmente em `core/prompts.py` (SYSTEM_PROMPT_BARBEARIA, secao "DADOS DA BARBEARIA") e em `core/respostas_canonicas.py` (`_CORPO_HORARIO`). Isso cria risco de dessincronizacao: se os horarios mudarem no banco, o prompt e as canonicas continuam com os valores antigos.

## Regra

### Fonte da verdade

A tabela `horarios` no banco de dados e a fonte de verdade para os horarios de funcionamento injetados no contexto temporal da IA (via `_construir_contexto_temporal()`).

### Hierarquia de fontes

1. **Tabela `horarios`** (primaria): usada se a tabela tiver pelo menos um registro
2. **`_HORARIOS` hardcoded** (fallback): usado APENAS se a tabela estiver vazia ou inacessivel por erro de banco

### Horarios atuais (valores corretos a 2026-05-22)

| Dia | Abertura | Fechamento |
|---|---|---|
| Segunda | 14:00 | 21:00 |
| Terca | 09:00 | 21:00 |
| Quarta | 09:00 | 21:00 |
| Quinta | 09:00 | 21:00 |
| Sexta | 09:00 | 21:00 |
| Sabado | 09:00 | 18:00 |
| Domingo | FECHADO | — |

### Sincronizacao obrigatoria

Quando os horarios de funcionamento da barbearia mudam:
1. Atualizar a tabela `horarios` no banco (script SQL ou via admin)
2. Atualizar `core/prompts.py` — secao "DADOS DA BARBEARIA" (string de horario no system prompt)
3. Atualizar `core/respostas_canonicas.py` — constante `_CORPO_HORARIO`
4. Atualizar `services/ai_service.py` — dict `_HORARIOS` (fallback)

Falhar em sincronizar (1) e (2)/(3) cria inconsistencia: a IA recebe contexto temporal correto mas o prompt diz valores errados.

### Cache do banco de horarios

- TTL: 5 minutos (igual ao cache de servicos/barbeiros)
- Estrutura: `_cache_horarios` em `ai_service.py` (cache de modulo, nao por instancia)
- Se o banco falhar, o cache retorna o ultimo valor valido conhecido (nao falha silenciosamente)

### Horarios em fechamento especial (feriado, recesso)

Decisao de produto: o modelo `Horario` tem campo `fechado` (Boolean). Para marcar um feriado:
- Setar `fechado=True` no registro do dia correspondente
- O contexto temporal injetara "FECHADA hoje (dia_semana)" para esse dia
- **LIMITACAO**: a tabela `horarios` nao suporta excepcoes pontuais por data — apenas por dia da semana. Para feriados, e necessario intervenção manual no banco e revertida depois.

## Gatilhos

Este mecanismo e ativado a cada chamada de `_construir_contexto_temporal()` dentro de `processar_intencao()`.

## Comportamento esperado

- Banco acessivel + tabela populada: contexto temporal usa dados do banco com cache de 5 min
- Banco acessivel + tabela vazia: fallback para `_HORARIOS` hardcoded (warning em log)
- Banco inacessivel: fallback para cache anterior se existir; senao usa `_HORARIOS` hardcoded

## Excecoes

- Horario especial (ex.: sabado de Carnaval, fechamento antecipado): necessita atualizacao manual na tabela — nao ha interface de admin para isso atualmente

## Implementacao em codigo

- `db/models.py`: classe `Horario` (campos: `dia_semana` PK int, `abertura` str HH:MM nullable, `fechamento` str HH:MM nullable, `fechado` bool)
- `services/ai_service.py`: `_carregar_horarios_db()`, `_construir_contexto_temporal()`, `_formatar_horario_dia()`
- `core/prompts.py`: secao "DADOS DA BARBEARIA" (texto literal — deve estar sincronizado com o banco)
- `core/respostas_canonicas.py`: `_CORPO_HORARIO` (texto literal — deve estar sincronizado com o banco)

## Debito tecnico associado

- **TD-001** (datetime naive + TZ): timestamps no banco sao naive sem configuracao de TZ=UTC. O campo `abertura` e `fechamento` sao strings HH:MM (nao afetados pelo TD-001), mas o campo `fechado` pode ter inconsistencia se o banco for consultado em horario de transicao
- **GAP pendente**: nao ha interface de admin para editar horarios — apenas via SQL direto. Criar endpoint CRUD para `horarios` e recomendado para Sprint 0.3.0+

## Notas de produto

- A tabela `horarios` requer seed inicial via `scripts/seed_horarios.py` (referenciado no CLAUDE.md). Sem o seed, o sistema usa o fallback hardcoded — que hoje esta sincronizado com os horarios reais
- Qualquer mudança de horario da barbearia DEVE ser tratada como mudança em 4 arquivos (banco + 3 fontes de codigo) — alertar o time tecnico sobre esse acoplamento
- Prioridade para Sprint 0.3.0+: criar endpoint admin para edicao de horarios sem intervencao tecnica
