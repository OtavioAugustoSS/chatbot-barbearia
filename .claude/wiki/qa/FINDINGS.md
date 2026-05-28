---
type: qa
title: "FINDINGS — QA Full Sweep"
updated: 2026-05-27
tags: [qa, findings, full-sweep]
related: ["[[RECON_REPORT]]", "[[TEST_PLAN]]", "[[FINAL_REPORT]]"]
---

# FINDINGS — QA Full Sweep (incremental)

Severidade: **P0** bloqueia prod/segurança/perda de dados · **P1** quebra fluxo principal ·
**P2** degrada UX · **P3** polimento. Status: `OPEN` / `RESOLVED` / `ACEITO`.

---

## Bloco 1 — Análise estática de segurança (Lead, sem servidor live)

Veredito do bloco: **postura de segurança forte**. A mega-auditoria recente (commit a01dd1e)
endureceu os caminhos de alto risco. Nenhum P0 confirmado na passada estática. Achados abaixo
são P1 de deploy + P2/P3.

### SEC-01 — Webhook aceita POST sem assinatura quando META_APP_SECRET ausente [P1] RESOLVED
- **Fix:** `main.py` — gate rígido no boot: `RuntimeError` se `META_APP_SECRET` ausente e
  `ALLOW_UNSIGNED_WEBHOOK` não for `1`/`true`/`yes`. Para dev local sem assinatura, definir
  `ALLOW_UNSIGNED_WEBHOOK=1` explicitamente (log WARNING, não boot silencioso).
- **`.env.example`** atualizado com documentação de `META_APP_SECRET` e `ALLOW_UNSIGNED_WEBHOOK`.
- **Testes:** `tests/conftest.py` atualizado com `ALLOW_UNSIGNED_WEBHOOK=1`; 43/43 PASS.
- **Verificação manual:** sem `META_APP_SECRET` e sem flag → `RuntimeError` confirmado; com flag → boot com WARNING confirmado.

### SEC-02 — `file.name` interpolado cru em innerHTML (self-XSS) [P3] OPEN
- **Onde:** `static/admin/js/app.js:2862` — `chip.innerHTML = \`<span title="${file.name}">${file.name}</span>...\``.
- **Risco:** baixo. Só o próprio operador, ao anexar um arquivo com nome malicioso
  (`<img onerror=...>`), executaria script na própria sessão (self-XSS). Sem cross-user.
- **Fix:** `escapeHtml(file.name)` ou usar `textContent`. Trivial (frontend-agent).

### SEC-03 — `/admin/search` não escapa wildcards LIKE [P3, funcional] OPEN
- **Onde:** `api/admin.py:637` — `termo = f"%{q}%"`. Valor é bound-param (sem SQLi), mas `%` e `_`
  em `q` agem como wildcards.
- **Risco:** apenas funcional — buscar `100%` ou `a_b` retorna resultados inesperados. Não é
  segurança.
- **Fix:** escapar `% _ \` em `q` e usar `.like(termo, escape='\\')`.

### SEC-04 — Sem isolamento por operador (qualquer um lê qualquer conversa) [P2] ACEITO?
- **Onde:** `api/admin.py` — `atendente_atual` valida só o JWT (operador ativo), não a posse da
  conversa. `GET /admin/conversa/{tel}` e search expõem qualquer telefone.
- **Contexto:** documentado em **ADR-011** (RBAC ausente, modelo inbox compartilhado tipo Chatwoot).
  `devolver` e `notas` PATCH/DELETE **têm** checagem de posse (`atendente_id=me.id` / só criador).
- **Decisão humana (PO):** confirmar que para 1–2 operadores da barbearia o inbox compartilhado é
  aceitável. Se sim → ACEITO (referencia ADR-011). Se houver requisito de privacidade entre
  operadores → vira P1.

### SEC-05 — Timing side-channel na enumeração de usuário no login [P3] OPEN
- **Onde:** `api/admin.py:172` — `if not atendente or ... or not verificar_senha(...)` curto-circuita;
  bcrypt só roda se o usuário existe → resposta mais lenta para usuário válido.
- **Risco:** baixíssimo (rate-limit 5/60s por IP, 1–2 operadores). Permite inferir existência de
  login por tempo de resposta.
- **Fix (opcional):** rodar um bcrypt dummy quando o usuário não existe.

### Pontos positivos confirmados (cobertura — o que está OK)
- **XSS:** helper `escapeHtml` (app.js:62, escapa `& < > " '`) aplicado consistentemente em TODOS
  os renders de conteúdo controlado por cliente/operador: bolha de mensagem (924 — escapa **antes**
  do `\n→<br>`), lista de conversas (530-531), busca (2070/2073), notas (2206/2210), menções
  (1833/1836), labels (478/487), mídia caption/filename (911/918). Atributos via `escapeHtml`
  + leitura por `getAttribute`/`textContent`.
- **SQLi:** queries via ORM SQLAlchemy com bound params (`.like(termo)`, `.filter(... == ...)`).
  Sem concatenação de SQL cru.
- **HMAC webhook:** `hmac.compare_digest` (constant-time) quando o secret existe.
- **Vazamento de secret:** `senha_hash` nunca serializado (`GET/POST /atendentes` retornam campos
  explícitos). `JWT_SECRET` com gate (login → 503 se ausente; `criar_token` levanta RuntimeError).
- **Mass-assignment:** bodies são modelos Pydantic com campos explícitos + `Literal` enums +
  bounds (`min_length`/`max_length`). `Atendente` criado com campos explícitos, `ativo=True`
  hardcoded.
- **Login:** rate-limit por IP (429), mensagem genérica "Credenciais inválidas" (sem enumeração
  explícita), bcrypt, JWT_SECRET gate, log de tentativas inválidas.
- **Race "assumir":** UPDATE condicional `WHERE atendente_id IS NULL` + tratamento `afetadas==0`
  → 409 para o perdedor (admin.py:458-477). Correto.

---

## Bloco 1b — Runtime / dependências (Lead, ao subir o servidor)

### DEP-01 — `python-multipart` ausente quebra o boot em modo híbrido [P1] RESOLVED
- **Sintoma:** `python main.py` (hibrido) → `RuntimeError: Form data requires "python-multipart"
  to be installed` ao importar o router admin (`api/admin.py:1001`, endpoint
  `/admin/enviar-midia/{telefone}` usa `UploadFile`/`Form`). Servidor não sobe.
- **Causa raiz:** a feature de upload de mídia (sprint a01dd1e) adicionou o endpoint multipart mas
  `python-multipart` **nunca foi declarado** em `requirements.txt` nem instalado no `.venv`.
  Um `pip install -r requirements.txt` limpo + boot em hibrido falha.
- **Evidência:** `pip show python-multipart` → não instalado; `requirements.txt` não listava.
- **Fix aplicado:** adicionado `python-multipart` ao `requirements.txt` + instalado no `.venv`.
  Após o fix, `import api.admin` OK e app sobe.
- **Severidade:** P1 (bloqueia deploy/boot em ambiente novo). Era latente — só não pegou quem já
  tinha a lib por acaso.
- **Nota de limpeza (P3):** `google-generativeai==0.8.3` consta em `requirements.txt` mas é dead
  dep (código usa NVIDIA NIM via `openai`; `GEMINI_API_KEY` não é usado). Candidato a remoção.

## Bloco 2 — Harness pytest (backend-agent) — CONCLUÍDO

**`pytest -q` resultado real (2026-05-27):** `43 passed, 2 warnings in 11.56s`

Arquivos de teste:
- `tests/conftest.py` — fixtures SQLite in-memory, mocks WhatsApp+NIM
- `tests/test_admin_endpoints.py` — 13 testes (login, auth, conversas, assumir, devolver, labels, notas)
- `tests/test_webhook_pipeline.py` — 13 testes (dedup, rate limit, saudação, FAQ canônica, handoff H-02, IA)
- `tests/test_concurrency.py` — 3 testes (assumir sequencial H-03/C-01, UPDATE condicional, devolver+reassumir)
- `tests/test_auto_cases.py` — 14 testes (A-02 token expirado, A-04 rate limit login, H-05 devolver alheio, V-04 HMAC, V-06 no-leak, C-05 lock timeout, R-04 background exception, normalização BR-003)

### Casos [AUTO] verificados pelo harness

| ID | Caso | Resultado |
|---|---|---|
| H-02 | JSON inválido → transbordo_falha (não crash) | PASS |
| H-03/C-01 | Dois assumir ~simultâneos → 1×200 + 1×409 | PASS |
| H-05 | B não devolve conversa de A (UPDATE cond.) | PASS |
| C-04 | Dedup message_id (processa 1×) | PASS |
| C-05 | Lock timeout 90s não causa starvation | PASS |
| A-01 | Sem token → 401 | PASS |
| A-02 | Token expirado → 401 | PASS |
| A-04 | Rate limit login 5/60s → 429 | PASS |
| V-04 | HMAC ausente = dev mode aceita; com secret inválido → 403 | PASS |
| V-06 | senha_hash e JWT_SECRET não vazam em nenhuma resposta | PASS |
| R-04 | Exceção em background task capturada na raiz (ADR-010) | PASS |
| BR-003 | `<br>` → `\n`, colapso 3+ quebras, strip | PASS |

### BUG-01 — FAQ canônica não cobre "como faço para agendar?" [P2] OPEN

- **Onde:** `core/respostas_canonicas.py:168` — regex `_PADROES` lista agendamento.
- **Evidência:** `detectar_resposta_canonica("como faço para agendar?")` → `None`. Cai na IA.
- **Esperado:** retornar `RESPOSTA_AGENDAMENTO` (redirect AppBarber), poupando token NVIDIA.
- **Causa:** padrão cobre `"como agendar"` e `"quero agendar"` mas não `"como faço para"` + verbo.
- **Fix:** adicionar `r"como\s+(eu\s+)?fa[çc]o\s+para\s+(agendar|marcar)|"` ao regex de agendamento.
- **Teste documentador:** `tests/test_auto_cases.py::test_faq_gap_como_faco_para_agendar` — passa enquanto o bug existe (documenta comportamento atual); deve ser **invertido** após o fix.

### BUG-02 — Mock `_FakeChoice.finish_reason` no harness estava na classe errada [P0-harness] RESOLVED

- **Onde:** `tests/conftest.py` (corrigido antes do commit).
- **Evidência:** `completion.choices[0].finish_reason` levantava `AttributeError` silencioso → disparava `transbordo_falha` em vez da resposta normal da IA. Todos os testes de IA passavam como falso-positivo.
- **Corrigido:** `finish_reason` movido para `_FakeChoice` (não `_FakeMsg`).

---

## Bloco 3 — E2E Playwright (Lead, servidor live localhost:8000) — PARCIAL

Servidor já rodava em :8000 (instância pré-existente, Meta API **real**). Por segurança
**não disparei** assumir/enviar/devolver/mídia (mandaria WhatsApp real a clientes reais).
Limitei a interações read-only/internas. Atendente de teste `qa_sweep` criado (id=4).

### Validado (PASS)
- **Login (A-01 path):** `POST /admin/login` → 200 + JWT válido; UI login → redirect ao dashboard.
- **Dashboard render:** sidebar, métricas (0 aguardando / 0 atendendo / 3 com bot), 4 conversas reais.
- **SSE:** status "Conectado" (conecta no load). Sem erro de stream.
- **Empty-state (F-01):** "Nenhuma conversa selecionada" antes de abrir thread.
- **Render de histórico (P-01):** thread do Otavio (52 msgs) em ordem cronológica, com separadores
  de data ("sábado, 16 de maio" … "Ontem"), bolhas Cliente/Bolshoi Bot/Atendente, timestamps,
  ticks (SVG). Sem duplicação/sumiço aparente.
- **Info panel:** populado (Cliente desde 14/05/2026, última atividade 21h, 52 mensagens,
  25 atend. humanos, STATUS "Bot inativo", "Nenhuma etiqueta", "Nenhuma nota ainda").
- **Composer desabilitado p/ conversa de outro operador:** "Esta conversa está sendo atendida por
  outro operador" + `#attach-btn`/`#msg-input`/`#send-btn` `disabled`. Valida o fix do sprint.
- **Regras de negócio visíveis no histórico:** anti-agendamento (BR-001) — respostas do bot
  redirecionam p/ `sites.appbarber.com.br/bolshoi`; contato do Fred só após pedido explícito
  ("queria falar com o fred" → "(38) 99897-0661"); preços via DB.
- **Console:** só `favicon.ico` 404 (cosmético) + warning Tailwind CDN. Zero erro JS.

### Achados novos (E2E)
- **UI-01 [P3]** Tailwind via CDN (`cdn.tailwindcss.com`) emite warning "should not be used in
  production". Aceito em dev (ADR-007 permite libs CDN), mas em prod recomenda build/CLI (purge,
  sem dep externa em runtime). Documentar/decidir.
- **UI-02 [P3]** `favicon.ico` 404 — cosmético. Adicionar favicon ou `<link>` vazio.
- **UI-03 [P3]** Menu gerado pela IA às vezes usa emojis diferentes do menu canônico
  (ex: "✅️/👨‍🏫/🎁" vs "✂️/👨‍🎨/📅"). Inconsistência visual menor; canônico deveria prevalecer.
- **Nota P-02 (timezone):** horários renderizam consistentes (tooltip ISO + relativo "Ontem"/"21h").
  Verificação profunda UTC↔BRT (UTC-3) fica para reteste com dado controlado.

### Ainda bloqueado — requer WhatsApp inbound real (ngrok + telefone de teste)
> Usuário optou por subir o ambiente; estes casos aguardam telefone de teste controlado p/ não
> afetar clientes reais:

| ID | Caso | Bloqueio |
|---|---|---|
| F-01..F-07 | Dashboard funcional (empty-state, skeleton, assumir UI, draft, Cmd+K, erro 500, retry) | servidor live |
| H-01 | chamar_recepcao → SSE novo_transbordo chega no painel | WhatsApp real |
| H-04 | Handoff sem atendente → fica em "aguardando" | servidor live |
| S-01..S-06 | SSE real-time (nova_mensagem, reconexão, tick ✓✓ azul) | servidor live |
| C-02 | Lock por telefone durante handoff (sem dupla resposta) | WhatsApp real |
| C-03 | Browser fecha → presence offline em 90s | servidor live |
| P-04 | Reload preserva estado | servidor live |
| PF-03 | 1000+ msgs sem travar render | servidor live + dados |
| U-01..U-04 | WCAG AA, teclado, mobile, leitor de tela | servidor live + browser |

**Para iniciar:** suba o servidor (`python main.py` com `.env` de produção), exponha com ngrok, crie um atendente de teste via `scripts/criar_atendente.py`, e informe as credenciais + URL para o próximo ciclo do QA.

---

## Bloco 4 — Fase D: loop fix → reteste (backend-agent)

**Regressão final (`pytest -q`, 2026-05-27):** `43 passed` (0 falhas)

### BUG-01 — FAQ canônica não cobre "como faço para agendar?" [P2] RESOLVED

- **Fix:** `core/respostas_canonicas.py` — adicionado `r"como\s+(eu\s+)?fa[çc]o\s+para\s+(agendar|marcar)|"` ao bloco de padrões de agendamento (inserido após `r"como\s+marc(o|ar)|"`).
- **Teste:** `test_faq_gap_como_faco_para_agendar` invertido para `assert resp is not None`.
- **Regressão:** 43/43 PASS.

### SEC-02 — `file.name` interpolado cru em innerHTML (self-XSS) [P3] RESOLVED

- **Fix:** `static/admin/js/app.js:~2862` — `escapeHtml(file.name)` aplicado em `title=` e conteúdo do chip de anexo.
- **Verificação:** frontend-only; sem impacto no harness pytest.

### SEC-03 — `/admin/search` não escapa wildcards LIKE [P3] RESOLVED

- **Fix:** `api/admin.py:~636` — escape de `\`, `%`, `_` em `q` antes de montar o LIKE; `.like(termo, escape="\\")` nas duas condições de filtro.
- **Regressão:** 43/43 PASS.

### SEC-05 — Timing side-channel login (enumeração de usuário) [P3] RESOLVED

- **Fix:** `api/admin.py:~171` — quando `atendente` não existe, executa `verificar_senha(payload.senha, "$2b$12$dummyhash...")` para equalizar tempo de resposta antes de lançar 401.
- **Regressão:** 43/43 PASS.

### Findings pendentes (aguardam decisão humana)

| ID | Severidade | Status | Bloqueio |
|---|---|---|---|
| SEC-01 | P1 | OPEN | Decisão de política de gate: `META_APP_SECRET` obrigatório em prod (abort boot) vs flag `ALLOW_UNSIGNED_WEBHOOK=1`. Confirmação do usuário necessária antes de implementar. |
| SEC-04 | P2 | ACEITO? | PO deve confirmar que inbox compartilhado (ADR-011, sem RBAC por conversa) é aceitável para 1–2 operadores da barbearia. |
