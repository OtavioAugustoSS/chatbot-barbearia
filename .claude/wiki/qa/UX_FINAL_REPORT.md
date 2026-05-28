---
type: qa
title: "UX_FINAL_REPORT — Sprint de Usabilidade"
updated: 2026-05-28
tags: [qa, ux, usabilidade, final-report]
related: ["[[UX_FINDINGS]]", "[[UX_SETTINGS_CHECK]]", "[[FEATURE_BACKLOG]]"]
---

# UX FINAL REPORT — Sprint de Usabilidade (Dashboard do Atendente)

Branch: `ui/usabilidade` (a partir de `qa/full-sweep`). Time `barbearia-bolshoi-team`:
frontend-agent (fixes), qa-agent (settings), product-owner-agent (backlog), Lead (Playwright + relatórios).

## 1. Sumário executivo
Os **6 problemas de usabilidade** reportados foram corrigidos e validados (5 ao vivo via Playwright,
P4 por code review — exige msg inbound real p/ E2E). O dashboard ficou mais usável: footer de status
sempre visível, respostas rápidas responsivas, ticks com 3 estados distintos (cinza→azul de leitura),
auto-scroll corrigido, busca com origem rotulada (🤖/👤/👩‍💼), e settings verificada (14/14 endpoints)
com 3 gaps corrigidos. **Sem regressão** (pytest 47/47). Entregue também um **backlog de 14 features**
priorizado (apenas proposto, conforme decisão).

## 2. Tabela de resultados
| ID | Problema | Sev | Status | Agente |
|---|---|---|---|---|
| P1 | Sidebar status cortado | P2 | RESOLVED | frontend |
| P2 | Canned pequeno/mal posto | P2 | RESOLVED | frontend |
| P3 | Ticks sobrepostos/leitura | P1 | RESOLVED | frontend |
| P4 | Auto-scroll msg nova | P1 | RESOLVED (code) | frontend |
| P5 | Busca mistura msgs/bot | P2 | RESOLVED | frontend (+PO) |
| P6 | Verificar settings | P2 | VERIFICADO + gaps fix | qa + frontend |
| GAP-A | Canned mascara erro | P1 | RESOLVED | frontend |
| GAP-B | 409 nunca exibido | P1 | RESOLVED | frontend |
| GAP-C | Hex sem validação | P2 | RESOLVED | frontend |

Detalhes + evidência: `UX_FINDINGS.md`. Settings: `UX_SETTINGS_CHECK.md`. Backlog: `FEATURE_BACKLOG.md`.

## 3. Cobertura
- **Validado ao vivo (Playwright):** P1 (CSS computed), P2 (max-height/clamp), P3 (dimensões+cores
  dos ticks), P5 (rótulos de origem na busca). Console sem erros (só warning Tailwind CDN).
- **Verificado por API (qa):** P6 — 14 endpoints das 4 abas (atendentes/labels/canned/tema).
- **Code review (sólido, sem E2E live):** P4 (rAF pós-append) — precisa msg inbound real p/ confirmar
  ponta-a-ponta.
- **Regressão:** pytest 47/47.

## 4. Riscos residuais
1. **P4 sem E2E live** — validar com mensagem WhatsApp real chegando (reteste `[USER-IN-LOOP]`).
2. **Cache agressivo de estáticos** — o browser serviu JS/HTML velhos até forçar revalidação.
   Em produção, operadores podem ficar em versão antiga após deploy. **Recomendação:** versionar
   assets (`app.js?v=<hash>`) ou enviar headers `Cache-Control` adequados no mount de estáticos.
3. **P3** mantém leve adjacência entre os dois checks do double-tick (proposital, padrão WhatsApp);
   sem sobreposição de stroke graças ao container fixo + viewBox novo.

## 5. Backlog de features (proposto — não implementado)
`.claude/wiki/frontend/FEATURE_BACKLOG.md` — 14 features priorizadas. Top 3 do PO:
1. **Badges SLA / alerta de fila** (BR-011, usa `transbordo_em`).
2. **Contador de não-lidas por aba** (expor `mensagens_nao_lidas` em `/admin/conversas`).
3. **Reabertura rápida de conversa resolvida**.
Rejeitado por BR-001: qualquer feature com slots/agendamento no dashboard.

## 6. Próximos passos
- Reteste live de P4 (msg inbound).
- Avaliar versionamento de assets (risco de cache).
- Revisar/mergear `ui/usabilidade` (empilha sobre `qa/full-sweep`, ambos sem push).
- Priorizar o backlog com o PO p/ próxima sprint.

## 7. Como validar
- Servidor :8000 (hibrido); login `qa_sweep`. Forçar reload sem cache p/ ver os fixes.
- `.venv/Scripts/python.exe -m pytest -q` → 47 passed.
