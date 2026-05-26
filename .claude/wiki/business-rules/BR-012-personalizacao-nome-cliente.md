---
name: BR-012-personalizacao-nome-cliente
description: O nome do cliente e injetado na IA quando disponivel, permitindo personalizacao do atendimento. Regras sobre quando e como usar o nome.
metadata:
  type: business-rule
---

# BR-012 — Personalizacao por Nome do Cliente

Data: 2026-05-22
Stakeholders: product-owner-agent (auditoria autonoma — logica de personalizacao sem BR formal)

## Contexto

O sistema injeta o nome do cliente (`Usuario.nome_cliente`) como mensagem de sistema para a IA quando o valor nao e nulo. A IA recebe a instrucao: "O cliente atual se chama '{nome}'. Use o nome para personalizar o atendimento quando apropriado."

Esta personalizacao e uma feature de experiencia do cliente — usa o nome fornecido pelo WhatsApp Business API (via Meta webhook payload `contacts[].profile.name`).

## Regra

### Quando o nome e injetado

- Se `Usuario.nome_cliente` nao for None: IA recebe o nome via mensagem de sistema
- Se `Usuario.nome_cliente` for None: IA nao recebe instrucao de nome (responde sem personalizacao)

### Como a IA deve usar o nome

O nome pode ser usado para:
- Saudacao inicial ("Ola, {Nome}! Como posso ajudar?")
- Personalizacao contextual em mensagens de confirmacao ou encerramento

O nome NAO deve ser usado em:
- Toda mensagem do bot (repetir o nome toda hora soa artificial)
- Mensagens de resposta simples de fato ("O corte sai por R$ 50,00.")
- Listas de servicos ou barbeiros

### Formato e tratamento do nome

- Usar apenas o primeiro nome (se o nome completo estiver disponivel)
- Capitalizar adequadamente (a API do Meta retorna como o usuario cadastrou no WhatsApp)
- Se o nome tiver acentos ou caracteres especiais, manter como recebido — nao latinizar

### Captura do nome

O nome e capturado do payload do WhatsApp na primeira mensagem do cliente via:
- `contacts[0].profile.name` no payload do Meta Cloud API
- Salvo em `Usuario.nome_cliente` na criacao do registro

A barbearia nao tem autonomia para alterar o nome — ele e o nome do perfil WhatsApp do cliente.

## Comportamento esperado na primeira mensagem

A primeira mensagem de um novo cliente recebe sempre o menu de boas-vindas fixo (pre-IA), com o primeiro nome quando disponivel. O sistema em `api/webhook.py` extrai `nome_cliente` do payload e salva no banco antes de qualquer processamento da IA.

## Excecoes

- Clientes que nao tem nome configurado no WhatsApp Business (numero sem perfil): `nome_cliente=None`, bot atende sem personalizacao
- Nomes muito longos ou que parecem nomes de empresa: usar como recebido, sem truncamento

## Implementacao em codigo

- `services/whatsapp.py`: extracao do nome do payload Meta (`contacts[0].profile.name`)
- `db/models.py`: `Usuario.nome_cliente` (String 100, nullable)
- `services/ai_service.py`: `processar_intencao()`, injecao condicional: `if nome_cliente: messages_payload.append(...)`
- `api/webhook.py`: salva nome na criacao/atualizacao do usuario

## Notas de produto

- O nome do cliente e visivel no dashboard de atendentes (info panel) — consistente com a personalizacao do bot
- Nao ha mecanismo de "atualizar nome" se o cliente mudar o nome no WhatsApp — o banco manteria o nome antigo ate uma logica de atualizacao ser implementada
- Privacidade: o nome e dado publico do perfil WhatsApp — nao ha restricao legal de uso para personalizacao de atendimento em contexto de negocio
