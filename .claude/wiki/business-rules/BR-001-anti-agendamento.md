# BR-001: Anti-Agendamento Absoluto — Bot NUNCA Agenda

Data: 2026-05-21
Stakeholders: product-owner-agent (FASE 3 — formalização de regra hardcoded preexistente)

## Contexto

O bot WhatsApp da Barbearia Bolshoi não tem acesso à agenda do AppBarber em tempo real. Toda tentativa de fazer o bot prometer, marcar, confirmar, cancelar ou remarcar horários cria expectativa falsa no cliente e compromete a confiança na barbearia. Esta é a regra de negócio mais crítica do sistema — sua violação gera impacto direto no cliente e na reputação da barbearia.

## Regra

O bot NUNCA agenda, cancela, remarca ou reserva horário. Sem exceções.

Comportamentos proibidos (qualquer variação linguística):
- "Marquei para você"
- "Agendei seu horário"
- "Reservei o horário"
- "Confirmei para quinta-feira"
- "Vou marcar para você"
- "Posso agendar para você"
- "Estou à disposição para agendar"
- "Vou cancelar seu horário"
- "Remarquei para você"
- "Alterei sua data"

Redirecionamento obrigatório em todos os casos:
- Agendamento: "Para agendar, acesse: https://sites.appbarber.com.br/bolshoi"
- Cancelamento/remarcação: "Cancelamentos e remarcações são feitos diretamente no aplicativo: https://sites.appbarber.com.br/bolshoi — localize seu agendamento e escolha cancelar ou alterar."

A regra se aplica também ao fornecimento de informações de disponibilidade de slots: o bot informa o horário de funcionamento do dia, mas deixa claro que apenas o AppBarber mostra vagas disponíveis em tempo real.

## Implementação em código

Três camadas de proteção independentes:

1. **System prompt** (`core/prompts.py`, regra 6): instrução explícita "PROIBIDO PROMETER" com exemplos negativos e positivos.
2. **Regra 7 do prompt**: cancelamento e remarcação também proibidos — redirecionamento obrigatório para AppBarber.
3. **Anti-appointment regex** (`services/ai_service.py`, função `_validar_resposta()`): expressão regular que detecta promessas de agendamento na saída da IA e as substitui silenciosamente pelo redirecionamento AppBarber, mesmo que o modelo ignore o prompt.
4. **ANCORA_ANTI_DRIFT** (`core/prompts.py`): reforço injetado em conversas com 6+ turnos, lembrando ao modelo: "NUNCA prometa marcar/agendar/reservar/cancelar/remarcar."
5. **Canônica de agendamento** (`core/respostas_canonicas.py`, `RESPOSTA_AGENDAMENTO`): padrões de intenção de agendar detectados por regex antes mesmo de a IA ser chamada — resposta determinística sem custo de token.
6. **Canônica de cancelamento** (`core/respostas_canonicas.py`, `RESPOSTA_CANCELAR_REMARCAR`): idem para cancelar/remarcar.

## Exceções

Nenhuma. Esta regra não tem exceções operacionais. Mesmo em modo híbrido, o bot não agenda — o máximo permitido é transferir a conversa para um atendente humano que poderá orientar o cliente no AppBarber.

## Notas de produto

- O SEC-GAP documentado em hot.md (2026-05-21) indica que a regex anti-agendamento cobre apenas 1 de 5 padrões de booking. QW-B3 (FASE 3) expande para 5+ padrões. Esta expansão é requisito de compliance desta BR.
- Qualquer novo padrão de evasão identificado em `erro_ia_debug.txt` deve ser adicionado à regex imediatamente.
