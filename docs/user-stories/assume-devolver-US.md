# User Stories — Assume / Devolver (Conversa Humano-Bot)

**Domínio:** Dashboard híbrido (MODO_OPERACAO=hibrido)
**Data:** 2026-05-25
**Autor:** product-owner-agent
**Branch:** redesign/admin-interface

---

## Legenda de Estado

- **OK** — Implementado e correto com base na leitura do código.
- **Gap** — Comportamento desejado não está totalmente implementado.
- **Bug** — Comportamento implementado é incorreto ou inesperado.

---

## US-AD-001 — Atendente assume conversa com aguardando_humano=true

**Role:** Atendente autenticado no dashboard
**Acao:** Clica no botão "Assumir" em conversa marcada como aguardando atendimento humano
**Resultado esperado:** O sistema registra o atendente como responsável, desativa o bot, envia saudação automática ao cliente via WhatsApp, e atualiza o dashboard em tempo real.

### Criterios de aceite

- [ ] `POST /admin/assumir/{telefone}` retorna 200 com `{status: "ok", atendente_id, entregue}`
- [ ] Campo `atendente_id` do usuario fica igual ao id do atendente que assumiu
- [ ] Campo `bot_ativo` fica `False`
- [ ] Campo `aguardando_humano` fica `False`
- [ ] Campo `status_conversa` fica `"open"`
- [ ] Mensagem de saudação ("Olá! Sou [Nome]...") é enviada via WhatsApp e registrada em `historico_conversas` com `origem="humano"`
- [ ] SSE `atendente_assumiu` publicado com `telefone`, `atendente_id`, `atendente_nome`
- [ ] SSE `nova_mensagem` publicado com a saudação
- [ ] SSE `status_alterado` publicado com `status="open"`
- [ ] Dashboard do atendente que assumiu exibe botões "Devolver" e "Transferir", compositor habilitado
- [ ] Outros atendentes recebem SSE e veem conversa como "Outro atendente" com compositor desabilitado

**Estado atual:** OK

**Notas tecnicas:** `api/admin.py:assumir()` (linha 439). UPDATE condicional garante atomicidade. `syncComposerState()` em `app.js:1093` lida corretamente com `meuAtendimento=true`.

---

## US-AD-002 — Atendente envia 1a mensagem em conversa com bot_ativo=true (auto-assume ao enviar)

**Role:** Atendente autenticado no dashboard
**Acao:** Com a conversa aberta, digita uma mensagem e clica Enviar sem ter clicado em "Assumir" antes. O bot esta ativo nessa conversa.
**Resultado esperado:** O sistema assume automaticamente a conversa em nome do atendente antes de enviar a mensagem, sem exigir acao adicional do operador.

### Criterios de aceite

- [ ] `enviarMensagem()` detecta que `atendente_id !== eu.id` e chama `api.assumir()` antes de `api.enviar()`
- [ ] Se `assumir()` retornar 409, mensagem nao e enviada e toast de erro e exibido
- [ ] Apos assumir com sucesso, `state.usuarioAtual` e atualizado via `api.getConversa()`
- [ ] `syncComposerState()` e chamado para refletir novo estado (compositor habilitado, botoes corretos)
- [ ] A mensagem digitada e enviada apos o assume bem-sucedido
- [ ] Banner "Bot ativo — enviar vai interrompe-lo" e visivel antes do envio
- [ ] Apos envio, banner e removido e botoes "Devolver" / "Transferir" aparecem

**Estado atual:** OK

**Notas tecnicas:** `app.js:enviarMensagem()` linha 1207. Bloco `naoAssumido` (linha 1220) chama `api.assumir()`. Banner e controlado por `syncComposerState()` estado `u.bot_ativo=true` (linha 1139-1155).

---

## US-AD-003 — Atendente envia 1a mensagem em conversa sem atendente e bot_ativo=false

**Role:** Atendente autenticado no dashboard
**Acao:** Abre conversa onde bot esta inativo (handoff anterior) mas nenhum atendente a assumiu ainda (`atendente_id=null`). Envia mensagem.
**Resultado esperado:** Sistema assume automaticamente antes de enviar, igual ao US-AD-002, mas sem precisar parar o bot (ja esta inativo).

### Criterios de aceite

- [ ] `enviarMensagem()` detecta `naoAssumido=true` (atendente_id nulo) e chama `api.assumir()`
- [ ] `assumir()` aceita conversa com `bot_ativo=False` — UPDATE condicional filtra por `atendente_id IS NULL`, nao por `bot_ativo`
- [ ] Saudacao automatica e enviada ao cliente via WhatsApp
- [ ] `bot_ativo` permanece `False` (nao reativa)
- [ ] Compositor fica habilitado apos assume
- [ ] `syncComposerState()` exibe estado "Bot inativo" antes do envio, com `btnAssumir` visivel

**Estado atual:** OK

**Notas tecnicas:** `api/admin.py:assumir()` linha 454-468. Filtro `.filter(Usuario.atendente_id.is_(None))` independe de `bot_ativo`. `syncComposerState()` linha 1148-1154: estado "Bot inativo" sem atendente.

---

## US-AD-004 — Atendente envia midia como 1a mensagem em conversa sem atendente (auto-assume via enviar-midia)

**Role:** Atendente autenticado no dashboard
**Acao:** Anexa um arquivo (imagem/PDF/audio) e envia em conversa sem atendente, com ou sem bot ativo.
**Resultado esperado:** O endpoint `/admin/enviar-midia/{telefone}` assume automaticamente a conversa antes de fazer upload e enviar a midia.

### Criterios de aceite

- [ ] `POST /admin/enviar-midia/{telefone}` detecta `usuario.atendente_id is None` e faz auto-assume
- [ ] Saudacao automatica e enviada antes da midia
- [ ] Campo `auto_assumiu=true` no payload de resposta
- [ ] SSE `atendente_assumiu`, `status_alterado` e `nova_mensagem` (saudacao) sao publicados antes do SSE da midia
- [ ] Arquivo e validado (max 16MB, tipos suportados: image/jpeg, image/png, image/webp, image/gif, application/pdf, audio/ogg, audio/mpeg, audio/aac, video/mp4)
- [ ] Se arquivo invalido, retorna 400 antes de tentar assumir
- [ ] Frontend: `enviarMensagem()` chama `api.enviarMidia()` com FormData; a logica de auto-assume e server-side (nao precisa chamar `api.assumir()` separado para midia)

**Estado atual:** Gap

**Notas tecnicas:** `api/admin.py:enviar_midia()` linha 979 faz auto-assume server-side (OK). Porem `enviarMensagem()` no frontend (`app.js` linha 1238-1258) NAO chama `api.assumir()` antes de `api.enviarMidia()` — a validacao de `naoAssumido` acontece antes do bloco `if (state.attachedFile)`, portanto o frontend chama `assumir()` + `getConversa()` antes de chamar `enviarMidia()`. Isso resulta em DUPLA saudacao: uma do frontend (via `assumir()`) e outra do backend (via auto-assume em `enviar_midia()`). GAP: o frontend deve pular o `assumir()` manual quando ha anexo, deixando o auto-assume do servidor agir.

---

## US-AD-005 — Dois atendentes tentam assumir a mesma conversa simultaneamente (race condition)

**Role:** Dois atendentes autenticados
**Acao:** Ambos clicam "Assumir" quase ao mesmo tempo na mesma conversa aguardando humano.
**Resultado esperado:** Apenas um atendente assume. O outro recebe erro 409 claro.

### Criterios de aceite

- [ ] UPDATE condicional com `WHERE atendente_id IS NULL` garante que apenas um atendente vence
- [ ] O perdedor recebe HTTP 409 com mensagem "Outro atendente assumiu essa conversa antes de voce."
- [ ] O perdedor ve toast de erro "Outro atendente assumiu primeiro"
- [ ] Apenas uma saudacao e enviada ao cliente (sem duplicidade de mensagens)
- [ ] SSE `atendente_assumiu` e publicado apenas uma vez, com os dados do vencedor
- [ ] O vencedor assume e o UI do perdedor atualiza via SSE (conversa passa para "Outro atendente")
- [ ] A conversa nao fica em estado inconsistente mesmo se duas transactions DB chegarem simultaneamente

**Estado atual:** OK

**Notas tecnicas:** `api/admin.py:assumir()` linha 454-468. Dupla protecao: pre-check de 409 (linha 451) + UPDATE condicional (linha 455). Segundo check pos-UPDATE (linha 472) cobre race condition. Frontend: toast de 409 em `assumirConversa()` linha 1174.

---

## US-AD-006 — Atendente assume e imediatamente devolve ao bot (cliente recebe saudacao + despedida)

**Role:** Atendente autenticado
**Acao:** Clica "Assumir" e logo em seguida clica "Devolver" sem enviar nenhuma mensagem.
**Resultado esperado:** Cliente recebe saudacao seguida de mensagem de despedida. Bot volta a responder.

### Criterios de aceite

- [ ] Saudacao e enviada no momento do assume
- [ ] Mensagem de despedida ("Atendimento humano encerrado. O assistente virtual esta de volta...") e enviada no devolver
- [ ] Ambas as mensagens aparecem no historico com `origem="humano"`
- [ ] Apos devolver: `bot_ativo=True`, `atendente_id=null`, `aguardando_humano=False`
- [ ] Dashboard do atendente exibe modal de confirmacao antes de devolver ("Devolver ao bot?")
- [ ] Confirmacao positiva executa `api.devolver()` e atualiza compositor para estado "Bot ativo"
- [ ] Na thread, separador de evento "Bot retomou o atendimento" aparece entre as mensagens

**Estado atual:** OK

**Notas tecnicas:** `devolverAoBot()` em `app.js:1178` usa `abrirModalConfirmar()`. `api/admin.py:devolver()` linha 1053. UPDATE condicional (linha 1087) atualiza campos em transacao unica. Separador de evento em `renderMensagens()` linha 900.

---

## US-AD-007 — Atendente devolve conversa ao bot via botao Devolver (fluxo normal)

**Role:** Atendente autenticado que e dono atual da conversa
**Acao:** Clica no botao "Devolver" no header da conversa.
**Resultado esperado:** Bot retoma o atendimento, cliente recebe aviso de encerramento humano, dashboard atualiza.

### Criterios de aceite

- [ ] Modal de confirmacao aparece antes de executar a acao
- [ ] `POST /admin/devolver/{telefone}` retorna 200 com `{status: "ok", silent: false}`
- [ ] Mensagem de despedida enviada ao WhatsApp e registrada no historico
- [ ] SSE `nova_mensagem`, `bot_devolveu` e `status_alterado` (status="open") publicados nessa ordem
- [ ] `bot_ativo=True`, `atendente_id=null`, `aguardando_humano=False`, `snoozed_until=null`
- [ ] Se `status_conversa` era "resolved", e resetado para "open"
- [ ] Dashboard: botoes "Devolver" e "Transferir" somem, compositor volta ao estado adequado
- [ ] Outros atendentes recebem SSE `bot_devolveu` e atualizam a lista

**Estado atual:** OK

**Notas tecnicas:** `api/admin.py:devolver()` linha 1053. Ordem de publicacao SSE: `nova_mensagem` (linha 1148), `bot_devolveu` (linha 1157), `status_alterado` (linha 1161). Handler SSE `bot_devolveu` em `app.js:2223`.

---

## US-AD-008 — Silent devolver (?silent=true): quando usar e se a UI precisa expor esse modo

**Role:** Sistema ou atendente via chamada direta de API
**Acao:** `POST /admin/devolver/{telefone}?silent=true` e chamado.
**Resultado esperado:** Bot reativa sem enviar mensagem ao cliente e sem SSE `nova_mensagem`. Apenas DB atualizado e SSE `bot_devolveu` publicado.

### Criterios de aceite

- [ ] Nenhuma mensagem enviada ao cliente via WhatsApp
- [ ] SSE `nova_mensagem` NAO publicado
- [ ] SSE `bot_devolveu` publicado
- [ ] SSE `status_alterado` publicado com `status="open"`
- [ ] Registro em `historico_conversas` com `intencao="devolucao_silenciosa"` e sem texto
- [ ] `bot_ativo=True`, `atendente_id=null`, demais campos limpos

### Decisao de produto

O modo `?silent=true` NAO deve ser exposto na UI principal do atendente. Casos de uso legitimos: automacoes internas (ex.: bulk resolve + devolver), scripts de manutencao, integracao futura com RBAC supervisor. Expor na UI principal confundiria o atendente sobre o que o cliente recebeu.

**Estado atual:** Gap (backend OK, UI nao expoe — decisao intencional de produto)

**Notas tecnicas:** `api/admin.py:devolver()` linha 1110. Branch `if silent:` registra `devolucao_silenciosa`. UI em `devolverAoBot()` `app.js:1178` nunca passa `silent=true` — correto por ora.

---

## US-AD-009 — Transferir conversa para outro atendente

**Role:** Atendente que e dono atual da conversa
**Acao:** Clica "Transferir", seleciona outro atendente ativo no popover, confirma.
**Resultado esperado:** Conversa e reatribuida, ambos os atendentes sao notificados via SSE, cliente NAO recebe mensagem automatica.

### Criterios de aceite

- [ ] Apenas o dono atual (`atendente_id == me.id`) pode transferir — 403 para outros
- [ ] Atendente destino deve estar ativo — 404 se inativo ou inexistente
- [ ] Nao e possivel transferir para si mesmo — 400
- [ ] `POST /admin/conversa/{telefone}/atribuir` retorna 200 com `{ok, atendente_id, atendente_nome}`
- [ ] Registro interno em `historico_conversas` com `resposta_bot="[Sistema] Conversa transferida de X para Y"` e `intencao="transferencia"`, sem mensagem ao cliente
- [ ] SSE `conversa_atribuida` publicado com `de_atendente_id`, `para_atendente_id`, `para_atendente_nome`
- [ ] Atendente destino recebe toast "Conversa transferida para voce"
- [ ] Atendente origem ve a conversa sumir de sua lista
- [ ] Popover exibe status de presence (online/away/offline) de cada atendente disponivel

**Estado atual:** OK

**Notas tecnicas:** `api/admin.py:atribuir_conversa()` linha 871. `transferirConversa()` em `app.js:1579`. Handler SSE `conversa_atribuida` em `app.js:2183`. Popover com presence em `abrirPopoverTransferir()` linha 1544.

---

## US-AD-010 — Admin desativa conta de atendente mid-conversation (auto-release)

**Role:** Admin (qualquer atendente autenticado por ora — ADR-011: sem RBAC)
**Acao:** Desativa conta de atendente via `PATCH /admin/atendentes/{id}/desativar` enquanto esse atendente esta atendendo conversas ativas.
**Resultado esperado:** Conversas abertas do atendente desativado sao automaticamente liberadas: bot reativa, cliente nao fica em limbo.

### Criterios de aceite

- [ ] `PATCH /admin/atendentes/{id}/desativar` retorna 200
- [ ] Admin nao pode desativar a propria conta — 400
- [ ] Todas as conversas com `atendente_id == id_desativado` e `bot_ativo=False` sao atualizadas: `atendente_id=null`, `bot_ativo=True`, `aguardando_humano=False`
- [ ] Bot retoma respostas automaticas para esses clientes (sem aviso ao cliente — silencioso)
- [ ] O atendente desativado nao consegue mais autenticar (`login` retorna 401)
- [ ] SSE NAO e publicado para as conversas liberadas (bug potencial: cliente pode receber respostas do bot sem aviso de transicao)

**Estado atual:** Gap

**Notas tecnicas:** `api/admin.py:desativar_atendente()` linha 1634. A query de auto-release (linha 1645) reseta campos corretamente. Porem nenhum SSE e publicado para os clientes afetados — outros atendentes no dashboard nao sao notificados das mudancas. Tambem: `status_conversa` permanece como estava (nao e resetado para "open"), o que pode deixar conversas invisiveis no filtro padrao. GAP: publicar SSE `bot_devolveu` para cada telefone afetado e resetar `status_conversa` para "open".

---

## US-AD-011 — Conversa resolved: cliente envia nova mensagem

**Role:** Sistema (recepcao de mensagem do cliente)
**Acao:** Conversa com `status_conversa="resolved"` recebe nova mensagem do cliente via WhatsApp.
**Resultado esperado:** Dashboard exibe a nova mensagem; conversa reaparece na fila; bot pode responder conforme `bot_ativo`.

### Criterios de aceite

- [ ] Nova mensagem do cliente e registrada em `historico_conversas` independente de `status_conversa`
- [ ] Webhook nao bloqueia mensagens de conversas "resolved" — apenas `bot_ativo=False` silencia o bot
- [ ] Se `bot_ativo=True`: bot responde normalmente
- [ ] Se `bot_ativo=False` e `atendente_id=null`: mensagem do cliente fica sem resposta ate atendente assumir ou `BOT_REATIVAR_APOS_HORAS` expirar
- [ ] Dashboard: conversa "resolved" com nova mensagem NAO aparece automaticamente no filtro "open" sem acao do atendente
- [ ] SSE `nova_mensagem` publicado, toast exibido para atendentes logados

**Estado atual:** Gap

**Notas tecnicas:** `api/webhook.py` nao verifica `status_conversa` — processa mensagens independente. O problema e de visibilidade no dashboard: conversa permanece com `status_conversa="resolved"`, invisivel no filtro padrao "open". Atendente precisa mudar o filtro para "resolved" para ver. Seria desejavel um mecanismo que, ao receber nova mensagem em conversa "resolved", resete `status_conversa` para "open" automaticamente (similar ao `_auto_unsnooze`). GAP de produto: definir politica de re-abertura automatica.

---

## US-AD-012 — Conversa snoozed: atendente assume — snoozed_until e limpo?

**Role:** Atendente autenticado
**Acao:** Assume conversa que esta com `status_conversa="snoozed"` (adiada).
**Resultado esperado:** Ao assumir, a conversa sai do estado "snoozed", `snoozed_until` e limpo, e conversa aparece como "open" no dashboard.

### Criterios de aceite

- [ ] `POST /admin/assumir/{telefone}` inclui `status_conversa: "open"` no UPDATE (nao condicional a snoozed)
- [ ] `snoozed_until` e limpo pelo UPDATE de assume (campo nao esta no payload do UPDATE atual)
- [ ] SSE `status_alterado` e publicado com `status="open"`, `snoozed_until=null`
- [ ] Conversa aparece no filtro padrao "open" apos assumir
- [ ] Dashboard: badge "Adiada" some do card da conversa

**Estado atual:** Bug

**Notas tecnicas:** `api/admin.py:assumir()` linha 459-468. O UPDATE define `status_conversa: "open"` (correto), mas NAO inclui `snoozed_until: None` no payload. Isso significa que `snoozed_until` permanece com o valor antigo no DB apos o assume. O SSE `status_alterado` (linha 504) envia `snoozed_until: None` (hardcoded) — correto no SSE, mas incorreto no DB. `_auto_unsnooze()` eventualmente limparia, mas o estado fica inconsistente ate o proximo poll. BUG: adicionar `"snoozed_until": None` ao UPDATE de `assumir()`.

---

## US-AD-013 — Outro atendente esta atendendo: UI desabilita compositor do atendente atual

**Role:** Atendente que visualiza conversa ja assumida por outro
**Acao:** Abre uma conversa cuja `atendente_id` pertence a outro atendente.
**Resultado esperado:** Compositor fica desabilitado, banner informativo exibido, botoes de assumir/devolver ocultados.

### Criterios de aceite

- [ ] `syncComposerState()` detecta `outroAtendente = u.atendente_id && u.atendente_id !== state.eu.id`
- [ ] `msg-input` fica `disabled=true`
- [ ] `send-btn` fica `disabled=true`
- [ ] Banner "Esta conversa esta sendo atendida por outro operador." aparece
- [ ] Botoes "Assumir", "Devolver" e "Transferir" ficam ocultos
- [ ] Status no header exibe "Outro atendente"
- [ ] SSE `atendente_assumiu` recebido pelo segundo atendente atualiza o estado em tempo real se a conversa estiver aberta

**Estado atual:** OK

**Notas tecnicas:** `syncComposerState()` `app.js:1093`. Bloco `outroAtendente` linha 1120-1127. Handler SSE `atendente_assumiu` linha 2154 atualiza `state.usuarioAtual` e chama `syncComposerState()` se `ev.telefone === state.conversaAtual`.

---

## US-AD-014 — Race condition: SSE atrasado, atendente tenta enviar para conversa de outro

**Role:** Atendente A (compositor aparentemente habilitado) e Atendente B (assumiu faz 2s)
**Acao:** Atendente A, com UI desatualizada (SSE ainda nao chegou), tenta enviar mensagem antes de receber o SSE de que B assumiu.
**Resultado esperado:** Backend rejeita o envio de A com 403. A UI de A exibe erro e atualiza o estado.

### Criterios de aceite

- [ ] `POST /admin/enviar/{telefone}` verifica `user.atendente_id == me.id` antes de enviar — 403 se nao for dono
- [ ] Frontend exibe toast "Erro ao enviar mensagem" (generico) quando recebe 403
- [ ] Frontend NAO atualiza estado automaticamente apos 403 do `/enviar` — atendente precisa aguardar SSE
- [ ] SSE `atendente_assumiu` chega eventualmente e desabilita o compositor de A automaticamente
- [ ] Nenhuma mensagem de A chega ao cliente

**Estado atual:** Gap

**Notas tecnicas:** `api/admin.py:enviar()` linha 929 — verifica `user.atendente_id != me.id` e retorna 403 (backend OK). Frontend `enviarMensagem()` linha 1270-1276: captura erro e exibe toast, mas nao forca reload do estado da conversa. Sem o SSE chegando, o compositor permanece habilitado e o atendente pode tentar enviar indefinidamente. GAP: apos 403 em `/enviar`, o frontend deve chamar `api.getConversa()` para forcar sincronizacao de estado, mesmo sem SSE.

---

## US-AD-015 — Atendente fecha aba/browser mid-conversation: bot NAO reativa imediatamente

**Role:** Sistema (comportamento automatico apos desconexao do atendente)
**Acao:** Atendente fecha o browser ou perde conexao enquanto atende conversa.
**Resultado esperado:** A conversa permanece atribuida ao atendente. O bot permanece inativo. Reativacao automatica so ocorre apos `BOT_REATIVAR_APOS_HORAS` (default 24h) decorridas.

### Criterios de aceite

- [ ] Fechar o browser NAO aciona `POST /admin/devolver/{telefone}` — nao ha mecanismo de desconexao automatica
- [ ] `navigator.sendBeacon()` ao fechar aba envia apenas `status: "offline"` para `/admin/presence` — NAO devolve conversa
- [ ] Presence do atendente muda para "offline" apos 90s sem heartbeat (PRESENCE_TIMEOUT_SECS)
- [ ] A conversa permanece com `atendente_id` preenchido e `bot_ativo=False`
- [ ] `BOT_REATIVAR_APOS_HORAS` (24h default) e verificado em `api/webhook.py` na proxima mensagem do cliente
- [ ] Ao expirar o timeout, `bot_ativo` volta a `True`, campo `reativado_por_timeout=True` e setado
- [ ] O dashboard deve exibir aviso visual quando atendente responsavel esta "offline" ha mais de X minutos (GAP de UX — nao implementado)

**Estado atual:** Gap

**Notas tecnicas:** `iniciarPresenceTracking()` `app.js:1888`. `sendBeacon` envia `{status: "offline"}` para `/admin/presence` (nao `/admin/devolver`). Logica de reativacao por timeout em `api/webhook.py` (campo `reativado_por_timeout` em `db/models.py` linha 39). GAP de UX: nao ha indicador no dashboard de que o atendente responsavel esta offline, deixando conversas em limbo invisivel para os outros operadores.

---

## Resumo de Gaps e Bugs

| ID | Estado | Descricao curta | Prioridade |
|---|---|---|---|
| US-AD-004 | Gap | Dupla saudacao ao enviar midia: frontend chama `assumir()` + backend tambem auto-assume | Alta |
| US-AD-008 | — | Silent devolver nao exposto na UI — decisao intencional de produto | — |
| US-AD-010 | Gap | Desativar atendente nao publica SSE para conversas liberadas; `status_conversa` nao e resetado para "open" | Media |
| US-AD-011 | Gap | Conversa "resolved" com nova mensagem do cliente nao reabre automaticamente — invisivel no filtro padrao | Media |
| US-AD-012 | Bug | `assumir()` nao limpa `snoozed_until` no DB, deixando estado inconsistente | Alta |
| US-AD-014 | Gap | Apos 403 em `/enviar`, frontend nao forca reload do estado — atendente pode continuar tentando | Media |
| US-AD-015 | Gap | Sem indicador visual de atendente offline mid-conversation; conversas ficam em limbo invisivel | Baixa |
