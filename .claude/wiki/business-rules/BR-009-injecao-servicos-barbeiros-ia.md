---
name: BR-009-injecao-servicos-barbeiros-ia
description: Servicos e barbeiros sao injetados dinamicamente no system prompt a cada chamada da IA, com cache de 5 minutos. O formato de injecao controla o que a IA pode e nao pode exibir ao cliente.
metadata:
  type: business-rule
---

# BR-009 — Injecao de Servicos e Barbeiros na IA

Data: 2026-05-22
Stakeholders: product-owner-agent (auditoria autonoma — logica critica em ai_service.py sem BR formal)

## Contexto

O system prompt da IA recebe, a cada chamada, a lista atual de servicos e barbeiros do banco de dados. O formato dessa injecao determina o que a IA ve e o que ela pode compartilhar com o cliente. Ha uma distincao intencional entre "dados primarios" (exibir ao cliente) e "referencia interna" (so usar ao responder pergunta direta, nunca em listas).

## Regra

### Formato de injecao de servicos

Cada servico e injetado no formato:
```
emoji nome_do_servico — R$ preco  | ref: dura Xmin; desc: descricao
```

Exemplo:
```
✂️ Corte — R$ 50.00  | ref: dura 30min; desc: Corte de cabelo no estilo que o cliente preferir
```

O separador ` | ref:` e intencional: orienta a IA a tratar o que vem antes como dados primarios e o que vem depois como referencia interna.

### O que a IA PODE exibir ao cliente em listas

Apenas: `emoji + nome do servico + " — R$ valor"`

Exemplos corretos:
- `✂️ Corte — R$ 50,00`
- `✂️ Barba — R$ 50,00`
- `✂️ Corte e Barba — R$ 90,00`

### O que a IA NAO PODE exibir em listas

- Descricao textual do servico
- Tempo estimado em minutos
- O marcador `| ref:` ou qualquer texto apos ele
- Separadores `|` na resposta ao cliente

Descricao e duracao so podem aparecer quando o cliente pergunta DIRETAMENTE sobre um servico especifico (ex.: "o que e hidratacao masculina?", "quanto dura um corte?").

### Categorias de servico

Os servicos sao agrupados em duas categorias, na seguinte ordem de apresentacao:
1. `💈 BARBEARIA` — servicos de barbeiros (corte, barba, etc.)
2. `💆‍♀️ ESTETICA` — servicos exclusivos de Isabella (procedimentos esteticos)

A IA nao pode reclassificar servicos. A categoria vem do campo `categoria` no banco de dados.

### Formato de injecao de barbeiros

Cada barbeiro e injetado no formato:
```
Nome (dias_trabalho) -> Especializa-se em: servico1, servico2, ...
```

Exemplo:
```
Fred (segunda a sabado) -> Especializa-se em: Corte, Barba, Corte e Barba, Acabamento
```

A relacao barbeiro-servico e muitos-para-muitos (`barbeiros_servicos`). Ao responder "quem faz X?", a IA deve consultar essa lista e listar os nomes dos barbeiros que tem aquele servico.

### Cache e TTL

- TTL do cache: 5 minutos (300 segundos)
- Cache e por instancia de `AIService` (memória do processo, nao distribuido)
- O cache e invalidado explicitamente apos mutacoes em `Servico` ou `Barbeiro` via `invalidar_cache_db()`
- Se o cache estiver vazio (primeiro boot), uma query SQL e executada antes da chamada a IA

### Sanitizacao de seguranca

Apos a resposta da IA, `_validar_resposta()` remove automaticamente qualquer ocorrencia de ` | ref: ...` que o modelo tenha copiado por drift, via regex: `r'\s*\|\s*ref:[^\n<]*'`

## Gatilhos

Este mecanismo e ativado em toda chamada a IA que processa mensagem de cliente (funcao `processar_intencao()`).

## Comportamento esperado

| Pergunta do cliente | Dados usados | O que a IA exibe |
|---|---|---|
| "quais servicos voces tem?" | Lista completa do banco | Categorias separadas, sem descricoao |
| "quais servicos de barbearia?" | Categoria barbearia | Lista enxuta: emoji + nome + preco |
| "o que e hidratacao masculina?" | Referencia interna (`ref:`) | Pode usar descricao |
| "quanto dura um corte?" | Referencia interna (`ref:`) | Pode usar duracao |
| "quem faz barba?" | Lista de barbeiros + servicos | Lista de nomes de barbeiros |

## Excecoes

- Se o banco de servicos estiver vazio (`Nenhum servico encontrado.`), a IA deve indicar que os servicos estao temporariamente indisponiveis e sugerir o AppBarber
- Se o banco de barbeiros estiver vazio (`Nenhum barbeiro encontrado.`), a IA deve sugerir o AppBarber para escolher profissional

## Implementacao em codigo

- `services/ai_service.py`: `_carregar_dados_db()` — query + formatacao + cache
- `services/ai_service.py`: `_validar_resposta()` — sanitizacao de ref: leakage (QW-B2)
- `core/prompts.py`: regras 3 (formato de lista), 4 (equipe), 13 (precos)
- `db/models.py`: `Servico` (campos: nome_servico, preco, tempo_estimado_minutos, descricao, categoria, ativo), `Barbeiro` (campos: nome, dias_trabalho), `barbeiros_servicos` (associacao M2M)

## Notas de produto

- A coluna `Barbeiro.dias_trabalho` e String livre — nao ha validacao de formato. Recomendavel que siga o padrao "segunda a sabado" ou "terca, quarta, quinta" para que a IA interprete corretamente
- A coluna `Barbeiro.categoria` NAO existe — a categoria e de `Servico`, nao de `Barbeiro`. Isso significa que um barbeiro pode estar em ambas as categorias se tiver servicos de barbearia e estetica. Na pratica, Isabella e a unica profissional de estetica
- Ao adicionar novo barbeiro ao banco, o cache so e atualizado apos 5 minutos (ou reinicio do servidor) — informar equipe tecnica para chamar `invalidar_cache_db()` ou aguardar TTL
