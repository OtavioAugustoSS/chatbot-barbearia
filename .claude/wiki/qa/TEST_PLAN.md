---
type: qa
title: "TEST_PLAN — QA Full Sweep"
updated: 2026-05-27
tags: [qa, test-plan, full-sweep]
related: ["[[RECON_REPORT]]", "[[FINDINGS]]"]
---

# TEST PLAN — Fase B do QA Full Sweep

Casos Dado/Quando/Então. Marcação: `[AUTO]` automatizável agora (TestClient/curl/leitura);
`[E2E]` precisa servidor live (Lead+Playwright); `[USER-IN-LOOP]` precisa WhatsApp inbound real.
Severidade-alvo entre colchetes ao fim de casos críticos.

---

## 1. Funcional — painel do atendente

- **F-01 [E2E]** Dado dashboard sem conversas, Quando carrego, Então vejo empty-state
  ("Nenhuma conversa") e nenhum erro de console.
- **F-02 [E2E]** Dado lista carregando, Quando a request `/admin/conversas` está pendente, Então
  vejo skeleton (não tela branca).
- **F-03 [E2E]** Dado conversa aberta, Quando clico "assumir", Então botão entra em loading, some
  e aparece "devolver"; composer habilita.
- **F-04 [E2E]** Dado composer com texto, Quando dou refresh, Então draft (`localStorage.draft_{tel}`)
  é restaurado.
- **F-05 [E2E]** Dado foco no input, Quando aperto Cmd+K/Ctrl+K, Então abre command palette.
- **F-06 [E2E]** Dado erro 500 em `/admin/conversas`, Quando ocorre, Então UI mostra estado de erro
  legível (não trava). [P2]
- **F-07 [E2E]** Dado mensagem que falhou no envio, Quando clico retry, Então reenvia e atualiza tick.

## 2. Handoff IA→humano

- **H-01 [USER-IN-LOOP]** Dado cliente pedindo atendente, Quando IA classifica `chamar_recepcao`,
  Então `bot_ativo=False`, `aguardando_humano=True`, SSE `novo_transbordo` chega no painel. [P1]
- **H-02 [AUTO]** Dado IA retorna JSON inválido, Quando parse falha, Então `intencao=transbordo_falha`
  e handoff dispara (não crash). [P1]
- **H-03 [AUTO]** Dado dois atendentes, Quando ambos `POST /assumir/{tel}` ~simultâneo, Então só 1
  recebe 200, o outro 409. (admin.py:458-477) [P0]
- **H-04 [E2E]** Dado nenhum atendente online, Quando handoff dispara, Então conversa fica em
  "aguardando" sem perder mensagem.
- **H-05 [AUTO]** Dado conversa assumida por A, Quando B tenta `devolver`, Então não consegue
  (UPDATE condicional `atendente_id=me.id`). [P1]
- **H-06 [USER-IN-LOOP]** Dado bot_only mode, Quando handoff dispara, Então resposta vira redirect
  AppBarber (não promessa de humano). [P1] (regra PO)

## 3. SSE / real-time

- **S-01 [E2E]** Dado painel aberto, Quando cliente manda msg, Então `nova_mensagem` aparece
  incrementalmente (sem reload). [P1]
- **S-02 [E2E]** Dado SSE conectado, Quando derrubo a rede 5s e volto, Então reconecta com backoff
  e não duplica eventos. [P1]
- **S-03 [E2E]** Dado aba em background, Quando chega evento, Então é processado ao focar.
- **S-04 [E2E]** Dado JWT a <2min de expirar, Quando o tempo passa, Então banner aparece, draft é
  salvo e há auto-logout em exp. [P2]
- **S-05 [AUTO]** Dado fila SSE cheia (>100), Quando novo evento chega, Então drop-oldest (ADR-005)
  sem travar stream.
- **S-06 [E2E]** Dado msg enviada, Quando Meta confirma `read`, Então tick vira ✓✓ azul via
  `mensagem_lida`.

## 4. Concorrência / race

- **C-01 [AUTO]** = H-03 (dois assumir). [P0]
- **C-02 [USER-IN-LOOP]** Dado handoff em andamento, Quando cliente manda msg no meio, Então não há
  perda nem dupla resposta (lock por telefone). [P1]
- **C-03 [E2E]** Dado atendente atendendo, Quando fecha o browser, Então presence vai offline em
  ~90s e conversa não fica órfã travada.
- **C-04 [AUTO]** Dado mesma `message_id` reenviada pela Meta, Quando chega 2x, Então dedup
  (`MensagemProcessada`) processa só 1x. [P1]
- **C-05 [AUTO]** Dado lock de telefone preso, Quando passa 90s, Então acquire-timeout libera
  (sem starvation).
- **C-06 [AUTO]** Dado transferência concorrente (A→B e A→C), Quando simultâneas, Então estado
  final consistente (1 dono). [P1]

## 5. Persistência / consistência

- **P-01 [AUTO]** Dado conversa com N msgs, Quando reabro, Então ordem cronológica correta, sem
  dup, sem sumiço. [P1]
- **P-02 [AUTO]** Dado timestamps UTC no DB, Quando renderizo no painel, Então exibe horário
  Brasil (UTC-3) correto. [P1] (TD-001)
- **P-03 [AUTO]** Dado histórico >50 msgs, Quando cresce, Então trim mantém as 50 mais novas.
- **P-04 [E2E]** Dado reload no meio de uma conversa, Quando recarrego, Então estado (conversa
  ativa, composer) é preservado.

## 6. Auth / autorização

- **A-01 [AUTO]** Dado sem token, Quando chamo `/admin/conversas`, Então 401. [P0]
- **A-02 [AUTO]** Dado token expirado, Quando chamo endpoint, Então 401 e front redireciona login.
- **A-03 [AUTO]** Dado atendente A logado, Quando lê `/admin/conversa/{tel de outro}`, Então
  (RBAC ausente, ADR-011) confirma se isso é aceito ou IDOR. [P0 se vazar dados sensíveis]
- **A-04 [AUTO]** Dado 6 logins errados em 60s, Quando 6º, Então rate-limit bloqueia (5/60s/IP). [P1]
- **A-05 [AUTO]** Dado logout, Quando reuso o token antigo, Então comportamento documentado
  (JWT stateless — token válido até exp; confirmar se é risco aceito). [P2]

## 7. Validação / segurança

- **V-01 [AUTO]** Dado mensagem com `<script>alert(1)</script>`, Quando renderiza no painel,
  Então é escapada (sem XSS). **Checar `innerHTML` vs `textContent` em app.js.** [P0]
- **V-02 [AUTO]** Dado filtros de `/admin/search` e `/admin/conversas`, Quando injeto SQL/LIKE
  wildcards, Então parametrizado (SQLAlchemy) sem injeção; LIKE escapa `%_`. [P0/P1]
- **V-03 [AUTO]** Dado `/admin/conversa/55XXX`, Quando troco para `/admin/conversa/55YYY`, Então
  IDOR avaliado vs ADR-011. [P0/P1]
- **V-04 [AUTO]** Dado `POST /webhook` sem assinatura, Quando `META_APP_SECRET` setado, Então
  rejeita (HMAC). Sem o secret → dev mode aceita (documentar risco). [P0 em prod]
- **V-05 [AUTO]** Dado `/webhook` público, Quando floodado, Então rate-limit/dedup mitigam. [P1]
- **V-06 [AUTO]** Dado resposta de qualquer endpoint, Quando inspeciono, Então nenhum secret
  (tokens, hash de senha, JWT_SECRET) vaza pro client. [P0]
- **V-07 [AUTO]** Dado `POST /atendentes` com payload extra, Quando enviado, Então sem
  mass-assignment de campos sensíveis (ex: setar `ativo`/id arbitrário). [P1]

## 8. Performance

- **PF-01 [AUTO]** Dado `/admin/conversas` filtrado, Quando rodo `EXPLAIN`, Então usa índice
  (`idx_usuarios_status_conversa`) — sem full scan. [P2]
- **PF-02 [AUTO]** Dado `/admin/search` LIKE, Quando base grande, Então medir latência (sem
  FULLTEXT, TD-007) e documentar. [P2]
- **PF-03 [E2E]** Dado conversa com 1000+ msgs, Quando abro, Então render não trava a aba. [P2]
- **PF-04 [AUTO]** Dado listagem de conversas com labels/notas, Quando carrega, Então sem N+1
  óbvio. [P2]

## 9. Resiliência

- **R-01 [AUTO]** Dado NVIDIA fora, Quando IA é chamada, Então retry tenacity 3x (ADR-003), depois
  fallback/handoff sem crash; erro em `erro_ia_debug.txt`. [P1]
- **R-02 [AUTO]** Dado MySQL fora, Quando endpoint chamado, Então erro tratado (não 500 cru com
  stacktrace pro client). [P1]
- **R-03 [E2E]** Dado SSE fora, Quando cai, Então front reconecta e sinaliza visualmente
  (connecting/failed). [P2]
- **R-04 [AUTO]** Dado exceção no background task, Quando ocorre, Então `tarefa_em_segundo_plano_ia`
  captura na raiz (ADR-010) e não derruba o worker.

## 10. UX / acessibilidade

- **U-01 [E2E]** Dado dark e light, Quando inspeciono contraste de texto/botões, Então atende WCAG
  AA mínimo. [P3]
- **U-02 [E2E]** Dado teclado só, Quando navego até "assumir", Então focável e acionável (Enter). [P2]
- **U-03 [E2E]** Dado mobile (drawer), Quando abro conversa, Então layout responsivo sem overflow.
- **U-04 [E2E]** Dado leitor de tela, Quando foco no botão "assumir", Então tem label acessível. [P3]

## 11. Logs / observabilidade

- **L-01 [AUTO]** Dado um incidente simulado, Quando leio os logs, Então dá pra rastrear telefone,
  intenção, erro (sem precisar de debugger). [P2]
- **L-02 [AUTO]** Dado logs em nível INFO, Quando inspeciono, Então não vaza PII desnecessária
  (conteúdo completo de mensagens, tokens). [P1]
- **L-03 [AUTO]** Dado `erro_ia_debug.txt`, Quando IA falha, Então registra timestamp ISO + payload
  (só em DEBUG?). Confirmar que não cresce sem rotação.

---

## Ordem de execução sugerida
1. **Bloco AUTO sem servidor** (leitura + TestClient + mocks): V-01..V-07, H-02/H-03/H-05,
   C-04/C-05/C-06, P-01/P-02/P-03, A-01..A-05, R-01/R-02/R-04, L-01..L-03, PF-01/PF-02/PF-04.
   → Roda agora, gera maioria dos achados de segurança/lógica.
2. **Bloco E2E** (servidor live + Playwright): F-*, S-*, P-04, PF-03, U-*, R-03, C-03.
3. **Bloco USER-IN-LOOP** (WhatsApp real): H-01, H-04, H-06, C-02, S-01/S-06 ponta-a-ponta.
