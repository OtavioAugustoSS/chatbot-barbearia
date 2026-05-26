# BR-003: Formatacao de Mensagens — IA usa `<br>`, Operador usa `\n`

Data: 2026-05-21
Stakeholders: product-owner-agent (FASE 3 — formalização de regra hardcoded preexistente)

## Contexto

A Meta WhatsApp Cloud API renderiza quebras de linha de forma diferente dependendo da origem da mensagem. Quando o texto vem de JSON (respostas da IA), `\n` não é renderizado corretamente pelo WhatsApp. A solução adotada é usar a tag `<br>` no JSON, que é convertida para newline real pela função `_normalizar_texto_envio()` antes do envio à API. Mensagens digitadas diretamente por operadores humanos no dashboard já chegam como texto puro e usam `\n` diretamente, sem passar pela camada de conversão da IA.

Misturar os dois sistemas produz quebras de linha duplas, ausentes ou literais `<br>` visíveis no chat do cliente.

## Regra

### Regra A — Respostas da IA e canônicas

Todas as respostas geradas pela IA ou pelas respostas canônicas de `core/respostas_canonicas.py` DEVEM usar `<br>` como marcador de quebra de linha.

Uso correto de `<br>`:
- UM `<br>` antes de cada item de lista
- DOIS `<br><br>` entre parágrafos ou blocos de assunto diferente
- DOIS `<br><br>` antes da frase final de encerramento de uma lista
- ZERO `<br>` em respostas curtas de uma única frase

Negrito no WhatsApp: UM asterisco (`*texto*`). Nunca dois asteriscos (`**texto**`).

### Regra B — Mensagens de operador humano

Mensagens enviadas via `POST /admin/enviar/{telefone}` usam `\n` diretamente. O endpoint recebe o texto como digitado pelo atendente e envia sem conversão de `<br>`.

### Regra C — Conversão na camada de envio

A função `_normalizar_texto_envio()` em `api/webhook.py` realiza:
1. Converte `<br>` e `\n` para newline real (`\n`)
2. Colapsa 3+ newlines consecutivos para no máximo 2

Esta conversão ocorre APENAS para mensagens do bot (IA + canônicas). Mensagens de operador passam diretamente para `services/whatsapp.py` sem normalização.

## Implementação em código

- **System prompt** (`core/prompts.py`, seção "REGRA DE FORMATAÇÃO CRITICA"): instrução explícita para a IA usar `<br>`, com exemplos de quando usar um vs dois `<br>`.
- **`core/respostas_canonicas.py`**: todas as constantes de resposta usam `<br>` nativamente.
- **`api/webhook.py`**, `_normalizar_texto_envio()`: conversão de `<br>` para newline antes do envio.
- **`api/admin.py`**, endpoint `enviar`: usa `\n` direto, sem camada de conversão.
- **ANCORA_ANTI_DRIFT** (`core/prompts.py`): reforça "Os campos após `| ref:` no banco injetado são REFERÊNCIA INTERNA — não copie em listas" (evita vazamento de formato interno do banco para o cliente).

## Exceções

Nenhuma. A separação `<br>` (IA/canônicas) vs `\n` (operador) é estrutural e não deve ser mesclada em nenhuma circunstância.

## Impacto em código

- Qualquer nova canônica adicionada a `core/respostas_canonicas.py` DEVE usar `<br>`, nunca `\n`.
- Qualquer novo endpoint de envio de mensagem pelo operador DEVE usar `\n` direto, nunca `<br>`.
- Testes de integração devem verificar que `_normalizar_texto_envio()` converte corretamente e não duplica newlines.
