# Auditoria de prontidão para produção — Bot WhatsApp + Dashboard · Barbearia Bolshoi

**Data:** 2026-06-08 · **Método:** auditoria multi-agente (segurança, ops/dados, completude funcional, testes/qualidade) **com verificação adversarial em primeira mão** de cada P0. **Escopo:** todo o sistema (bot, IA, WhatsApp, admin/SSE/auth, dados, ops/deploy, LGPD, testes, UX). **Profundidade:** auditável localmente (pytest sobre SQLite/mocks, leitura de código, dashboard via mock) + checklist e2e para o ambiente vivo. **Nenhuma correção foi aplicada** — este é o diagnóstico.

---

## 1. Veredito go/no-go

**🔴 NO-GO para um lançamento limpo HOJE — mas NÃO é uma catástrofe.** É um MVP bem construído, com um **motor de conversa sólido** e **47 testes passando**, segurado por um conjunto **focado e atingível** de bloqueadores que são majoritariamente **operacionais, de conformidade (LGPD) e de configuração de deploy** — não reescrita. Estimo **~1 a 2 semanas** de trabalho dirigido para um **GO responsável**.

A primeira varredura (agentes Explore) pintou um quadro "2/10 catástrofe" que **a verificação desmentiu em vários pontos** (ver §2). O quadro real é melhor — e por isso mais acionável.

> **Resumo de uma linha:** o *cérebro* (regras de negócio + IA + testes) está forte; o que falta é o *corpo de produção* (deploy resiliente, observabilidade, conformidade LGPD, e algumas arestas de fluxo).

---

## Status de execução (atualizado 2026-06-08)

Sprints A/B/C executados em `main`. Suíte: **84 testes verdes** (47 originais → +37). Para o objetivo atual (modo dev/test completo, sem produção ainda), o que restava está coberto ou conscientemente adiado:

| Item | Status | Onde |
|---|---|---|
| **P0-1..P0-4** (LGPD, token 401, deploy/health, horário do banco) | ✅ feito | Sprint A (`c74db64`) |
| **P1-1,2,5,7,9** (Sentry/alerta IA, utf8mb4, reabertura, guard Fred, testes /enviar+/bulk) | ✅ feito | Sprint B backend (`6ae53d5`) |
| **P1-4** (contraste tema claro) | ✅ feito + verificado no browser | redesign (`ec84f54`) |
| **P1-8** (SLA/tempo de espera) | ✅ já existia end-to-end (`transbordo_em`) | — |
| **P1-10** (1 worker) | ✅ documentado | runbook |
| **P2-3** (cron de limpeza) | ✅ `scripts/limpeza.py` + runbook | Sprint C |
| **P2-4** (dep morta google-generativeai) | ✅ removida | Sprint C |
| **P2-6** (saudação com emoji; `intencao` VARCHAR) | ✅ emoji corrigido; VARCHAR já era 50 | Sprint C |
| **P2-7a** (fallback hardcoded do VERIFY_TOKEN) | ✅ removido | Sprint C |
| **P1-6** (descarte silencioso em lock-timeout) | ✅ notifica o cliente | Sprint C |
| **P2-2** (FK CASCADE em canned/filtros) | ✅ resolvido como **documentar** — atendente só é *soft-deleted* (`/desativar` → `ativo=False`), nunca hard-deleted, então o CASCADE **nunca dispara**. Risco teórico. | — |
| **P1-3** (schema drift / Alembic) | ⏳ **adiado** — decisão arquitetural; é o maior pendente | — |
| **P2-1** (circuit breaker NIM/Meta) | ⏳ adiado — resiliência de produção; mexe em estado global (risco p/ suíte) | — |
| **P2-5** (a11y: focus-return/trap nos modais) | ⏳ adiado — passe de frontend dedicado | — |
| **P2-7b** (JWT em query no `/presence`) | ⏳ adiado — `sendBeacon` não envia header; baixo impacto (a própria auditoria classificou) | — |

**Para ir à produção (futuro, decisão do dono):** token permanente Meta, `META_APP_SECRET`, remover `ALLOW_UNSIGNED_WEBHOOK=1`, hospedagem + TLS, e endereçar os 4 itens ⏳ acima (sobretudo P1-3).

---

## 2. Transparência: claims do 1º passe REFUTADOS/recontextualizados

A honestidade brutal começa por aqui — vários "P0" alarmistas do passe inicial **não se sustentaram** na verificação:

| Claim inicial | Veredito verificado | Evidência |
|---|---|---|
| 🔴 "Segredos commitados no Git" | ❌ **FALSO** | `git log --all -- .env` → **vazio** (nunca versionado); `.gitignore:8` ignora `.env` corretamente (e ainda ignora `erro_ia_debug.txt`, dumps de DB — com comentário ciente de LGPD) |
| 🔴 "Zero / nenhum teste" (CLAUDE.md diz "no test suite exists") | ❌ **FALSO** | `pytest tests/` → **47 passed**; `tests/test_auto_cases.py` cobre IDOR, HMAC, JWT, vazamento de segredo |
| 🔴 "P0 configurar TZ=UTC" | ⚠️ **Já tratado no código** | `main.py:7` `os.environ.setdefault("TZ","UTC")` + `tzset()` (server-level TZ ainda recomendado como cinto-e-suspensório) |
| 🔴 "HMAC desligado = endpoint aberto" | ⚠️ **Real, mas o código é defensivo** | `main.py:30-47` **aborta o boot** se `META_APP_SECRET` faltar E `ALLOW_UNSIGNED_WEBHOOK≠1`. O `.env` atual optou por `ALLOW_UNSIGNED_WEBHOOK=1` (dev). É **item de checklist de deploy**, não bug oculto. |
| 🔴 "IDOR P0 — 12 endpoints expõem tudo" | ⚠️ **Real, porém baixa severidade neste contexto** | Há dezenas de checagens `atendente_id == me.id` (enviar/assumir/devolver/transferir/views em `api/admin.py`). Os GET de leitura + status/labels/bulk não filtram por dono — **mas é modelo de caixa-compartilhada** para 1-2 atendentes confiáveis (ADR-011 aceita "sem RBAC"). Importaria com muitos operadores / multi-tenant. |

**Lição:** agentes de varredura ampla alucinam especificidades (números de linha, "está no Git"). Todo P0 abaixo foi **confirmado em primeira mão**.

---

## 3. Forças reais do sistema (o que NÃO mexer)

- **Anti-agendamento robusto (6 camadas):** prompt + âncora anti-drift + **regex determinística** em `_validar_resposta()` + canônicas + sub-fluxo de botões. Funciona **mesmo se a IA ignorar o prompt**. (verificado · `po`)
- **Categorias 💈/💆‍♀️ determinísticas:** separação no banco + sub-fluxo de listagem — não dependem da IA.
- **47 testes verdes** cobrindo webhook pipeline, auth, concorrência (atomicidade do "assumir"), e **segurança** (IDOR/HMAC/JWT/leak) — `tests/` roda em ~0.5s sem MySQL.
- **Higiene de segredos boa:** `.gitignore` ciente de LGPD; `.env` nunca versionado.
- **Guardas defensivas de boot:** exige `META_APP_SECRET` (ou opt-in explícito) e `JWT_SECRET` no modo híbrido (`main.py:30-68`).
- **TZ=UTC forçado no código** (`main.py:7`).
- **Contrato SSE íntegro** (11 tipos publicados = 11 ouvidos no frontend) e regra `\n`(operador)/`<br>`(IA) com 3 testes.
- **Dashboard acessível** (passe recente de WCAG/movimento) — com 2 regressões pontuais de contraste no tema claro (ver P1).

---

## 4. Matriz priorizada (achados verificados)

Severidade **contextualizada para uma barbearia de 1-2 atendentes**. Ação: **[C]orrigir · [A]dicionar · [R]emover**. Esforço: **S/M/L**.

### 🔴 P0 — Bloqueiam um lançamento responsável

| # | Área | Achado (evidência) | Ação | Esf. |
|---|---|---|---|---|
| P0-1 | LGPD | Sem consentimento/opt-in na 1ª mensagem; sem caminho pro cliente apagar dados; nome+telefone+histórico persistidos sem base legal explícita. PII pode cair em `erro_ia_debug.txt` (`ai_service.py:455` loga `Texto recebido: {response_text}`). Risco legal real (ANPD). | **[A]** nota de privacidade no menu de boas-vindas + canônica "apagar meus dados" + sanitizar PII no log | M |
| P0-2 | Resiliência | Token WhatsApp: se for **temporário** (sandbox, 24h), o bot **fica mudo diariamente** sem aviso. `whatsapp.py:14` carrega o token uma vez, sem refresh; falha 401 só vira log. | **[C/A]** confirmar token permanente (System User) + alerta em 401 + procedimento documentado pro Fred | M |
| P0-3 | Deploy | Sem process manager / Docker / Procfile / CI (busca vazia). `main.py:82` roda 1 worker via `uvicorn.run`; se cair, **a barbearia fica muda** até restart manual. Health-check é fake (`GET /` hardcoded "Online", não testa DB). Config de prod precisa de `META_APP_SECRET` setado e `ALLOW_UNSIGNED_WEBHOOK` removido. | **[A]** systemd/Docker com auto-restart + `/health` que faz `SELECT 1` + checklist de config prod | M |
| P0-4 | Regra de negócio | Horário **hardcoded** em `respostas_canonicas.py:24-27` (`_CORPO_HORARIO` texto fixo) — a FAQ responde isso direto, **não lê do banco** (model `Horario` existe e fica subutilizado). Mudar horário = editar código. Pergunta nº1 de barbearia → risco de informar horário errado. **Feriados** (BR-010) só editando o DB na mão. | **[C]** fonte única de horário (DB) + endpoint/script pra feriado sem SQL | M |

### 🟡 P1 — Alto impacto, antes/logo após o go-live

| # | Área | Achado (evidência) | Ação | Esf. |
|---|---|---|---|---|
| P1-1 | Observabilidade | Sem Sentry/error-tracking/métricas/request-id (grep vazio). Quando a IA cai (após 3 retries, `ai_service.py:288-302`), o operador **não é avisado** — bot pode ficar degradado por horas. | **[A]** Sentry (free) + alerta de IA-down + `/metrics` básico | M |
| P1-2 | Dados | `charset utf8mb4` não garantido: connection string sem `?charset=utf8mb4` (`db/database.py`) e `barbearia_bot_db.sql` sem charset na maioria das tabelas → emoji/acento em `nome_cliente` pode corromper. | **[C]** `?charset=utf8mb4` + garantir charset nas tabelas | S |
| P1-3 | Dados | **Schema drift:** `barbearia_bot_db.sql` (~5 tabelas) defasado vs `db/models.py` (13 models); migrations manuais em `scripts/migrations/` sem tracking, algumas não-idempotentes. Restaurar do `.sql` dá schema incompleto. | **[C]** adotar Alembic OU schema canônico único + descontinuar o `.sql` antigo | M |
| P1-4 | UX/a11y (regressão do port) | Tema claro: `.waiting-badge` usa `--warning-text #d97706` (`index.html:681` + `:169`) → contraste **2.72:1 (falha AA)**. Idem chip "Bot ativo" com `--success-text` (~3.77:1). O ADR-013 criou os tokens `-strong` mas **não os aplicou aos badges no light**. | **[C]** apontar badges no light pra `--warning-text-strong`/`--success-text-strong` | S |
| P1-5 | Fluxo | Cliente "resolved" volta com `bot_ativo=False` de handoff anterior → mensagem cai em "bot inativo" e é **descartada sem resposta** (bot_only) ou só persistida (híbrido) — cliente no vácuo. (`webhook.py`, fluxo resolved/bot_ativo) | **[C]** ao reabrir conversa, reativar bot se não houver operador | M |
| P1-6 | Fluxo | Mensagem longa pode estourar o lock de 90s no NIM → **descarte silencioso**, cliente sem aviso. | **[C]** ao expirar lock, avisar/re-enfileirar | S |
| P1-7 | Regra de negócio | **Tom profissional** e **contato do Fred** dependem **só do prompt** (sem guarda determinística, ao contrário do anti-agendamento). Em conversa longa com drift, a IA pode vazar o telefone do Fred ou soltar gíria. | **[A]** regex de proteção ao telefone do Fred (análogo ao anti-agendamento) | S |
| P1-8 | Produto | Sem indicador de **SLA/tempo de espera** na fila de handoff (BR-011/GAP-06 pendente). Cliente em "aguardando" pode esperar sem ninguém ver urgência. | **[A]** badge de tempo-de-espera no dashboard | S |
| P1-9 | Testes | `/admin/enviar` (o endpoint mais usado) e `/admin/conversas/bulk` **sem nenhum teste** → regressão silenciosa. 11 de 39 endpoints sem cobertura. | **[A]** testes p/ `/enviar` e `/bulk` primeiro | S |
| P1-10 | Resiliência/escala | Estado 100% in-memory (`notificador.py` filas SSE; `webhook.py:764-813` locks/rate-limit) **quebra com >1 worker**. Funciona porque roda 1 worker — mas qualquer `--workers 2` quebra em silêncio. | **[C]** documentar "máx. 1 worker" OU migrar p/ Redis antes de escalar | S/L |

### 🟢 P2 — Polish / risco futuro

| # | Área | Achado | Ação |
|---|---|---|---|
| P2-1 | Resiliência | Sem circuit breaker em NIM/Meta: outage de 30min → cada msg gasta ~24s de retry, satura threads. (`ai_service.py:288`, `whatsapp.py:25`) | **[A]** circuit breaker / limite de concorrência |
| P2-2 | Dados | `CannedResponse`/`FiltroSalvo` com FK `CASCADE` (`models.py:193,205`): desativar/deletar atendente apaga canned+views pessoais sem aviso. | **[C]** `SET NULL` ou documentar |
| P2-3 | Dados | `mensagens_processadas` e `historico_conversas` sem limpeza garantida (cleanup oportunista 1%). | **[A]** cron de limpeza |
| P2-4 | Deps | `google-generativeai` em `requirements.txt` é **dependência morta** (código usa NVIDIA). | **[R]** remover |
| P2-5 | a11y | Modais não devolvem foco ao ativador (`app.js:276+`); falta focus-trap. `#metric-cards` oculto — **verificar** se `display:none` (então não focável) ou outro mecanismo; `text-muted` light em `bg-card` = 4.34:1 (levemente < AA). | **[C]** focus return + verificar metric-cards |
| P2-6 | Fluxo | Saudação com emoji ("oi 👋") não casa o regex `_e_saudacao_pura()` → cai na IA em vez do menu. `intencao VARCHAR(30)` pode truncar (TD-015). Frase de reativação-timeout assume handoff anterior. | **[C]** ajustes pontuais |
| P2-7 | Segurança | `VERIFY_TOKEN` com fallback hardcoded (`"barbearia_bot_123"`, webhook handshake) — baixo impacto (só verificação inicial Meta). JWT via query param em `/presence` vaza em logs. | **[C]** remover fallback; mover token do `/presence` p/ header |

---

## 5. O que está SOBRANDO (remover/simplificar para o MVP)

- **[R]** `google-generativeai` (dep morta).
- **[R/arquivar]** **Saved Views** (US-233): backend pronto, **UI nunca feita** — complexidade enterprise que 1-2 atendentes não usam.
- **[Simplificar]** Estados `snoozed_until`/`status_conversa` sem UI completa geram ambiguidade UX (US-271). Avaliar reduzir para o MVP.
- **[Simplificar]** Sub-fluxo de botões em **3 níveis** (Menu → categoria → serviços → ações): 3 cliques pra ver preço. Um menu mais raso pode servir melhor uma barbearia pequena.

---

## 6. Roadmap de remediação sequenciado

**Sprint A — "destravar o lançamento" (P0, ~3-5 dias):**
1. LGPD: nota de privacidade no boas-vindas + canônica "apagar meus dados" + truncar/sanitizar PII em `erro_ia_debug.txt` *(P0-1)*.
2. Token: confirmar/migrar para System User token permanente + alerta em 401 + doc de refresh *(P0-2)*.
3. Deploy: systemd ou Docker com restart + `/health` real + checklist de config prod (`META_APP_SECRET` setado, `ALLOW_UNSIGNED_WEBHOOK` fora) *(P0-3)*.
4. Horário: fonte única (DB) + script/endpoint de feriado *(P0-4)*.

**Sprint B — "estabilizar a 1ª semana" (P1):**
5. Sentry + alerta de IA-down *(P1-1)* · 6. `utf8mb4` *(P1-2)* · 7. Alembic/schema canônico *(P1-3)* · 8. Contraste dos badges no light *(P1-4)* · 9. Edge cases de fluxo resolved/bot_inativo + lock *(P1-5,6)* · 10. Guarda do telefone do Fred *(P1-7)* · 11. SLA badge *(P1-8)* · 12. Testes `/enviar` e `/bulk` *(P1-9)* · 13. Documentar "máx 1 worker" *(P1-10)*.

**Sprint C — "qualidade e escala" (P2):** circuit breaker, crons de limpeza, `SET NULL` em FKs, remover deps mortas, polish de a11y, regex de saudação, simplificações de produto.

---

## 7. Checklist e2e (rodar no SEU ambiente vivo — não dá aqui)

O que esta auditoria **não** pôde exercer (precisa de MySQL + Meta + NVIDIA reais):

- [ ] **Token:** descobrir se o `WHATSAPP_TOKEN` de prod é temporário (24h) ou permanente. Enviar msg de teste, esperar 24h+, reenviar — confirmar se o bot continua respondendo.
- [ ] **HMAC:** em prod, setar `META_APP_SECRET` real e remover `ALLOW_UNSIGNED_WEBHOOK` → confirmar que webhook rejeita POST sem assinatura (403) e aceita os legítimos da Meta.
- [ ] **Charset:** inserir cliente com nome com emoji/acento ("João 💈") e confirmar que não corrompe no MySQL real (`SHOW CREATE TABLE usuarios` deve ser `utf8mb4`).
- [ ] **Fluxo real:** mensagem real → bot responde → "falar com recepção" → operador assume no dashboard → responde → devolve. Confirmar SSE em tempo real, ticks, badges.
- [ ] **IA-down:** simular NIM indisponível (key inválida temporária) → confirmar handoff `transbordo_falha` e que alguém é avisado.
- [ ] **Horário/feriado:** mudar horário e confirmar se a resposta da FAQ acompanha (hoje **não acompanha** — P0-4).
- [ ] **Multi-worker:** NÃO subir com `--workers 2+` até P1-10 (quebra SSE/lock/rate-limit).
- [ ] **Carga:** simular ~10 msg/s e medir latência/erros (sem teste de carga hoje).

---

## 8. Suíte de testes — estado e lacunas

**47 PASS / 0 FAIL** (`pytest tests/`, SQLite/mocks, ~0.5s). Cobertura estimada ~45-55%.

| Arquivo | Nº | Cobre |
|---|---|---|
| `test_webhook_pipeline.py` | 13 | dedup, rate limit, saudação, FAQ canônica, handoff, IA mock |
| `test_admin_endpoints.py` | 13 | login, /conversas, assumir/devolver, labels, notas |
| `test_auto_cases.py` | 18 | JWT, rate limit login, **IDOR**, **HMAC** dev/prod, vazamento de segredo, lock timeout, background exception, `<br>`, gate `META_APP_SECRET` |
| `test_concurrency.py` | 3 | atomicidade do "assumir" |

**Lacunas perigosas:** `/admin/enviar` e `/bulk` sem teste *(P1-9)*; **zero** integração com MySQL real, e2e WhatsApp→NIM, carga, ou multi-worker. **Config:** `pytest` da raiz coleta 0 (falta `testpaths` em `pyproject.toml`/`pytest.ini`) — um CY ingênuo reportaria "no tests"; corrigir a descoberta.

---

## 9. Notas de método

Cada P0 foi **confirmado em primeira mão** (git, grep, leitura de `main.py`/`admin.py`/`webhook.py`/`respostas_canonicas.py`, `pytest`). Achados marcados como "verificar" não foram confirmados em código e **não** devem ser tratados como fato sem checagem. Os relatórios completos dos 4 auditores (`sec`, `ops`, `po`, `qa`) embasam o detalhe; este documento é a síntese verificada.
