---
name: BR-006-escopo-bot-conteudo
description: O bot responde APENAS sobre Barbearia Bolshoi. Qualquer assunto fora do escopo é recusado com frase padrao.
metadata:
  type: business-rule
---

# BR-006 — Escopo de Conteudo do Bot

Data: 2026-05-22
Stakeholders: product-owner-agent (auditoria autonoma — regra hardcoded sem BR formal)

## Contexto

A regra 10 do `SYSTEM_PROMPT_BARBEARIA` define escopo estrito: o bot nao fala sobre nada alem da Barbearia Bolshoi. Esta e uma decisao de produto deliberada para evitar que o bot vire assistente geral e perca a identidade de marca.

## Regra

O bot opera em escopo fechado. Topicos permitidos:
- Servicos e precos da barbearia
- Equipe de profissionais (barbeiros e esteticista Isabella)
- Agendamento (redirecionamento ao AppBarber — nunca executa)
- Horario de funcionamento
- Localizacao/endereco
- Formas de pagamento
- Estrutura do estabelecimento (Wi-Fi, climatizacao, acessibilidade, atendimento infantil)
- Atendimento feminino
- Cancelamento/remarcacao (redirecionamento ao AppBarber — nunca executa)
- Contato do Fred (so se cliente pedir explicitamente — ver BR-002)

Topicos proibidos (bot recusa com frase padrao):
- Politica, receitas, matematica, conselhos pessoais
- Assuntos externos a Barbearia Bolshoi
- Qualquer pergunta que nao se enquadre nas categorias acima

## Comportamento esperado

Ao receber mensagem fora do escopo, o bot responde:

> "Sou treinado unicamente para ajudar com o ecossistema da Barbearia Bolshoi. Como posso te auxiliar com nossos servicos de barbearia e estetica?"

Intencao retornada: `tirar_duvida` (nunca `chamar_recepcao` por motivo de escopo).

## Gatilhos

- Qualquer mensagem cujo conteudo nao se enquadre nos topicos permitidos acima
- Perguntas sobre outros estabelecimentos
- Pedidos de comparacao com concorrentes

## Excecoes

Nenhuma. O escopo e fixo e nao pode ser expandido por solicitacao do cliente durante a conversa.

## Implementacao em codigo

- `core/prompts.py`, regra 10: instrucao explicita de escopo com frase padrao exata
- A frase padrao e hardcoded no prompt — nao pode ser alterada sem atualizacao do arquivo

## Notas de produto

- A frase "ecossistema da Barbearia Bolshoi" usa linguagem ligeiramente formal proposital — reforco de identidade de marca premium
- Se cliente insistir em assunto fora do escopo, o bot repete a recusa ou redireciona para o menu principal
- Nao e papel do bot detectar intencao maliciosa — apenas manter o escopo tematico
