# ADR-006: Sanitização Pré-Parse de JSON da IA e Política de Fallback
Status: aceito
Data: 2026-05-21
Decisor: architect-agent
Stakeholders consultados: backend-agent (código existente como fonte de verdade)

## Contexto

O modelo Llama 3.1 70B via NVIDIA NIM é instruído a retornar JSON puro `{"intencao": "...", "resposta_sugerida": "..."}`. Na prática, modelos de linguagem às vezes envolvem o JSON em blocos de código markdown (`` ```json ... ``` ``). A sanitização foi adicionada organicamente e precisa ser formalizada.

## Decisão

### Sanitização pré-parse (pipeline atual em `ai_service.py`)

Aplicada ao `response_text` bruto antes de `json.loads()`:

1. Strip de espaços nas pontas
2. Remoção de bloco de código markdown:
   - Se começa com `` ```json ``: remove os 7 primeiros caracteres
   - Se começa com `` ``` ``: remove os 3 primeiros caracteres
   - Se termina com `` ``` ``: remove os 3 últimos caracteres
3. Strip novamente
4. `json.loads(response_text)`
5. Se o JSON não tem `intencao` mas tem `choices`: tenta extrair JSON aninhado do formato OpenAI bruto (fallback para double-wrapping acidental)

### Validação pós-parse (`_validar_resposta`)

- `intencao` fora do enum `{"tirar_duvida", "chamar_recepcao", "transbordo_falha"}`: substituído por `"tirar_duvida"`
- `resposta_sugerida` contendo padrão de agendamento proibido (regex `_REGEX_AGENDAMENTO_PROIBIDO`): substituída por mensagem redirect AppBarber
- Ambas as validações são silenciosas (apenas `log.warning`) — nunca expõem o erro ao cliente

### Fallback de falha de parse

`json.JSONDecodeError` é capturado e retorna:
```python
{"intencao": "transbordo_falha", "resposta_sugerida": "<mensagem de instabilidade>"}
```
Em `MODO_HIBRIDO`: aciona handoff humano.
Em `MODO_BOT_ONLY`: bot continua ativo, envia mensagem de instabilidade pedindo reformulação.

### Problemas de fragilidade conhecidos (não resolvidos)

1. **Markdown inside JSON**: se a IA colocar `resposta_sugerida` com tripla backtick dentro do valor JSON, o pré-strip atual não resolve. Probabilidade baixa com `response_format={"type": "json_object"}`.
2. **Unicode escape sequences**: `json.loads` trata automaticamente — sem problema.
3. **JSON truncado por max_tokens**: `max_tokens=2048` pode truncar resposta longa, resultando em JSON inválido. Não há detecção específica — cai no fallback genérico `transbordo_falha`.
4. **Campos adicionais no JSON**: ignorados silenciosamente por `dados.get()` — comportamento correto e desejável (tolerância a evolução do modelo).

## Consequências

- Positivo: sistema robusto a variações comuns de output do LLM
- Positivo: nunca expõe erro técnico ao cliente final
- Negativo: JSON truncado por `max_tokens` não tem tratamento diferenciado — poderia aumentar `max_tokens` ou detectar truncamento via `finish_reason == "length"`
- Risco: se a NVIDIA NIM mudar o formato de resposta para double-wrapping em escala, o fallback em `choices[0]["message"]["content"]` cobre o caso mais comum, mas não todos

## Alternativas consideradas

- Usar `response_format={"type": "json_schema", ...}` com schema rígido: NVIDIA NIM suporta isso em versões mais recentes do endpoint; migraria da sanitização manual para validação estrutural. ADR de atualização necessária quando viável.
- `pydantic.TypeAdapter` para parse + validação em uma etapa: melhora mas não elimina a necessidade da sanitização de markdown pré-parse
