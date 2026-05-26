# SPRINT-FIXES — Fase 3 Backend

Data: 2026-05-21
Executado por: backend-agent

---

## QW-B1: JSON Regex Fallback (CRÍTICO — bug em produção)

**Problema:** `json.loads()` falhava sem recuperação ao receber JSON pretty-printed
sem `{` de abertura (erro confirmado em `erro_ia_debug.txt`: `'\n  "intencao"'`).
Todo parse failure disparava `transbordo_falha`, desativando o bot desnecessariamente.

**Solução:** Adicionada cadeia de fallback em `processar_intencao()` após o strip de
markdown fences:
1. Tenta `json.loads()` direto (caminho feliz — sem overhead).
2. Se falhar: `re.search(r'\{[^{}]*"intencao"[^{}]*"resposta_sugerida"[^{}]*\}', ..., re.DOTALL)` — extrai objeto JSON específico das chaves esperadas.
3. Se falhar: `re.search(r'\{.*\}', ..., re.DOTALL)` — extrai qualquer JSON e valida campos.
4. Se falhar: re-lança `json.JSONDecodeError` para o `except` externo.

**Arquivo:** `services/ai_service.py` linhas 340-379
**Risco:** Zero — fallbacks só ativam se parse direto falhar.

---

## QW-B2: Strip `| ref:` em `_validar_resposta()`

**Problema:** O formato injetado no prompt (`✂️ Nome — R$ X  | ref: dura Ymin; desc: Z`)
pode vazar para a resposta ao cliente se o modelo sofrer drift em conversas longas.
A proteção era apenas instrucional (no prompt), sem barreira técnica no output.

**Solução:** Adicionado `re.sub(r'\s*\|\s*ref:[^\n<]*', '', resposta)` ao final de
`_validar_resposta()`, após a verificação de agendamento proibido.

**Arquivo:** `services/ai_service.py` linhas 264-268
**Risco:** Mínimo — regex só casa com o pipe `|` seguido de `ref:`, padrão exclusivo
do formato de serviço injetado. Não afeta conteúdo normal.

---

## QW-B3: Expansão do Booking Promise Regex

**Problema:** `_REGEX_AGENDAMENTO_PROIBIDO` cobria apenas 1 de 5 frases de teste.
"reserva confirmada", "ficou marcado", "já deixei marcado", "vou deixar reservado",
"pode ir que já está marcado" passavam sem bloqueio.

**Solução:** Regex expandido com 6 novos padrões:
- `reserva\s+confirmada`
- `agendamento\s+(foi\s+|est[aá]\s+)?(realizado|confirmado|feito|conclu[íi]do)`
- `(ficou|est[aá]|foi)\s+(marcad|agendad|confirmad|reservad)[ao]`
- `j[aá]\s+(deixei|est[aá]|foi)\s+(marcad|agendad|reservad)[ao]`
- `vou\s+(deixar|deixo)\s+(reservad|marcad|agendad)[ao]`
- `pode\s+(ir|vir)\s+que\s+(j[aá]\s+)?est[aá]\s+(marcad|agendad|confirmad)[ao]`

Padrões originais preservados integralmente.

**Arquivo:** `services/ai_service.py` linhas 23-42
**Risco:** Mínimo — `\b` word boundary preserva. `re.IGNORECASE` já estava ativo.

---

## QW-B4: Anti-drift Threshold Reduzido

**Problema:** `ANCORA_ANTI_DRIFT` injetada apenas em `>= 6` mensagens.
Drift já ocorre a partir da 2ª troca (4 mensagens) em conversas sobre disponibilidade.

**Solução:** Threshold alterado de `>= 6` para `>= 4`.

**Arquivo:** `services/ai_service.py` linha 316 (comentário) e 317 (condição)
**Custo:** ~200 tokens extras por chamada de IA em conversas ativas. Aceitável.

---

## SP-2 / GAP-01: Endpoint POST /admin/atendentes/{id}/reativar

**Problema:** Existia `PATCH /admin/atendentes/{id}/desativar` mas não o equivalente
para reativar. Operadores precisavam de acesso SQL direto para reativar atendentes.

O endpoint existente `PATCH /ativar` retornava 400 se já ativo e não publicava SSE.

**Solução:** Adicionado `POST /admin/atendentes/{id}/reativar` com comportamento:
- 404 se atendente não existe
- `{"ok": true, "id": ..., "nome": ..., "ja_ativo": true}` se já estava ativo (idempotente)
- Seta `ativo = True`, commita, publica SSE `presence_changed`
- Retorna `{"ok": true, "id": ..., "nome": ...}` em caso de sucesso

O `PATCH /ativar` existente foi mantido sem alteração (compatibilidade).

**Arquivo:** `api/admin.py` linhas 1591-1618 (após o bloco `/ativar`)
**Migration SQL:** Não necessária — apenas novo endpoint, sem mudança de schema.

---

## Compilação

```
python -m py_compile services/ai_service.py  → OK
python -m py_compile api/admin.py            → OK
```
