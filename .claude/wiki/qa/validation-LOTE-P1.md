# Validação Lote P1
Data: 2026-05-27
Auditor: qa-agent

## Resultado: 8/10 aprovados

---

[P1-1] APROVADO
index.html:788 — `[data-theme="light"] #messages-area { background-color: var(--bg-chat); }` presente.

[P1-2] APROVADO
app.js:556-557 — `isUnread = (c.aguardando_humano && !c.atendente_id) || (c.mensagens_nao_lidas > 0)`. TODO(backend) documentado no comentário da linha 554.

[P1-3] APROVADO
app.js:547 — `const tempoBase = c.transbordo_em || c.ultima_mensagem_em`. Fallback correto.

[P1-4] APROVADO
app.js:1415-1419 — após `await api.enviarMidia(...)` + `_limparAttach()`, chama `await abrirConversa(state.conversaAtual)` na linha 1419.

[P1-5] APROVADO
app.js:565 — `<div class="avatar w-11 h-11 rounded-full ...">`. Classe `avatar` presente.

[P1-6] APROVADO
index.html:1283 — `@media (max-width: 1023px) { #empty-state { display: flex !important; } }` presente.

[P1-7] APROVADO (com observação)
admin.py:453-454 — `if user.atendente_id == me.id: raise HTTPException(status_code=400, ...)` antes do UPDATE.
Observação: a checagem retorna 400 "Você já é o atendente desta conversa." — semântica correta. O critério do fix estava especificado como check antes do UPDATE com retorno 400, o que está implementado.

[P1-8] REPROVADO: horários específicos ainda existem no prompt como exemplos
core/prompts.py:14 — instrução para usar contexto temporal injetado está presente. PORÉM o fix não é completo: linhas 158, 161, 164 e 188 contêm horários hardcoded ("14:00 às 21:00", "09:00 às 21:00", "09:00 às 18:00") dentro de exemplos de resposta do próprio SYSTEM_PROMPT. Quando a IA usa esses exemplos como template, ela pode emitir horários hardcoded mesmo que o contexto temporal diga outro valor. A instrução na linha 14 diz "nunca cite horários fixos desta seção" mas as seções de exemplos (linhas 145-188) ainda contêm os horários.

[P1-9] REPROVADO: bulk_acao() não atualiza data_ultima_interacao
admin.py:776-864 — assumir() (linha 469) e devolver() (linha 1107) têm `data_ultima_interacao: datetime.now(timezone.utc)` no UPDATE com `synchronize_session=False`. bulk_acao() usa atribuição direta em objeto ORM (user.status_conversa = ..., user.atendente_id = ...) sem setar `user.data_ultima_interacao = agora`. A variável `agora` existe (linha 790) mas não é atribuída ao campo. Fix: adicionar `user.data_ultima_interacao = agora` em cada branch de bulk_acao (resolver, snooze, atribuir).

[P1-10] APROVADO
app.js:1916 — `Object.assign(state.presence, data || {})`. Confirmado (validado no lote P0, sem regressão).

---

## Ações requeridas

**P1-8** (frontend-agent / backend-agent): remover ou neutralizar os horários hardcoded das linhas de exemplo no SYSTEM_PROMPT_BARBEARIA (prompts.py:158, 161, 164, 188). Substituir por placeholders como `{horario_amanha}` ou remover os exemplos com horas fixas.

**P1-9** (backend-agent): em `bulk_acao()` (admin.py:799-857), adicionar `user.data_ultima_interacao = agora` em cada branch de ação (resolver, snooze, atribuir, label_add, label_remove) antes de `resultados["sucesso"].append(tel)`.
