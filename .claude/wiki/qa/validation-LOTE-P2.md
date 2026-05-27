# Validação Lote P2 + Recheck P1-8/P1-9
Data: 2026-05-27
Auditor: qa-agent

## RECHECK P1

[P1-8] APROVADO
prompts.py:158,161,164,174,188 — todos os exemplos usam `[HORA_ABERTURA]` e `[HORA_FECHAMENTO]`. Nenhum horário fixo remanescente. Instrução principal (linha 14) intacta.

[P1-9] APROVADO
admin.py:859 — `user.data_ultima_interacao = agora` antes de `db.flush()` (linha 862), fora de todos os branches. Cobertura uniforme.

---

## LOTE P2 — DESIGN SYSTEM (frontend)

[DS-01] APROVADO
index.html:358 — `.conv-card { border-bottom: 1px solid var(--border); }` sem fallback hardcoded.

[DS-02] APROVADO
index.html:403-405 — `#conn-status-dot.connected { background: var(--success, #00a884) !important; }`. Usa var(--success), não var(--ok).

[DS-03] APROVADO
index.html:258 — `.bolha-outgoing-humano .bolha-label { color: var(--bubble-human-label, #d6e8fa); }`. Token com fallback, não raw.

[DS-04] APROVADO
app.js:145-161 — `showToast()` usa `getComputedStyle(document.documentElement)` + `styles.getPropertyValue(v)` para todas as cores (accent, success-text, danger-text, warning-text). Nenhum hex hardcoded.

[DS-05] APROVADO
index.html:1499 — `background: linear-gradient(135deg, var(--accent), var(--accent-hover, #1a5a8f))`. Usa var(--accent-hover) com fallback, não raw primário.

[DS-06] APROVADO
index.html:398-400 — `.presence-dot.online { background: var(--success-text, #3fb950); }`, `.presence-dot.away { background: var(--warning-text, #d29922); }`, `.presence-dot.offline { background: var(--text-muted); }`. Todos com tokens alinhados ao :root.

[DS-07] APROVADO
index.html:1081-1084 — seletores `.row-client + .row-client`, `.row-bot + .row-bot`, `.row-human + .row-human` com `margin-top: 2px`. Cauda e label ocultos em rows consecutivas (linhas 1086-1097). Implementação correta.

[DS-08] APROVADO
index.html:1143-1149 — `@media (prefers-reduced-motion: reduce) { *, *::before, *::after { animation: none !important; transition: none !important; } }`.

[DS-09] APROVADO
index.html:1149 — `#chat-empty-state svg { animation: none !important; }` dentro do bloco prefers-reduced-motion.

[DS-10] APROVADO
index.html:407 — `#conn-status-dot.failed { background: var(--danger-text) !important; }` presente.

---

## LOTE P2 — BACKEND

[BE-01] APROVADO
whatsapp.py:27-33 — bloco `if response.status_code == 429:` lê `response.headers.get("Retry-After", 5)`, converte para int, loga warning e chama `time.sleep(retry_after)` se `attempt < 2`. Fallback 5s correto.

[BE-02] APROVADO
whatsapp.py:47-53 — `response.json()` dentro de `try/except ValueError`, retorna `(False, None)` em erro de parsing JSON.

[BE-03] APROVADO
admin.py:864-867 — `except Exception as exc: db.rollback()` dentro do loop de bulk_acao(). Rollback por item confirmado com comentário explicativo.

[BE-04] APROVADO
webhook.py:1272-1280 — bloco explícito: verifica MensagemProcessada e insere se ausente, com try/except e rollback. Garante deduplicação mesmo após retorno precoce do handler de mídia.

[BE-05] APROVADO
admin.py:1531 — `CannedResponse.atendente_id.is_(None)` quando `aid is None`. Usa `.is_(None)`, não `== None`.

[BE-06] APROVADO
admin.py:1834 — `db.flush()` em criar_nota() antes de _processar_mentions(). admin.py:1812 — `db.flush()` em _processar_mentions() sem commit interno. admin.py:1840 — `db.commit()` único em criar_nota() após _processar_mentions(). Transação única confirmada.

---

## Resumo

Recheck P1: 2/2 aprovados
DS: 10/10 aprovados
BE: 6/6 aprovados

**Total: 18/18 aprovados**
