---
name: ADR-009-bulk-action-atomicity
description: Estratégia de atomicidade e SSE para operações bulk em admin.py
metadata:
  type: decision
  status: ACCEPTED
---

# ADR-009 — Atomicidade Parcial em Bulk Actions e Ordem de SSE

Status: aceito
Data: 2026-05-22
Decisor: architect-agent
Stakeholders consultados: backend-agent (código como fonte de verdade)

## Contexto

O endpoint `POST /admin/conversas/bulk` em `api/admin.py` (linhas 768–866) executa ações em lote
sobre múltiplos telefones. A implementação atual tem dois problemas arquiteturais relacionados:

### Problema 1 — Commit único após loop vs. commit por item

O loop percorre cada telefone, muta o objeto `user`, e ao final chama `db.commit()` uma única vez
(linha 857). Isso é correto para garantir que **ou tudo ou nada** persiste no banco — se uma exceção
ocorrer no meio do loop, o `except Exception` por telefone captura e adiciona à lista de falha, mas
as mutações dos itens anteriores (já em memória do SQLAlchemy) ainda serão comitadas no commit final.

Resultado: o `db.commit()` pós-loop confirma TODAS as mutações que não geraram exceção, incluindo
as anteriores ao telefone que falhou. Isso é **parcialmente atômico por design** — mas não é documentado.

Para operações `label_add` e `label_remove`, o código usa `db.execute()` diretamente na tabela de
associação. Essas execuções emitem SQL imediatamente; se o loop continuar e o commit final ocorrer,
elas são confirmadas. Se ocorrer rollback, são desfeitas. Comportamento correto, mas frágil:
mistura `db.execute()` e mutações de ORM na mesma transação.

### Problema 2 — SSE `bulk_aplicado` publicado antes de conhecer falhas parciais

O evento SSE `bulk_aplicado` (linhas 859–864) é publicado logo após `db.commit()`, mas o payload
inclui apenas `afetadas: len(resultados["sucesso"])` sem mencionar falhas. O frontend ao receber
o evento faz reload da lista (`carregarConversas()`), então a inconsistência é cosmética — mas o
contrato SSE formalizado em ADR-005 não documenta que `bulk_aplicado` pode ter falhas parciais.

### Problema 3 — `BulkIn.telefones` valida min=1 mas não garante unicidade

Se o mesmo telefone aparecer duas vezes no payload, o loop o processa duas vezes. Para `label_add`
isso é idempotente (guard SELECT + INSERT). Para `resolver` ou `atribuir`, o segundo loop lê o
mesmo objeto `user` da sessão (ORM identity cache) e reaplicar `status_conversa = "resolved"`
duas vezes é inócuo. Problema teórico, não prático, mas vale documentar.

## Decisão

### 1. Atomicidade parcial é aceita e documentada

`bulk_acao` opera com **atomicidade parcial intencional**: itens bem-sucedidos são comitados
mesmo se outros falham. Isso é preferível ao rollback total porque:

- O caso de uso é "aplicar em lote" — o operador quer que 99 de 100 resolvam mesmo se 1 falha
- O feedback de falhas é retornado no payload da response (`falha: [...]`)
- O dashboard recarrega estado via SSE após o evento `bulk_aplicado`

Este comportamento deve ser documentado no docstring do endpoint e no ADR-005.

### 2. SSE `bulk_aplicado` recebe addendum no ADR-005

O campo `afetadas` em `bulk_aplicado` representa itens bem-sucedidos apenas. Falhas parciais
são comunicadas **exclusivamente via response body** (não via SSE). O frontend não precisa
tratar falhas via SSE — o reload de estado após o evento é suficiente.

### 3. Unicidade de telefones no payload: não validar no servidor

Duplicatas de telefone no payload são idempotentes na prática (ORM cache + guards). Adicionar
validação de unicidade no `BulkIn` (via `field_validator`) é uma melhoria baixa prioridade
que pode ser feita sem novo ADR.

### 4. Mistura de `db.execute()` e ORM na mesma transação: aceita

A mistura atual (ORM para `Usuario`, raw execute para `usuario_labels`) está contida dentro
de uma única transação por request. O `db.commit()` confirma ambos. Padrão aceito enquanto
não houver casos de operações mais complexas que exijam savepoints.

## Consequências

- Positivo: documenta o comportamento atual como intencional, evitando mudanças desnecessárias
- Positivo: addendum ao ADR-005 fecha lacuna no contrato SSE
- Negativo: falhas parciais em bulk não geram alerta visual proativo no dashboard (só via toast
  pós-request, que o frontend já exibe via response body)
- Risco: se o número de telefones no bulk crescer muito (payload max=200), a transação pode
  demorar e aumentar lock contention no MySQL. Aceitável no volume atual.

## Alternativas consideradas

- **Rollback total em qualquer falha**: rejeitado — comportamento unintuitive para o operador
  que espera que itens válidos sejam processados
- **Savepoints por item**: suportado pelo MySQL mas não pelo SQLAlchemy ORM de forma direta;
  complexidade injustificada para o volume atual
- **Fila de jobs assíncrona (Celery/etc)**: rejeitado — introduz dependência externa não
  justificada para bulk de até 200 itens em barbearia local
