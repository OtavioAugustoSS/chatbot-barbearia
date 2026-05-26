---
name: ADR-011-rbac-absence-admin-endpoints
description: Política de RBAC ausente nos endpoints admin — riscos documentados e aceitos
metadata:
  type: decision
  status: ACCEPTED
---

# ADR-011 — Ausência de RBAC nos Endpoints Admin: Riscos e Política de Aceitação

Status: aceito
Data: 2026-05-22
Decisor: architect-agent
Stakeholders consultados: backend-agent, product-owner-agent (referência a BR-005)

## Contexto

O dashboard admin (`api/admin.py`) autentica via JWT, mas todos os atendentes autenticados têm
exatamente as mesmas permissões. Não existe distinção de roles (supervisor vs. agent). A revisão
identificou **três categorias de endpoints sem restrição de role** que merecem atenção:

### Categoria A — Gestão de atendentes (alto risco)

```
POST   /admin/atendentes          — cria novo atendente
PATCH  /admin/atendentes/{id}/desativar  — desativa atendente
PATCH  /admin/atendentes/{id}/ativar     — ativa atendente
```

Qualquer atendente autenticado pode criar novos atendentes (potencialmente maliciosos) ou
desativar colegas. A única proteção é `if atual.id == atendente_id: raise 400` (não pode
auto-desativar). Um atendente desonesto pode criar um segundo login para si mesmo ou
desativar todos os outros.

### Categoria B — Labels globais (médio risco)

```
POST   /admin/labels              — cria label (disponível a todos)
PATCH  /admin/labels/{id}         — edita label de outro atendente
DELETE /admin/labels/{id}         — soft-delete de label compartilhada
```

Qualquer atendente pode modificar ou deletar labels criadas por qualquer outro atendente.
Labels são dados compartilhados — um atendente pode remover labels que outros usam.

### Categoria C — Canned responses globais (médio risco)

```
POST   /admin/canned (escopo='global')  — cria canned response global
PATCH  /admin/canned/{id}               — edita canned global de qualquer atendente
DELETE /admin/canned/{id}               — deleta canned global de qualquer atendente
```

O código valida ownership para canned pessoais: `if c.atendente_id is not None and c.atendente_id != me.id: raise 403`.
Mas canned globais (`atendente_id IS NULL`) são editáveis/deletáveis por qualquer atendente.

### Categoria D — Transferência de conversa sem verificação de destino ativo

`POST /admin/conversa/{telefone}/atribuir` verifica que o destino está ativo (`Atendente.ativo == True`).
Sem RBAC, um atendente pode transferir para si mesmo se for o dono atual — protegido por
`if destino.id == me.id: raise 400`. Comportamento correto.

### Categoria E — Bulk sem restrição de scope

`POST /admin/conversas/bulk` com `acao='atribuir'` pode reatribuir qualquer conversa para
qualquer atendente, mesmo que o executor não seja o dono atual. O comentário no código
documenta: "Aqui é admin-level: pode reatribuir mesmo sem ser dono." Intencionalmente irrestrito.

## Decisão

### Aceitar o risco atual e documentar formalmente

O CHATWOOT-VIABILITY.md já identifica RBAC como item de 8–12h de esforço (Sprint 0.3.0+).
Esta ADR documenta que a **ausência de RBAC é um débito aceito temporariamente** com as
seguintes mitigações compensatórias:

1. **Categoria A**: acesso ao dashboard é controlado por credenciais criadas manualmente via
   `scripts/criar_atendente.py` — apenas quem tem acesso ao servidor pode criar o primeiro
   atendente. O risco é de atendentes internos agindo de má-fé, não de atacantes externos.

2. **Categoria B e C**: labels e canned globais são dados de suporte, não dados de negócio
   crítico. Corrupção acidental é recuperável (soft-delete de label pode ser reativado via
   `PATCH /admin/labels/{id}` com `ativo: true`).

3. **Categoria E**: bulk sem restrição de scope é intencional para permitir reatribuição
   de emergência (ex: atendente sai abruptamente).

### Quando implementar RBAC

Implementar roles (`supervisor` / `agent`) quando **qualquer** das seguintes condições:
- Mais de 3 atendentes simultâneos (risco de conflito aumenta)
- Instância multi-tenant (outro cliente usando o mesmo deploy)
- Incidente de atendente modificando dado de outro (primeiro incidente real)

O CHATWOOT-VIABILITY.md tem o design de RBAC pronto para implementação.

### Endpoint de criação de atendente: exige proteção imediata

**Exceção à política de aceitação**: `POST /admin/atendentes` e os endpoints de ativar/desativar
devem ser restritos a `supervisor` quando RBAC for implementado. Até lá, documentar no
CLAUDE.md que esses endpoints existem e não têm proteção extra.

### Addendum ao ADR-002

Este documento funciona como addendum ao padrão de erros (ADR-002): os 403 de ownership
em notas e canned pessoais estão corretos. A ausência de 403 em labels globais e gestão
de atendentes é decisão explícita, não omissão.

## Consequências

- Positivo: documenta o risco de forma rastreável — próximo sprint pode priorizar RBAC com
  contexto claro
- Positivo: clarifica que o comportamento de bulk sem restrição é intencional (Categoria E)
- Negativo: atendente com acesso ao dashboard pode criar contas adicionais ou desativar colegas
- Risco médio: em barbearia com 2–3 atendentes de confiança, risco real é baixo

## Alternativas consideradas

- **Implementar RBAC agora (hardcode supervisor = primeiro atendente criado)**: rejeitado —
  heurística frágil, não escalável; melhor implementar com coluna `role` quando houver
  necessidade real
- **Remover endpoints de gestão de atendentes do dashboard**: rejeitado — settings.html já
  usa esses endpoints para CA-07 (ativar/desativar atendente)
- **Exigir JWT com claim `role=supervisor` sem banco**: possível como MVP rápido (atribuir
  role no momento de criar_token), mas requer migration e mudança no script criar_atendente.py
