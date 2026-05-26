---
name: BR-007-anti-drift-ancora
description: Em conversas longas (>= 4 turnos no historico), uma ancora de regras criticas e injetada antes da mensagem do cliente para prevenir deriva da IA.
metadata:
  type: business-rule
---

# BR-007 — Mecanismo Anti-Drift (Ancora de Regras)

Data: 2026-05-22
Stakeholders: product-owner-agent (auditoria autonoma — mecanismo tecnico sem BR formal)

## Contexto

LLMs tendem a "esquecer" instrucoes do system prompt em conversas longas — fenomeno conhecido como context drift. Em conversas com 4+ turnos, a Barbearia Bolshoi observou que o modelo Llama 3.1 70B comecou a: (a) incluir descricoes de servico em listas quando deveria mostrar apenas nome+preco, (b) somar precos ao inves de indicar combos existentes, (c) oferecer agendamento em vez de redirecionar ao AppBarber.

O mecanismo `ANCORA_ANTI_DRIFT` foi criado para mitigar isso injetando um lembrete compacto das regras criticas imediatamente antes da mensagem atual do cliente.

## Regra

### Condicao de ativacao

Threshold: `len(historico_mensagens) >= 4`.

Cada mensagem do historico representa uma troca (cliente ou bot). Portanto, 4 mensagens = aproximadamente 2 rodadas completas de dialogo (cliente + bot x2).

### Conteudo da ancora

A ancora `ANCORA_ANTI_DRIFT` (definida em `core/prompts.py`) reforga as seguintes regras:
1. Escopo exclusivo: Barbearia Bolshoi
2. Proibicao de inventar precos, servicos, barbeiros ou horarios
3. Formato de lista: apenas `emoji + nome + "— R$ valor"` — descricao e tempo sao referencia interna
4. Proibicao de prometer agendamento — sempre redirecionar AppBarber
5. Proibicao de somar precos — combos existem ou nao existem no cardapio
6. Comportamento por modo (bot_only vs hibrido): nao oferecer recepcao em bot_only
7. Formato de saida: JSON puro com exatamente duas chaves

### Posicao na cadeia de mensagens

A ancora e inserida como mensagem `{"role": "system"}` IMEDIATAMENTE antes da mensagem `{"role": "user"}` com a pergunta atual. Isso maximiza a janela de atencao do modelo sobre as instrucoes criticas no momento da geracao da resposta.

## Comportamento esperado

- Conversas com <= 3 mensagens no historico: sem ancora (system prompt e suficiente)
- Conversas com >= 4 mensagens: ancora injetada automaticamente, sem acoes do atendente ou do cliente
- A ancora nao e visivel ao cliente — e apenas parte do payload de chamada a API

## Custo e impacto

- Custo: ~200 tokens extras por chamada em conversas longas
- Beneficio: reducao significativa de drift em alucinacao de precos e promessas de agendamento
- O threshold 4 foi reduzido de 6 para 4 na Sprint FASE 3 (QW-B4) apos evidencia de drift precoce em conversas de disponibilidade/agendamento

## Excecoes

Nenhuma excecao por tipo de mensagem. A ancora e aplicada indiscriminadamente quando o threshold e atingido.

## Implementacao em codigo

- `core/prompts.py`: constante `ANCORA_ANTI_DRIFT` com o texto da ancora
- `services/ai_service.py`: funcao `processar_intencao()`, linha de injecao: `if len(historico_mensagens) >= 4: messages_payload.append({"role": "system", "content": ANCORA_ANTI_DRIFT})`

## Notas de produto

- Se novos tipos de drift forem identificados em `erro_ia_debug.txt`, o conteudo de `ANCORA_ANTI_DRIFT` deve ser atualizado — nao o threshold
- O threshold so deve ser reduzido abaixo de 4 com evidencia concreta de drift anterior a esse ponto
- Alternativa nao implementada: resumo comprimido do historico (mais cara, mais eficaz para conversas muito longas — considerar se historico exceder 15 turnos)
