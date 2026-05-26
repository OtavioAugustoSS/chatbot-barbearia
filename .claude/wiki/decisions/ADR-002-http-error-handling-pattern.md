# ADR-002: Padrão de Tratamento de Erros HTTP
Status: aceito
Data: 2026-05-21
Decisor: architect-agent
Stakeholders consultados: backend-agent (código existente como fonte de verdade)

## Contexto

O projeto não documentou formalmente como os endpoints devem retornar erros HTTP. A análise de `api/admin.py` e `api/webhook.py` revela um padrão consistente já emergido organicamente que precisa ser formalizado para guiar novos endpoints.

## Decisão

### Padrão de erros nos endpoints admin (FastAPI HTTPException)

| Situação | Status code | Exemplo de uso |
|---|---|---|
| Recurso não encontrado | 404 | `raise HTTPException(404, "Cliente não encontrado")` |
| Autenticação inválida | 401 | Login com credenciais erradas |
| Sem permissão | 403 | Atendente tenta editar nota de outro |
| Conflito de estado | 409 | Dois atendentes tentam assumir mesma conversa |
| Validação de negócio | 400 | `snoozed_until` no passado, self-desativar conta |
| Rate limit | 429 | Excesso de tentativas de login |
| Config ausente | 503 | `JWT_SECRET` não configurado no ambiente |

### Regra de formato de detail
- Strings em português (PT-BR) — dashboard é em PT-BR
- Sem stack trace no `detail` — jamais vazar informações internas
- Mensagem descritiva o suficiente para o frontend exibir sem tratamento adicional
- Exceção: erros 4xx genéricos de validação Pydantic são gerados automaticamente pelo FastAPI com formato padrão

### Endpoint webhook (`api/webhook.py`)
- **Nunca lança HTTPException 5xx** — sempre retorna `{"status": "ok"}` com 200
- Exceção: 403 para assinatura HMAC inválida e erro de verificação de token
- Racional: Meta retransmite qualquer resposta não-2xx causando loop de duplicatas
- Erros internos são absorvidos silenciosamente e logados com `log.exception()`

### Background tasks
- Erros em `_processar_mensagem` não propagam para o webhook (são isolados pela background task)
- O bloco `try/finally` garante `db.close()` mesmo em exceção não capturada

### Logging de erros
- `log.exception()` para erros inesperados (inclui stack trace no log)
- `log.error()` para erros esperados mas graves (ex: assinatura inválida)
- `log.warning()` para degradações esperadas (ex: rate limit, fallback de UI)
- `log.info()` para eventos de negócio relevantes (login OK, bot reativado)

### Validação de negócio vs. validação de schema
- Pydantic valida schema (tipos, tamanhos, regex de formato): retorna 422 automático
- Código Python valida regras de negócio (ownership, conflito de estado): HTTPException manual

## Consequências

- Positivo: formaliza o padrão já praticado — todos os novos endpoints seguem o mesmo contrato
- Positivo: frontend sabe que `detail` é sempre string PT-BR segura para exibir ao operador
- Negativo: sem biblioteca de erros estruturados — detail é string livre, não JSON tipado
- Risco: endpoints admin novos podem introduzir 500 sem querer se exceção não for capturada — FastAPI captura automaticamente e retorna 500, mas sem mensagem útil. Padrão recomendado: usar `try/except` em operações de banco em endpoints críticos

## Alternativas consideradas

- Retornar envelope `{"error": {"code": "...", "message": "..."}}` em vez de string plain: rejeitado por overhead sem benefício — apenas o dashboard consome esses erros, não uma API pública
- Usar `HTTPException` com `headers` adicionais: não necessário no estado atual
