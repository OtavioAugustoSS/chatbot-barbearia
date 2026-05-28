---
type: qa
title: "FINAL_REPORT — QA Full Sweep"
updated: 2026-05-27
tags: [qa, final-report, full-sweep]
related: ["[[RECON_REPORT]]", "[[TEST_PLAN]]", "[[FINDINGS]]"]
---

# FINAL REPORT — QA Full Sweep (Barbearia Bolshoi)

Branch: `qa/full-sweep` · Orquestração: time `barbearia-bolshoi-team` (Lead + backend-agent).

## 1. Sumário executivo

O sistema está **quase pronto para produção**, pendente de **uma decisão de política de deploy
(SEC-01)** e **um aceite de produto (SEC-04)** — ambos exigem confirmação humana, não código novo.
A postura de qualidade é **forte**: a mega-auditoria recente (commit `a01dd1e`) já havia endurecido
XSS, SQLi, secrets e a corrida de "assumir". Este sweep (a) criou o **harness de testes que não
existia** (TD-002) com **43 testes passando**, (b) achou e corrigiu **1 bug de boot crítico** que
impedia o servidor de subir num ambiente limpo (DEP-01, `python-multipart`), (c) corrigiu 4 achados
de menor severidade (BUG-01 FAQ, SEC-02/03/05), e (d) validou por E2E real (Playwright) o login, o
dashboard, SSE, render de histórico e os estados de composer. **Zero P0 em aberto. O único P1 em
aberto (SEC-01) é uma política de deploy a definir.**

## 2. Tabela de achados

| ID | Sev | Área | Status | Fix / commit |
|---|---|---|---|---|
| DEP-01 | P1 | deps/boot | **RESOLVED** | `python-multipart` add em `requirements.txt` + install |
| SEC-01 | P1 | segurança/deploy | **OPEN** (decisão humana) | gate de boot p/ `META_APP_SECRET` em prod — aguarda política |
| BUG-01 | P2 | FAQ/IA-custo | **RESOLVED** | regex agendamento em `respostas_canonicas.py` + teste invertido |
| SEC-04 | P2 | autorização | **ACEITO?** (decisão PO) | inbox compartilhado (ADR-011) — aguarda aceite |
| SEC-02 | P3 | XSS (self) | **RESOLVED** | `escapeHtml(file.name)` em `app.js` |
| SEC-03 | P3 | busca | **RESOLVED** | escape de wildcards LIKE em `/admin/search` |
| SEC-05 | P3 | login/timing | **RESOLVED** | bcrypt dummy p/ usuário inexistente |
| BUG-02 | P0-harness | testes | **RESOLVED** | mock `finish_reason` corrigido no conftest |
| UI-01 | P3 | frontend | OPEN (doc) | Tailwind via CDN (warning de prod) — ADR-007 |
| UI-02 | P3 | frontend | OPEN (doc) | `favicon.ico` 404 |
| UI-03 | P3 | IA/menu | OPEN (doc) | menu da IA usa emojis ≠ do canônico |

## 3. Cobertura

**Testado:**
- **Estático (Lead):** XSS (todos os renders), SQLi, HMAC, vazamento de secret, mass-assignment,
  login/rate-limit, race "assumir". Veredito: sólido.
- **Harness pytest (43 testes):** login/auth (A-01/A-02/A-04), assumir+409 (H-03/C-01), devolver
  alheio (H-05), dedup (C-04), lock timeout (C-05), handoff por JSON inválido (H-02), HMAC (V-04),
  no-leak (V-06), background exception (R-04), normalização `<br>`/`\n` (BR-003), FAQ canônica.
- **E2E Playwright (live, read-only):** login→dashboard, SSE "Conectado", empty-state, render de
  52 msgs em ordem cronológica c/ separadores de data, info panel, composer desabilitado p/
  conversa de outro operador, regras de negócio visíveis (anti-agendamento, Fred sob pedido).

**Fora de escopo / deferido:**
- Casos que disparam **WhatsApp real** (assumir/enviar/devolver/mídia, handoff inbound H-01, SSE
  `nova_mensagem` ponta-a-ponta, read receipts ✓✓) — **não executados para não afetar clientes
  reais**; aguardam telefone de teste controlado + ngrok. Cobertos indiretamente pelo harness (com
  Meta mockada) e pela análise estática.
- Performance com 1000+ msgs (PF-03), WCAG/acessibilidade detalhada (U-01..U-04), reconexão SSE
  sob queda real (S-02).

## 4. Riscos residuais

1. **SEC-01 (P1):** sem `META_APP_SECRET` em produção, o `/webhook` aceita qualquer POST. Hoje só
   há warning no boot. **Recomendação: gate rígido** (abortar boot em prod sem o secret).
2. **SEC-04 (P2):** qualquer operador lê qualquer conversa (sem RBAC por conversa). Aceitável p/
   inbox compartilhado de 1–2 pessoas (ADR-011); reavaliar se a equipe crescer ou houver
   requisito de privacidade.
3. **Cobertura live incompleta:** o fluxo WhatsApp ponta-a-ponta não foi exercido com tráfego real.
4. **TZ/timezone (P-02):** render consistente, mas a conversão UTC↔BRT não foi auditada a fundo.
5. **Dead dep:** `google-generativeai` em `requirements.txt` (não usado).

## 5. Próximos passos

- **Decidir SEC-01 e SEC-04** (perguntas abertas ao usuário/PO).
- **Reteste live** com telefone de teste: H-01, S-01..S-06, C-02, read receipts.
- **Manter o harness:** rodar `pytest -q` no CI/pre-commit. Expandir p/ cobrir bulk, transferência,
  status FSM, snooze/auto-unsnooze.
- **Monitoramento:** alertar se `erro_ia_debug.txt` crescer; logar latência IA e taxa de handoff.
- **Limpeza:** remover `google-generativeai`; adicionar favicon; avaliar Tailwind build vs CDN p/ prod.

## 6. Como rodar a suíte

```bash
.venv/Scripts/python.exe -m pip install -r requirements-dev.txt
.venv/Scripts/python.exe -m pytest -q
```
