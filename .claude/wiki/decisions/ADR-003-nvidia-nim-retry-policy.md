# ADR-003: Política de Retry e Ausência de Circuit Breaker para NVIDIA NIM
Status: aceito
Data: 2026-05-21
Decisor: architect-agent
Stakeholders consultados: backend-agent (código existente como fonte de verdade)

## Contexto

`services/ai_service.py` usa o cliente OpenAI-compatible apontado para `https://integrate.api.nvidia.com/v1` para chamar o modelo `meta/llama-3.1-70b-instruct`. A decisão de retry foi tomada implicitamente ao adicionar `tenacity`. Não há circuit breaker implementado. Esta ADR formaliza a política atual e documenta o risco aceito.

## Decisão

### Retry policy atual (via tenacity)

```python
@retry(
    retry=retry_if_exception_type((openai.APITimeoutError, openai.APIConnectionError)),
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=1, max=8),
    reraise=True,
)
def _chamar_llm(self, messages):
    ...
```

- **Máximo de tentativas**: 3 (1 original + 2 retries)
- **Tipos de erro que geram retry**: `APITimeoutError`, `APIConnectionError` apenas — erros 4xx (rate limit, bad request) NÃO fazem retry
- **Backoff**: exponencial, 1s → 2s → 4s (cap 8s), portanto até ~7s de espera entre tentativas
- **Timeout por chamada**: 30 segundos (configurado no `create()`)
- **Tempo máximo total possível**: 30s + 1s + 30s + 2s + 30s = ~93s por mensagem
- **Consequência de esgotamento de retries**: exceção é relançada (`reraise=True`), capturada pelo `except Exception` em `processar_intencao`, retorna `transbordo_falha`

### O que NÃO está implementado (e por quê)

**Circuit breaker**: não implementado. Racional aceito:
- O NVIDIA NIM é chamado em background task — falha não bloqueia o webhook (Meta recebe 200 OK imediatamente)
- Em falha total da IA, o fallback é `transbordo_falha` → handoff humano (comportamento razoável)
- Volume de mensagens é baixo (barbearia local) — probabilidade de cascata de falhas é pequena

**Rate limit awareness**: NIM pode retornar 429 mas o retry não discrimina tipos de 4xx para não fazer retry em erros `RateLimitError`. Isso está correto — retry em 429 apenas pioraria o throttle.

**Timeout adaptativo**: timeout fixo em 30s. Sem P95/P99 de latência da NVIDIA, não há como calibrar.

### Registro de erros

Erros da IA são persistidos em `erro_ia_debug.txt` com timestamp ISO via `_registrar_erro_debug()`. Não há alertas ou métricas — depende de inspeção manual.

## Consequências

- Positivo: simples, sem dependências adicionais, adequado ao volume atual
- Positivo: falha da IA não causa crash do servidor — sempre há um fallback
- Negativo: sem circuit breaker, se NVIDIA NIM ficar down prolongadamente, cada mensagem vai consumir ~93s de threads em background até esgotar
- Negativo: `erro_ia_debug.txt` cresce ilimitadamente — sem rotação de log
- Risco: em `MODO_HIBRIDO`, uma chamada IA que demora 93s pode resultar em condição de corrida onde o atendente assumiu durante o retry e o resultado da IA é descartado (protegido pelo re-check `db.refresh(user)` antes do envio — correto)

## Alternativas consideradas

- `circuitbreaker` lib: seria útil se o volume de chamadas fosse alto; no MVP com <100 msgs/dia, o overhead não justifica
- `asyncio` com timeout: exigiria refatorar `_processar_mensagem` para async, o que tem implicações na background task architecture — rejeitado por escopo
- Configurar retry para `RateLimitError` com espera longa: rejeitado — piora o throttle e aumenta latência percebida

## Revisão recomendada

Se o volume crescer para >500 msgs/dia ou se logs mostrarem >10 `transbordo_falha` por hora, avaliar:
1. Implementar circuit breaker com `pybreaker` ou similar
2. Adicionar rotação de `erro_ia_debug.txt` (logrotate ou troca por `logging.handlers.RotatingFileHandler`)
3. Métricas de latência IA (pode ser simples: append de `elapsed` em arquivo CSV)
