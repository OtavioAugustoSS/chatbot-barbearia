# BR-005: Modos de Operacao — bot_only vs hibrido

Data: 2026-05-21
Stakeholders: product-owner-agent (FASE 3 — formalização de regra hardcoded preexistente)

## Contexto

O sistema suporta dois modos de operação configurados via variável de ambiente `MODO_OPERACAO`. O modo determina quais funcionalidades estão disponíveis, como o bot se comporta diante de certas situações e quais rotas HTTP existem. O modo é imutável em runtime — não pode ser alternado sem reinicialização do servidor.

## Regra

### Modo bot_only (padrão)

`MODO_OPERACAO=bot_only` (valor padrão quando a variável não está definida).

Comportamento:
- Dashboard de admin (`/admin/*`) não existe — rotas não são registradas
- Diretório `static/` não é montado
- `JWT_SECRET` não é necessário
- Handoff humano (`chamar_recepcao`) é interceptado: bot substitui a mensagem por orientação de usar o AppBarber. `bot_ativo` permanece `True`.
- Auto-reativação pode ocorrer (via `BOT_REATIVAR_APOS_HORAS`) mas não há interface humana para assumir
- Regra 15(f) do system prompt ativa: "NÃO ofereça recepção. Pare na orientação do app."
- `RESPOSTA_AGENDAMENTO` (sem variante híbrida) é usada nas canônicas

### Modo hibrido

`MODO_OPERACAO=hibrido`. Requer `JWT_SECRET`.

Comportamento adicional em relação ao bot_only:
- Dashboard `/admin/*` disponível com autenticação JWT (HS256, TTL configurável via `JWT_TTL_MIN`, padrão 15 min)
- SSE stream em `GET /admin/eventos/stream` ativo (heartbeat 25s, fila máx 100 eventos)
- Handoff real: `chamar_recepcao` seta `bot_ativo=False`, `aguardando_humano=True`
- Atendente pode assumir (`POST /admin/assumir/{telefone}`), enviar (`POST /admin/enviar/{telefone}`), devolver (`POST /admin/devolver/{telefone}`)
- Regra 15(e) do system prompt ativa: ao responder sobre disponibilidade de slots, o bot oferece transferência para a recepção
- `RESPOSTA_AGENDAMENTO_HIBRIDO` é usada nas canônicas de agendamento (inclui menção a atendentes humanos)
- Rate limit de login: 5 tentativas por IP por 60 segundos
- Assumir conversa é condicional: apenas se `atendente_id IS NULL` (sem conflito entre atendentes)

### Diferencias criticas de comportamento do prompt por modo

| Situacao | bot_only | hibrido |
|---|---|---|
| Pergunta de slot/disponibilidade | Orienta AppBarber, sem oferta de recepção | Orienta AppBarber + oferece "posso te conectar com nossa recepção" |
| Handoff `chamar_recepcao` | Substitui por orientação AppBarber | Aciona handoff real, seta `bot_ativo=False` |
| Canônica de agendamento | `RESPOSTA_AGENDAMENTO` | `RESPOSTA_AGENDAMENTO_HIBRIDO` |
| Dashboard admin | Inexistente | Disponível em `/admin/` |
| SSE | Inexistente | Ativo em `/admin/eventos/stream` |

## Implementacao em codigo

- **`main.py`**: condicional de importação do router `/admin` e montagem de `static/` baseado em `MODO_OPERACAO`.
- **`core/prompts.py`**: regras 15(e) e 15(f) com comportamento explicitamente diferenciado por modo.
- **`core/respostas_canonicas.py`**: `RESPOSTA_AGENDAMENTO` e `RESPOSTA_AGENDAMENTO_HIBRIDO` separadas; a escolha entre elas ocorre em `api/webhook.py`.
- **`api/admin.py`**: toda lógica de dashboard, JWT, SSE, assumir/devolver — só carregada em modo hibrido.

## Excecoes

- `!reiniciar` funciona em ambos os modos (enviado via WhatsApp por `ADMIN_PHONES`).
- Deduplicação, rate limit e lock por telefone operam em ambos os modos.

## Notas de produto

- A variável `GEMINI_API_KEY` existe no `.env` mas não é usada — o sistema usa exclusivamente NVIDIA NIM (Llama 3.1 70B). Esta distinção não tem impacto no modo de operação mas é relevante para auditoria de segredos.
- Futuras funcionalidades (RBAC, Analytics, Automation Rules) serão exclusivas do modo hibrido — documentar em ADR antes de implementar.
