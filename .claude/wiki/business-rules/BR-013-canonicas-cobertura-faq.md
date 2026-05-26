---
name: BR-013-canonicas-cobertura-faq
description: Auditoria de cobertura das respostas canonicas. Identifica FAQs de barbearia nao cobertas por canonicas e define quais devem ir para IA vs canonicas.
metadata:
  type: business-rule
---

# BR-013 — Cobertura de FAQ pelas Respostas Canonicas

Data: 2026-05-22
Stakeholders: product-owner-agent (auditoria autonoma — analise de gaps nas canonicas)

## Contexto

O sistema usa canonicas (respostas determinísticas via regex) para reduzir custo de tokens e eliminar alucinacao em FAQs previsíveis. A auditoria de `core/respostas_canonicas.py` identificou gaps — perguntas frequentes de barbearia que nao tem canonicas e poderiam ter.

## Canonicas existentes (cobertura atual)

| Canonicas | Padrao detectado |
|---|---|
| `RESPOSTA_HORARIO` | Horario de funcionamento |
| `RESPOSTA_ENDERECO` | Localizacao/endereco |
| `RESPOSTA_AGENDAMENTO` / `RESPOSTA_AGENDAMENTO_HIBRIDO` | Como agendar, link do app |
| `RESPOSTA_PAGAMENTO` | Formas de pagamento |
| `RESPOSTA_FAQ_ESTRUTURA` | Wi-Fi, ar condicionado, acessibilidade, infantil |
| `RESPOSTA_CANCELAR_REMARCAR` | Cancelamento e remarcacao |
| `RESPOSTA_ATENDIMENTO_FEMININO` | Atende mulher? Cabelo feminino? |
| `RESPOSTA_DISPONIBILIDADE_FRED` | Fred esta la hoje/amanha? |
| (exlusao) `_PADRAO_DISPONIBILIDADE` | Slot disponivel → vai para IA (contexto temporal) |

## Analise de gaps — FAQs sem canonicas

### Gap A — "Qual o telefone / como contato voces?" (telefone da barbearia)

**Situacao atual:** Sem canonicas. Vai para IA.
**Risco:** IA pode inventar numero incorreto ou dar o telefone do Fred sem o cliente pedir.
**Decisao:** Adicionar canonicas para contato geral da barbearia (se houver numero comercial). Se nao houver numero comercial publico, a canonicas deve orientar para o AppBarber + indicar que atendimento e via WhatsApp.

**Acao para desenvolvimento:** Verificar com o Fred se ha numero comercial para exibir. Se sim, criar `RESPOSTA_CONTATO` com o numero. Se nao, a resposta e que o atendimento e exclusivamente via WhatsApp.

**Status:** Pendente de informacao do cliente (Fred/proprietario). NAO implementar ate confirmar.

### Gap B — "Voces tem estacionamento?"

**Situacao atual:** Sem canonicas. Vai para IA.
**Comportamento atual da IA:** Regra 14(c) do prompt instrui a responder: "Nao tenho essa informacao aqui. Para confirmar, acesse o AppBarber..."
**Avaliacao:** Este comportamento esta correto — o sistema nao tem informacao de estacionamento. Canonicas nao precisam cobrir isso; a IA trata adequadamente.
**Decisao:** Nao criar canonicas. Manter na IA com a regra atual.

### Gap C — "Preciso marcar para crianca / criancas podem ir?"

**Situacao atual:** Parcialmente coberto por `RESPOSTA_FAQ_ESTRUTURA` (menciona "atendimento especializado infantil") e pela regra de atendimento feminino. Mas a pergunta direta "atende crianca?" nao tem canonicas.
**Avaliacao:** A `RESPOSTA_FAQ_ESTRUTURA` ja cobre o tema, mas o trigger regex nao pega a pergunta "atende crianca?" diretamente.
**Decisao:** Expandir o regex de `RESPOSTA_FAQ_ESTRUTURA` para incluir variantes de "crianca" e "infantil" que disparem a mesma resposta. Este e um quick win de canonicas.

**Adicao ao regex de `RESPOSTA_FAQ_ESTRUTURA`:**
```
r"atende(m)?\s+crian[cç]a|"
r"corte\s+(infantil|de\s+crian[cç]a)|"
r"tem\s+atendimento\s+para\s+crian[cç]a|"
r"meu\s+filho\s+pode\s+(ir|cortar)"
```

### Gap D — "Quanto tempo dura o atendimento?"

**Situacao atual:** Sem canonicas. Vai para IA.
**Avaliacao:** A duracao varia por servico (injetada como `ref:` no prompt). A IA e a melhor fonte para isso — ela tem acesso aos dados de `tempo_estimado_minutos` por servico.
**Decisao:** Nao criar canonicas. Manter na IA.

### Gap E — "Tem lista de espera?" / "Tao cheio hoje?"

**Situacao atual:** Sem canonicas. Vai para IA via `_PADRAO_DISPONIBILIDADE` (excluido de canonicas — vai para IA por design).
**Avaliacao:** Corretamente na IA. O bot nao tem acesso a lista de espera em tempo real.
**Decisao:** Nao criar canonicas. Comportamento atual correto: IA orienta AppBarber para ver horarios.

### Gap F — "Voces abrem no feriado?"

**Situacao atual:** Sem canonicas. Vai para IA.
**Comportamento atual da IA:** Sem instrucao especifica sobre feriados — pode alucinar ou dar informacao incorreta.
**Decisao:** Adicionar instrucao ao prompt da IA para feriados: "Para feriados nao previstos no horario regular, informe ao cliente que o funcionamento pode variar e oriente a confirmar pelo AppBarber ou entrar em contato diretamente."
**Acao:** Atualizar `core/prompts.py` com regra de feriados. Nao criar canonicas (feriados variam por data).

## Decisoes de produto

| FAQ | Canonicas | IA | Status |
|---|---|---|---|
| Telefone da barbearia | Pendente (falta info) | Atual | Aguarda confirmacao do Fred |
| Estacionamento | Nao | Sim (regra 14c) | OK — IA trata corretamente |
| Atende crianca? | Expandir regex existente | Nao | Quick win — Sprint 0.3.0 |
| Duracao do atendimento | Nao | Sim | OK |
| Lista de espera / lotacao | Nao | Sim | OK |
| Feriados | Nao | Sim + nova regra no prompt | Adicionar regra ao prompt |

## Impacto em codigo

### Acao 1 — Expandir regex RESPOSTA_FAQ_ESTRUTURA (Gap C)
Arquivo: `core/respostas_canonicas.py`
Adicionar ao regex de `RESPOSTA_FAQ_ESTRUTURA`:
```python
r"atende(m)?\s+crian[cç]a(s)?|"
r"corte\s+(infantil|de\s+crian[cç]a)|"
r"(meu\s+)?(filho|filha|bebe|nenem)\s+pode\s+(ir|cortar|vir)|"
r"atendimento\s+infantil"
```

### Acao 2 — Regra de feriados no prompt (Gap F)
Arquivo: `core/prompts.py`
Adicionar nova regra (sugerida como regra 19 ou adicao a regra 16):
> "19. FERIADOS: a Barbearia Bolshoi pode ter horario diferente em feriados. Quando o cliente perguntar sobre funcionamento em feriado especifico, informe que o horario pode variar e oriente a confirmar via AppBarber ou diretamente na barbearia."

## Notas de produto

- As canonicas cobrem as perguntas de maior volume e menor variacao. O threshold para criar uma nova canonicas e: (a) resposta sempre identica independente do contexto, (b) pergunta claramente frequente, (c) risco de alucinacao da IA e real
- FAQ de "cancelamento/remarcacao" e "atendimento feminino" foram adicionadas recentmente — ambas seguiram este criterio
- A regra de feriados NO prompt (nao em canonicas) e intencional: feriados tem contexto variavel que a IA precisa considerar junto com o contexto temporal injetado
