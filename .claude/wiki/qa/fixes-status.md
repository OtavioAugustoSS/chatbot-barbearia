# Fixes Status — Mega Auditoria 2026-05-26

## P0 — CRÍTICOS
- [x] P0-1: font-family Inter inline no body (index.html:1452) — FEITO — frontend-agent
- [x] P0-2: META_APP_SECRET ausente sem alerta de produção (webhook.py:36-45) — FEITO — backend-agent
- [x] P0-3: state.presence não declarado no objeto state inicial (app.js:10-27) — FEITO — frontend-agent
- [x] P0-4: stroke-dasharray:30 em todos tick SVGs incluindo clock (index.html:1333) — FEITO — frontend-agent
- [x] P0-5: .entregue-status.delivered usa var(--accent) azul igual tick-read (index.html:1343) — FEITO — frontend-agent

## P1 — BUGS ATIVOS
- [x] P1-1: #messages-area background #0b141a hardcoded quebra tema claro (index.html:784) — FEITO — frontend-agent
- [x] P1-2: isUnread só ativa em aguardando_humano&&!atendente_id; mensagens em conv assumida perdem badge (app.js:552) — FEITO — frontend-agent
- [x] P1-3: Aguardando Xmin usa ultima_mensagem_em em vez de transbordo_em (app.js:546) — FEITO — frontend-agent
- [x] P1-4: Thread não recarrega após envio de mídia (app.js:1400-1420) — FEITO — frontend-agent
- [x] P1-5: Avatar gradient border: divs de avatar em renderConvList sem classe .avatar (app.js:560+) — FEITO — frontend-agent
- [x] P1-6: Empty state invisível em tablets <=1023px (index.html:1641+, app.js:2456) — FEITO — frontend-agent
- [x] P1-7: assumir() envia greeting duplicado se mesmo atendente clica 2x (admin.py:454) — FEITO — backend-agent
- [x] P1-8: Horários hardcoded em SYSTEM_PROMPT_BARBEARIA divergem do DB (core/prompts.py) — FEITO (refix: exemplos com [HORA_ABERTURA]/[HORA_FECHAMENTO]) — lead
- [x] P1-9: data_ultima_interacao não atualizado em bulk/assumir/devolver via synchronize_session=False (admin.py) — FEITO (refix: user.data_ultima_interacao=agora antes db.flush()) — lead
- [x] P1-10: state.presence inicializado tarde (linha 1917); mover para objeto state inicial — FEITO — frontend-agent

## P2 — DESIGN SYSTEM / TOKENS
- [x] DS-01: --border-subtle nunca definido; .conv-card usa fallback #1e2130 (index.html:358) — FEITO — frontend-agent
- [x] DS-02: --ok nunca definido; #conn-status-dot.connected usa fallback (index.html:403) — FEITO — frontend-agent
- [x] DS-03: .bolha-outgoing-humano .bolha-label usa #d6e8fa hardcoded (index.html:258) — FEITO — frontend-agent
- [x] DS-04: showToast() cores background hardcoded hex em vez de tokens (app.js:144) — FEITO — frontend-agent
- [x] DS-05: #my-avatar gradient usa #1a5a8f não-token (index.html:1496) — FEITO — frontend-agent
- [x] DS-06: .presence-dot fallbacks divergem dos tokens (index.html:398) — FEITO — frontend-agent
- [x] DS-07: margin-top: calc(2px - 6px) = -4px sobrepõe bolhas agrupadas (index.html:1082) — FEITO — frontend-agent
- [x] DS-08: prefers-reduced-motion usa 0.01ms; trocar por animation:none (index.html:1140) — FEITO — frontend-agent
- [x] DS-09: Empty state SVG floatIdle fica preso com reduced-motion (index.html:1285) — FEITO — frontend-agent
- [x] DS-10: #conn-status-dot sem estado visual .failed distinto (index.html:403+) — FEITO — frontend-agent

## P2 — BACKEND
- [x] BE-01: _post_com_retry() não retry em 429 Meta rate limit (whatsapp.py:22) — FEITO — backend-agent
- [x] BE-02: response.json() sem try/except; 502 HTML = crash (whatsapp.py:41) — FEITO — backend-agent
- [x] BE-03: bulk_acao() sem rollback em falha parcial (admin.py:819) — FEITO — backend-agent
- [x] BE-04: Mídia não registra message_id em MensagemProcessada (webhook.py:310) — FEITO — backend-agent
- [x] BE-05: criar_canned() unicidade global usa == None em vez de .is_(None) (admin.py:1524) — FEITO — backend-agent
- [x] BE-06: criar_nota() commit antes de processar mentions; orphan em falha (admin.py:1820) — FEITO — backend-agent
