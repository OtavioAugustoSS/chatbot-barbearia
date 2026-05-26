# BR-004: Handoff Humano — Gatilhos, Mecanismo e Reativacao

Data: 2026-05-21
Stakeholders: product-owner-agent (FASE 3 — formalização de regra hardcoded preexistente)

## Contexto

O sistema opera em dois modos (bot_only e hibrido). Em modo hibrido, um atendente humano pode assumir uma conversa do bot a qualquer momento. O handoff é a transição de controle do bot para o atendente. A reativacao é o retorno do controle ao bot após o atendimento humano. Ambos os fluxos têm regras rígidas para evitar conflitos de estado (bot enviando mensagem enquanto atendente está presente) e condições de corrida.

## Regra

### Gatilhos de handoff (bot -> humano)

Dois gatilhos exclusivos:

1. **`intencao == "chamar_recepcao"`**: a IA retorna esta intenção quando o cliente pede explicitamente para falar com um atendente, recepção ou pessoa real genérica. O bot envia mensagem de transição e seta `bot_ativo=False`, `aguardando_humano=True`.

2. **`intencao == "transbordo_falha"`**: disparado automaticamente quando o parse JSON da resposta da IA falha (após sanitização e tentativas de recuperação). Garante que o cliente nunca fique sem resposta mesmo em falha técnica.

Nenhum outro valor de intenção aciona handoff. Em especial: `tirar_duvida` NUNCA aciona handoff, mesmo que a resposta mencione a recepção.

### Botao "Falar c/ Recepcao" no dashboard

O botão "Falar c/ Recepcao" no frontend do atendente executa a mesma lógica de `chamar_recepcao` — seta `bot_ativo=False`, `aguardando_humano=True` — e não tem comportamento diferenciado.

### O caso Fred (excecao explicita)

Quando o cliente pergunta pelo Fred especificamente, a intenção é `tirar_duvida` e o bot responde com o número direto. Esta interação NUNCA aciona handoff. Ver BR-002.

### Modo bot_only durante handoff

Em modo `bot_only`, se a IA retornar `chamar_recepcao`, o bot substitui a mensagem de handoff pela orientação de usar o AppBarber (nenhum humano está disponível). O campo `bot_ativo` permanece `True`.

### Reativacao (humano -> bot)

Endpoint `POST /admin/devolver/{telefone}` (modo hibrido):
1. Envia mensagem de despedida ao cliente PRIMEIRO (antes de reativar o bot)
2. Seta `bot_ativo=True`, `aguardando_humano=False`
3. Publica evento SSE

A ordem é crítica: reativar antes de enviar a despedida cria condição de corrida se o cliente responder durante o envio.

### Auto-reativacao

Se `bot_ativo=False` e `BOT_REATIVAR_APOS_HORAS` (padrão: 24) horas tiverem passado desde o handoff, o bot é reativado automaticamente na próxima mensagem recebida do cliente, sem intervenção humana.

### Comando de staff

O comando `!reiniciar` enviado via WhatsApp por um número listado em `ADMIN_PHONES` reativa `bot_ativo=True` imediatamente para o usuário, sem mensagem de despedida.

## Implementacao em codigo

- **`api/webhook.py`**: verifica `bot_ativo` antes de processar qualquer mensagem; drop silencioso se `False`.
- **`api/admin.py`**: endpoints `assumir`, `devolver`, `enviar` gerenciam o estado de handoff.
- **`services/ai_service.py`**: detecta `chamar_recepcao` e `transbordo_falha` na resposta da IA.
- **`db/models.py`**: campos `Usuario.bot_ativo` (bool) e `Usuario.aguardando_humano` (bool).

## Excecoes

- `!reiniciar` pode ser enviado por qualquer número em `ADMIN_PHONES` sem autenticação JWT.
- Auto-reativacao ocorre silenciosamente — cliente não é notificado de que o bot voltou.

## Notas de produto

- GAP-06 (documentado em BR-AUDIT-001): endpoint `devolver` sempre envia mensagem de despedida. Não há opção de reativação silenciosa do bot sem despedida. Esta é uma decisão de produto pendente de avaliação — adicionar parâmetro `?silencioso=true` ao endpoint pode ser útil para casos de atendimento rápido onde a despedida formal seria redundante.
- GAP-08: evento SSE `atendente_assumiu` não inclui nome do atendente. Impacto: outros atendentes veem na fila que uma conversa foi assumida, mas não por quem.
