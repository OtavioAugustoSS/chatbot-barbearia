# BR-002: Contato Pessoal do Fred — Compartilhamento Sob Demanda Explícita

Data: 2026-05-21
Stakeholders: product-owner-agent (FASE 3 — formalização de regra hardcoded preexistente)

## Contexto

Fred é o proprietário da Barbearia Bolshoi. Seu número pessoal (38) 99897-0661 é um contato direto, não um canal de suporte geral. Divulgar este número indiscriminadamente sobrecarrega o proprietário com atendimentos que deveriam ser resolvidos pelo bot, pelo AppBarber ou pela recepção. O número deve aparecer na conversa apenas quando o cliente demonstra intenção explícita de falar com Fred especificamente.

## Regra

O número (38) 99897-0661 é compartilhado SOMENTE quando o cliente perguntar explicitamente por Fred ou pelo contato dele.

Gatilhos que autorizam o compartilhamento:
- "Quero falar com o Fred"
- "Qual o número do Fred?"
- "Me passa o contato do Fred"
- "Preciso falar com o dono"
- "Como falo com o proprietário?"
- Qualquer variação que mencione Fred pelo nome ou refira-se explicitamente ao dono/proprietário

Gatilhos que NÃO autorizam o compartilhamento:
- Pedido genérico de falar com "alguém" ou "um atendente" → usar handoff (`chamar_recepcao`)
- Reclamação ou insatisfação genérica → usar handoff
- Dúvida operacional que o bot não sabe responder → usar handoff ou redirecionar AppBarber
- O número NUNCA é usado como fallback genérico quando o bot não sabe a resposta

Resposta obrigatória quando autorizado:
- Intenção: `tirar_duvida` (NUNCA `chamar_recepcao`)
- Texto: "O contato direto do Fred é (38) 99897-0661."
- Sem prometer transferência, sem mencionar recepção

## Implementação em código

- **System prompt** (`core/prompts.py`, regra 11 e caso especial): instrução explícita sobre o caso Fred com exemplo de JSON de saída correto.
- O caso Fred é tratado com `intencao = "tirar_duvida"` — não aciona handoff humano, não seta `bot_ativo=False`.

## Exceções

Nenhuma. O número não deve aparecer em respostas de fallback, menus, ou qualquer resposta proativa.

## Notas de produto

- Esta regra é distinta do handoff humano (BR-004). Perguntar pelo Fred resolve-se com `tirar_duvida` + número; pedir um atendente genérico resolve-se com `chamar_recepcao`.
- Se o cliente perguntar pelo Fred E pedir para falar com recepção na mesma mensagem, a menção ao Fred tem prioridade — fornecer o número e não acionar handoff.
