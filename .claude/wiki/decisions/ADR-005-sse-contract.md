# ADR-005: Contrato SSE — Formato de Eventos e Heartbeat
Status: aceito
Data: 2026-05-21
Decisor: architect-agent
Stakeholders consultados: backend-agent, frontend-agent (código existente como fonte de verdade)

## Contexto

O notificador SSE (`services/notificador.py`) e o endpoint `GET /admin/eventos/stream` são a espinha dorsal do dashboard em tempo real. O contrato de eventos (nomes de campos, tipos, valores válidos) nunca foi documentado — cada `notificador.publicar({...})` foi adicionado organicamente. Esta ADR cataloga todos os tipos de evento e estabelece o contrato formal.

## Decisão

### Protocolo de transporte

- Formato SSE padrão W3C: `data: <json>\n\n`
- Heartbeat: `\n: keepalive\n\n` (comentário SSE) a cada **25 segundos**
- Reconexão: responsabilidade do frontend (`EventSource` faz retry automático). Em reconexão, frontend chama `GET /admin/conversas` para reconstruir estado completo (eventos perdidos não são reentregues).
- Fila por assinante: `queue.Queue(maxsize=100)` — ao encher, descarta o evento **mais antigo** (drop-oldest). Preferível a bloquear o thread publicador.

### Autenticação do stream

`GET /admin/eventos/stream` usa `Depends(atendente_atual)` — JWT Bearer obrigatório no header.

### Catálogo de tipos de evento

Todos os eventos têm campo `tipo` (string). O JSON é entregue sem envelope adicional.

#### `nova_mensagem`
Publicado quando qualquer mensagem é trocada (bot, humano ou cliente).
```json
{
  "tipo": "nova_mensagem",
  "telefone": "<string>",
  "nome": "<string | null>",
  "texto": "<string>",
  "origem": "bot | humano | cliente",
  "atendente_id": "<int | null>",
  "entregue": "<bool | null>"
}
```
- `entregue`: `true/false` para saídas (bot/humano), `null` para mensagens do cliente recebidas

#### `novo_transbordo`
Publicado quando bot seta `aguardando_humano=True`.
```json
{
  "tipo": "novo_transbordo",
  "telefone": "<string>",
  "nome": "<string | null>",
  "motivo": "<string>"
}
```

#### `atendente_assumiu`
Publicado quando atendente chama `POST /admin/assumir/{telefone}`.
```json
{
  "tipo": "atendente_assumiu",
  "telefone": "<string>",
  "atendente_id": "<int>",
  "atendente_nome": "<string>"
}
```

#### `bot_devolveu`
Publicado quando atendente chama `POST /admin/devolver/{telefone}`.
```json
{
  "tipo": "bot_devolveu",
  "telefone": "<string>"
}
```

#### `status_alterado`
Publicado em mudanças de `status_conversa` (open/pending/resolved/snoozed) e em reaberturas automáticas.
```json
{
  "tipo": "status_alterado",
  "telefone": "<string>",
  "status": "open | pending | resolved | snoozed",
  "snoozed_until": "<ISO8601 | null>",
  "por_atendente_id": "<int | null>"
}
```
- `por_atendente_id`: `null` indica reabertura automática pelo sistema (cliente mandou mensagem)

#### `conversa_atribuida`
Publicado em transferência de conversa entre atendentes.
```json
{
  "tipo": "conversa_atribuida",
  "telefone": "<string>",
  "de_atendente_id": "<int>",
  "para_atendente_id": "<int>",
  "para_atendente_nome": "<string>"
}
```

#### `bulk_aplicado`
Publicado após operação bulk.
```json
{
  "tipo": "bulk_aplicado",
  "acao": "resolver | atribuir | label_add | label_remove | snooze",
  "afetadas": "<int>",
  "por_atendente_id": "<int>"
}
```

#### `presence_changed`
Publicado em mudança de status de presença de atendente.
```json
{
  "tipo": "presence_changed",
  "atendente_id": "<int>",
  "status": "online | away | offline"
}
```

#### `nova_mention`
Publicado quando atendente é @mencionado em nota interna.
```json
{
  "tipo": "nova_mention",
  "atendente_id": "<int>",
  "telefone": "<string>",
  "mencionado_por": "<int>",
  "mencionado_por_nome": "<string>",
  "nota_id": "<int>",
  "preview": "<string até 120 chars>"
}
```

### Campos de data/hora em eventos SSE

Todos os timestamps em eventos SSE são strings ISO 8601 com sufixo `Z` (UTC). O frontend não deve inferir timezone local.

### Regra de adição de novos tipos de evento

Qualquer novo tipo de evento deve ser adicionado a este ADR antes de ser implementado. O campo `tipo` é a chave de discriminação — nunca reutilizar um `tipo` existente com semântica diferente.

## Consequências

- Positivo: frontend tem contrato completo para tratar cada tipo sem surpresas
- Positivo: heartbeat de 25s é compatível com timeout padrão de proxies (60s)
- Negativo: sem `id` de evento SSE — reconexão perde todos os eventos intermediários (aceito: dashboard re-faz GET ao reconectar)
- Negativo: fila de 100 eventos por assinante é arbitrária — cliente SSE travado por >1min com alto volume de mensagens pode perder eventos
- Risco: `presence_changed` com status `"offline"` é gerado por `_limpar_presence_stale()` chamado em `GET /admin/presence` — não é publicado proativamente em intervalo fixo, depende de request ao endpoint de presence

## Alternativas consideradas

- WebSockets: mais robusto para bidirecionalidade, mas SSE é suficiente (dashboard só precisa receber do servidor); evita a complexidade de gerenciar conexão WS em vanilla JS
- Redis pub/sub para filas: necessário apenas em deploy multi-processo; atualmente Uvicorn roda em worker único, filas in-memory são suficientes
- Usar campo `id:` do SSE para sequence: permitiria `Last-Event-ID` no reconnect, mas requereria persistência de eventos — rejeitado por complexidade

---

## Addendum 2026-05-22 (architect-agent / revisão de tech debt)

### Violação detectada: `presence_changed.status = "reativado"`

`api/admin.py/ativar_atendente()` publica `presence_changed` com `status: "reativado"` — valor
não previsto no catálogo acima. O contrato define apenas `"online | away | offline"`.

**Decisão**: corrigir para `status: "online"` no endpoint `ativar_atendente`. A semântica é
equivalente — atendente reativado está disponível, portanto `"online"` é o estado correto.
O campo adicional `atendente_nome` pode permanecer no payload (campos extras são tolerados
pelo frontend via duck typing, pois o handler de `presence_changed` usa apenas `atendente_id`
e `status`).

**Impacto no frontend**: nenhum — o handler em `sse.js` já ignora campos extras e o valor
`"reativado"` não matchava nenhum case existente, portanto o evento era efetivamente ignorado.
Registrado como TD-016.

### Addendum ao catálogo: `bulk_aplicado` — atomicidade parcial

O campo `afetadas` em `bulk_aplicado` representa **apenas os itens bem-sucedidos**. Falhas
parciais existem mas são comunicadas exclusivamente via response body (não via SSE). O
dashboard não precisa tratar falhas via SSE — o reload de estado após o evento é suficiente.
Documentado formalmente em ADR-009.
