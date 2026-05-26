---
name: ADR-010-background-task-exception-handling
description: Política de tratamento de exceções em background tasks do webhook
metadata:
  type: decision
  status: ACCEPTED
---

# ADR-010 — Tratamento de Exceções em Background Tasks do Webhook

Status: aceito
Data: 2026-05-22
Decisor: architect-agent
Stakeholders consultados: backend-agent (código como fonte de verdade)

## Contexto

O endpoint `POST /webhook` delega o processamento real para `tarefa_em_segundo_plano_ia()` via
`background_tasks.add_task()`. A função é definida assim (webhook.py, linhas 953–956):

```python
def tarefa_em_segundo_plano_ia(telefone: str, texto_cliente: str):
    with _lock_do_telefone(telefone):
        _processar_mensagem(telefone, texto_cliente)
```

E `_processar_mensagem` tem o bloco:

```python
try:
    # ... toda a lógica de processamento
finally:
    db.close()
```

### Problema identificado: exceção não capturada escapa silenciosamente

`_processar_mensagem` tem `try/finally` que **garante `db.close()`** mas **não captura exceções**.
Se qualquer exceção não esperada ocorrer dentro do `try` (ex: SQLAlchemy `OperationalError` por
conexão perdida, `AttributeError` por modelo None, erro de rede na chamada NVIDIA NIM fora do retry),
ela:

1. Escapa do `try/finally` (o finally roda, mas a exceção propaga)
2. Sobe para `tarefa_em_segundo_plano_ia()`
3. Escapa do `with _lock_do_telefone(telefone):` (o context manager libera o lock corretamente
   via `__exit__`, portanto o lock NÃO fica preso — esse é o comportamento correto)
4. Chega ao FastAPI `BackgroundTasks` runner

**FastAPI captura exceções em background tasks** (`BackgroundTasks._run_single`) e as loga via
`logging.getLogger("fastapi")` com `log.error()`. O cliente WhatsApp **não recebe resposta** pois
o background task falhou após o 200 OK já ter sido retornado.

O resultado visível para o usuário final: mensagem ignorada silenciosamente, sem resposta do bot.
Em produção com `LOG_LEVEL=INFO`, o erro vai para o log do FastAPI mas pode passar despercebido
se não houver monitoramento do log `fastapi` (o projeto usa `barbearia.*` como namespace).

### Problema secundário: threading lock TTL de 30 minutos

O `_LOCK_TTL_SEGUNDOS = 1800` (30 minutos) define por quanto tempo um lock sem uso é mantido
em memória. O lock é recriado a cada mensagem nova do telefone (atualiza o timestamp). O problema
de **starvation** ocorreria se:

1. Thread A adquire o lock para o telefone X
2. Thread A trava indefinidamente (ex: NVIDIA NIM sem timeout, rede travada)
3. Thread B tenta adquirir o lock para o telefone X e fica bloqueada

A chamada NVIDIA NIM (`services/ai_service.py`) usa `tenacity` com 3 tentativas e backoff
exponencial, mas o timeout de rede depende do timeout do `httpx.Client` da biblioteca
`openai`. Se não configurado, o `httpx` usa timeout padrão de 5 segundos por operação.
O pior caso com 3 tentativas é ~15–25 segundos — risco de starvation é baixo mas real.

Não há `acquire(timeout=...)` no código — o lock é bloqueante sem timeout.

## Decisão

### 1. Adicionar captura de exceção raiz em `tarefa_em_segundo_plano_ia`

**Mudança de 2 linhas — implementar imediatamente (não requer sprint):**

```python
def tarefa_em_segundo_plano_ia(telefone: str, texto_cliente: str):
    with _lock_do_telefone(telefone):
        try:
            _processar_mensagem(telefone, texto_cliente)
        except Exception:
            log.exception("Exceção não tratada em background task para %s", telefone)
```

Isso garante que:
- O erro aparece no namespace `barbearia.webhook` (visível com `LOG_LEVEL=INFO`)
- O lock é liberado (context manager já faz isso, mas o log confirma o evento)
- Comportamento de usuário final não muda (mensagem ignorada), mas o problema é rastreável

### 2. Lock sem timeout: aceitar o risco atual, documentar mitigação futura

O risco de starvation é baixo porque:
- O cliente `openai` tem timeout implícito de rede (~5s por operação no modo síncrono)
- `tenacity` limita tentativas a 3 (máximo ~25s total)
- FastAPI `BackgroundTasks` roda em thread pool com limite — threads não crescem infinitamente

**Não adicionar `acquire(timeout=...)` agora** — mudaria o comportamento (mensagem descartada
vs. enfileirada). Se starvation se tornar observável em produção, a solução correta é:

```python
adquirido = lock.acquire(timeout=60)  # 1 minuto máximo de espera
if not adquirido:
    log.warning("Lock timeout para %s — mensagem descartada", telefone)
    return
try:
    _processar_mensagem(telefone, texto_cliente)
finally:
    lock.release()
```

Isso requer refatoração do helper `_lock_do_telefone` para retornar o lock sem context manager.
Registrado como TD-013 (baixo).

### 3. Namespace de log para background tasks

Garantir que o namespace `barbearia.webhook` está configurado no log handler em produção.
Documentar em CLAUDE.md que `LOG_LEVEL=DEBUG` deve ser usado temporariamente em diagnóstico.

## Consequências

- Positivo: item 1 resolve um blind spot real em produção com mudança mínima (2 linhas)
- Positivo: item 2 documenta o risco e a solução futura sem introduzir complexidade agora
- Negativo: o usuário final ainda não recebe resposta quando a background task falha por razão
  não coberta pelo retry da IA — comportamento aceitável (Meta vai retentar)
- Risco residual: se a Meta retentar e a deduplicação (`_ja_processada`) tiver expirado (>20min),
  a mensagem pode ser reprocessada — comportamento aceitável

## Alternativas consideradas

- **Resposta fallback ao usuário em caso de falha de background task**: impossível —
  o 200 OK já foi retornado quando a background task roda; não há mecanismo de retroativo
- **Fila de mensagens com dead-letter queue (RabbitMQ/SQS)**: rejeitado — infraestrutura
  não justificada para o volume atual; a Meta já tem retry nativo
- **`asyncio.create_task` em vez de `BackgroundTasks`**: o endpoint já é `async` mas a
  background task chama código blocking (SQLAlchemy sync, `_lock_do_telefone` com threading);
  misturar asyncio e blocking sem `run_in_executor` introduziria mais problemas
