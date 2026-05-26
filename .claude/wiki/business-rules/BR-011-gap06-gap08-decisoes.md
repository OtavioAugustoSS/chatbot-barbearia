---
name: BR-011-gap06-gap08-decisoes
description: Decisao do PO sobre GAP-06 (reativacao silenciosa do bot) e GAP-08 (mensagem pos-reativacao automatica) — pendencias abertas desde Sprint 0.2.0.
metadata:
  type: business-rule
---

# BR-011 — Decisoes sobre GAP-06 e GAP-08

Data: 2026-05-22
Stakeholders: product-owner-agent (decisao autonoma — pendencias abertas em hot.md desde Sprint 0.2.0)

## Contexto

Dois gaps de comportamento estavam documentados como "aguarda PO" em `hot.md` desde a conclusao da Sprint 0.2.0:

- **GAP-06**: auto-atribuicao quando multiplos atendentes online e nenhum assume — o que acontece?
- **GAP-08**: mensagem enviada ao cliente apos reativacao automatica do bot (apos `BOT_REATIVAR_APOS_HORAS`)

Este BR documenta as decisoes de produto para ambos.

---

## GAP-06 — Auto-atribuicao sem atendente disponivel

### Situacao

Em modo hibrido, quando `chamar_recepcao` e acionado, o sistema seta `aguardando_humano=True`. Qualquer atendente logado pode assumir via `POST /admin/assumir/{telefone}`. O sistema e "first come, first served" — o primeiro atendente que clicar assume.

O gap e: se nenhum atendente assumir, o cliente fica esperando indefinidamente. Nao ha timeout ou auto-redistribuicao.

### Decisao do PO

**Nao implementar auto-atribuicao automatica neste momento.** Justificativa:

1. A Barbearia Bolshoi e um estabelecimento pequeno — o numero de atendentes e limitado (tipicamente 1-2)
2. Auto-atribuicao forcada cria mais problemas do que resolve (atendente ocupado recebe conversa que nao pode atender)
3. O mecanismo de auto-reativacao ja existe (`BOT_REATIVAR_APOS_HORAS=24`) — se nenhum humano assumir em 24h, o bot volta automaticamente

**O que implementar em vez disso (Sprint 0.3.0+):**
- SSE event `conversa_aguardando` com contador de tempo de espera — atendente ve quantos minutos uma conversa esta aguardando sem atendimento
- Aviso visual no dashboard quando conversa em `aguardando_humano=True` exceder X minutos sem atendente assumir (configuravel, sugestao: 10 minutos)
- Nao e auto-atribuicao — e alerta visual para o atendente tomar acao

### Comportamento atual (mantido)

- Nenhum atendente assume → cliente aguarda ate `BOT_REATIVAR_APOS_HORAS` (default 24h)
- Apos 24h, bot volta automaticamente, sem mensagem de notificacao ao cliente (GAP-08 abaixo)
- Qualquer atendente logado pode assumir a qualquer momento

---

## GAP-08 — Mensagem apos reativacao automatica do bot

### Situacao

Quando `bot_ativo=False` e `BOT_REATIVAR_APOS_HORAS` horas se passaram, o bot e reativado automaticamente na proxima mensagem do cliente. O cliente nao e notificado — a reativacao e silenciosa.

Ha duas sub-situacoes:
1. **Reativacao apos handoff humano nao atendido**: cliente pediu recepcao, nenhum atendente assumiu, bot voltou apos 24h
2. **Reativacao apos atendimento humano via endpoint `devolver`**: atendente devolve para o bot — ja tem mensagem de despedida enviada antes da reativacao (BR-004)

### Decisao do PO

**Reativacao silenciosa: MANTER como comportamento padrao.** Justificativa:

- Mandar mensagem proativa apos 24h de silencio pode parecer intrusive ou descontextualizado
- O cliente ja recebeu a mensagem de transbordo quando pediu a recepcao ("estou te transferindo...")
- A proxima mensagem que ele enviar sera processada normalmente pelo bot, que responde no fluxo natural

**Excecao — reativacao apos handoff nao atendido:** Esta e a situacao mais delicada. O cliente pediu falar com humano, nenhum atendeu, e 24h depois o bot volta. Neste caso:

Comportamento decidido: na **primeira mensagem recebida apos a reativacao automatica** (quando `bot_ativo` era `False` por handoff nao atendido, nao por `devolver`), o bot deve incluir uma frase de contexto antes de responder normalmente:

> "Lamentamos nao ter conseguido conectar voce com nossa recepcao anteriormente. Estou aqui para te ajudar! [continua com resposta normal]"

Esta frase so aparece UMA VEZ — na primeira interacao apos a reativacao por timeout.

**Implementacao necessaria (Sprint 0.3.0):**
- Adicionar campo `reativado_por_timeout` (Boolean, default False) em `Usuario` ou verificar logica na condicao de reativacao em `webhook.py`
- Quando reativado por timeout (nao por `devolver`): prefixar a resposta com a frase de contexto e limpar o flag
- Quando reativado por `devolver`: sem prefixo (atendente ja enviou despedida)

### Impacto em codigo

Necessita:
1. Migration: adicionar logica de distincao entre reativacao por timeout vs por `devolver`
2. `api/webhook.py`: detectar a condicao e ajustar a resposta
3. Nova US formal para implementacao

---

## User Story derivada (a ser criada)

A decisao sobre GAP-08 (mensagem apos reativacao por timeout) gera nova user story:

**US-GAP-02**: Como cliente que pediu atendimento humano e nao foi atendido, quero receber uma mensagem de contexto na primeira interacao apos o bot voltar, para entender o que aconteceu.

Esta US sera criada como arquivo separado em `docs/user-stories/US-GAP-02-reativacao-timeout.md`.

## Excecoes

- `!reiniciar` enviado via WhatsApp por ADMIN_PHONES: reativa sem mensagem de contexto — e um comando de staff, nao fluxo de cliente
- `POST /admin/devolver`: ja tem despedida antes de reativar (BR-004) — sem mudanca

## Notas de produto

- A decisao de nao implementar auto-atribuicao deve ser revisada se a barbearia escalar para 3+ atendentes simultaneos
- O alerta visual de "conversa aguardando X minutos" e item prioritario para Sprint 0.3.0 — melhora a UX dos atendentes sem complexidade de backend
