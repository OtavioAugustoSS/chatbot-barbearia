# US-GAP-01: Reativar Atendente Desativado

**ID:** US-GAP-01
**Area:** Gestao de Atendentes
**Origem:** GAP-01 identificado em BR-AUDIT-001 (2026-05-21)
**Data de formalizacao:** 2026-05-21
**Implementado em:** FASE 3, SP-2 (backend-agent, 2026-05-21)

---

## User Story

**Como** administrador da barbearia
**Quero** reativar um atendente que foi desativado anteriormente
**Para** que ele possa voltar a receber e atender conversas no dashboard sem precisar criar uma nova conta

---

## Contexto

Antes da FASE 3, existia apenas o endpoint `PATCH /admin/atendentes/{id}/desativar`. Uma vez desativado, o atendente nao podia ser reativado pela UI — o administrador precisaria intervir diretamente no banco de dados. O GAP foi identificado na auditoria BR-AUDIT-001 como bloqueante para a gestao do ciclo de vida de atendentes.

A implementacao entregou dois endpoints complementares:
- `PATCH /admin/atendentes/{id}/ativar` — nao-idempotente; retorna 400 se ja ativo
- `POST /admin/atendentes/{id}/reativar` — idempotente (SP-2/GAP-01); retorna `ja_ativo: true` se ja estava ativo; publica SSE ao reativar

---

## Criterios de Aceite

- [x] CA-01: `POST /admin/atendentes/{id}/reativar` existe e requer autenticacao JWT valida
- [x] CA-02: Se atendente com `id` nao existe → HTTP 404 "Atendente nao encontrado"
- [x] CA-03: Se atendente ja esta ativo → HTTP 200 `{"ok": true, "ja_ativo": true}` (idempotente, sem erro)
- [x] CA-04: Se atendente esta inativo → seta `ativo=True`, retorna HTTP 200 `{"ok": true, "id": ..., "nome": ...}`
- [x] CA-05: Apos reativacao bem-sucedida, publica evento SSE `presence_changed` com `{atendente_id, atendente_nome, status: "reativado"}`
- [x] CA-06: Dashboard de outros atendentes recebe SSE e pode atualizar lista de atendentes em tempo real
- [ ] CA-07: UI expoe botao "Reativar" na lista de atendentes inativos (frontend pendente — nao entregue na FASE 3)

---

## Estado atual

**Backend:** IMPLEMENTADO (`api/admin.py`, endpoint `POST /admin/atendentes/{atendente_id}/reativar`)
**Frontend:** PENDENTE — botao "Reativar" nao exposto na UI de gestao de atendentes

---

## Arquivos relevantes

- `api/admin.py`: linha ~1592 — funcao `reativar_atendente()`
- `api/admin.py`: linha ~1570 — funcao `ativar_atendente()` (endpoint nao-idempotente alternativo)
- `static/admin/js/app.js`: gestao de atendentes (frontend a ser atualizado para expor botao)

---

## Notas de produto

- O endpoint idempotente (`/reativar`) e preferido para chamadas do frontend, pois evita erros de UX quando o admin clica duas vezes ou quando ha dessincronizacao de estado.
- O endpoint nao-idempotente (`/ativar`) foi mantido para simetria com `/desativar` mas nao deve ser usado pela UI.
- CA-07 (botao na UI) fica como pendencia para proximo sprint. O backend esta pronto e testavel via API direta.
- Relacionado a US-090 CA-04 (conversas abertas liberadas ao desativar): ao reativar, o atendente pode reassumir conversas. Nenhum handoff automatico ocorre — ele precisa assumir manualmente.
