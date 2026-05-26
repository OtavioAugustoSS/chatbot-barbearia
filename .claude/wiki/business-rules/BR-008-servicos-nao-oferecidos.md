---
name: BR-008-servicos-nao-oferecidos
description: Quando o cliente pede servico fora do cardapio, o bot recusa sem inventar e redireciona ao AppBarber. Nunca promete servico futuro.
metadata:
  type: business-rule
---

# BR-008 — Servicos Nao Oferecidos e Nomes Populares de Corte

Data: 2026-05-22
Stakeholders: product-owner-agent (auditoria autonoma — duas regras relacionadas sem BR formal)

## Contexto

Clientes frequentemente perguntam por servicos que a barbearia nao oferece (progressiva, tatuagem, manicure, depilacao, etc.) ou usam nomes populares/regionais para estilos de corte que existem no cardapio sob nome generico ("Corte"). Sem regra clara, o bot poderia inventar que "talvez ofereça no futuro" ou nao saber que "degrade" e um servico de corte ja disponivel.

## Regra

### Parte A — Servicos fora do cardapio

Quando o cliente pergunta por servico que nao existe em `{lista_servicos_do_banco}`:

Resposta obrigatoria:
> "Esse servico nao faz parte do nosso cardapio atual. Para conferir tudo o que oferecemos, acesse o AppBarber: https://sites.appbarber.com.br/bolshoi"

Comportamentos proibidos:
- "Talvez no futuro" — proibido prometer expansao de cardapio
- "Nao sei dizer, pode ser que sim" — proibido
- Inventar qualquer servico que nao esteja na lista injetada do banco

Exemplos de servicos tipicamente fora do cardapio da Barbearia Bolshoi:
- Progressiva, alisamento, escova progressiva
- Tatuagem
- Depilacao
- Manicure, pedicure
- Quimica (permanente, tintura — salvo se houver na lista do banco)

### Parte B — Nomes populares de estilos de corte

Varios estilos populares sao variantes do servico generico "Corte" no cardapio. O bot DEVE reconhecer esses nomes e mapeá-los ao servico existente.

Lista canonica de mapeamentos (nomes populares → "Corte"):
- degradê, degrade, fade, low fade, mid fade, high fade
- taper, taper fade
- disfarçado, navalhado
- undercut, social, militar, americano
- comb over, mullet, viking, maquina baixa

Quando o cliente pedir qualquer um desses estilos, o bot responde:
> "Esse estilo se enquadra no nosso servico de Corte (R$ [preco exato do banco]). Praticamente toda nossa equipe atende. Para escolher e agendar: https://sites.appbarber.com.br/bolshoi"

O bot NUNCA responde "nao temos essa informacao" para esses estilos. Isso seria falso positivo — o servico existe.

### Parte C — Corte com risco/desenho especifico

Se o cliente pedir "corte com risco", "corte com desenho", "corte com arabesco" ou similar:
- Verificar se o servico "Corte com Desenho" existe na lista do banco
- Se existir: redirecionar para esse servico especifico (nao para "Corte" generico)
- Se nao existir: aplicar Parte A (servico fora do cardapio)

## Gatilhos

- Qualquer mensagem perguntando sobre servico que nao consta em `{lista_servicos_do_banco}`
- Qualquer mensagem com nome popular de estilo de corte listado na Parte B

## Comportamento esperado

| Mensagem do cliente | Situacao | Acao |
|---|---|---|
| "fazem progressiva?" | Fora do cardapio | Parte A: recusar sem prometer |
| "fazem degrade?" | Nome popular de corte | Parte B: mapear para "Corte" |
| "fazem corte com risco?" | Depende do banco | Parte C: verificar "Corte com Desenho" |
| "fazem alisamento?" | Fora do cardapio | Parte A: recusar sem prometer |

## Excecoes

- Se o banco de servicos for atualizado e incluir um servico antes considerado "fora do cardapio", o bot automaticamente o reconhece na proxima atualizacao do cache (5 min de TTL)
- Novos nomes populares de estilos de corte devem ser adicionados explicitamente ao prompt (nao sao detectados automaticamente)

## Implementacao em codigo

- `core/prompts.py`, regra 5: lista canonica de nomes populares e mapeamento para "Corte"
- `core/prompts.py`, regra 8: instrucao de recusa para servicos nao oferecidos
- `core/prompts.py`, regra 14(a): excecao explicita — nomes populares nao sao "info nao listada"

## Notas de produto

- A lista de nomes populares da regra 5 do prompt deve ser revisada periodicamente com base em perguntas frequentes reais dos clientes
- Se o banco for expandido com novos servicos (ex.: coloracao masculina), o sistema os reconhece automaticamente — nao exige alteracao de prompt para novos servicos
- Servicos de estetica (Isabella) que nao existem no banco seguem a mesma regra de Parte A
