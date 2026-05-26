# AI Quality Audit — 2026-05-21

Auditoria completa da camada de IA e pre-processing layers.
Executada por: backend-agent | Task: FASE1-AUDIT

---

## Tabela de Problemas

| # | Problema | Severidade | Arquivo(s) | Linha(s) | Fix Proposto |
|---|---|---|---|---|---|
| 1 | **JSON Parse sem recuperação robusta** — o arquivo `erro_ia_debug.txt` contém `'\n  "intencao"'`, confirmando que o modelo retornou JSON com newline escapado (`\n`) dentro da chave. O parse atual usa `json.loads()` direto; o único pré-processamento é strip de fences ` ```json ```. Não há tentativa de recuperação via `re.search(r'\{.*\}', ..., re.DOTALL)` antes de falhar para `transbordo_falha`. | CRÍTICO | `services/ai_service.py` | 311–319 | Antes de `json.loads()`, tentar extração de objeto JSON via regex `re.search(r'\{[^{}]*\}', text, re.DOTALL)` como segunda chance. Também tentar `text.replace('\\n', ' ')` para sanitizar escapes inválidos nas keys. |
| 2 | **Booking regex não cobre frases naturais comuns** — expressões como "reserva confirmada", "já deixei marcado pra você", "pode ir que já está marcado", "vou deixar reservado" NÃO casam com `_REGEX_AGENDAMENTO_PROIBIDO`. O regex cobre apenas primeira pessoa ("marquei", "agendei", "reservei", "confirmei seu horário") ou construções muito específicas. Variações passivas, participio e variações coloquiais escapam. | ALTO | `services/ai_service.py` | 23–28 | Ampliar regex com: `reserva\s+confirmada`, `j[aá]\s+(deixei\s+)?marcad[ao]`, `j[aá]\s+est[aá]\s+(marcad|agendad|confirmad|reservad)`, `pode\s+ir` + contexto de agendamento, `vou\s+deixar\s+(marcad|reservad|agendad)`, `ficou\s+(marcad|agendad|confirmad)`. |
| 3 | **Anti-drift threshold alto demais** — o anchor `ANCORA_ANTI_DRIFT` só é injetado em `>= 6` mensagens. Dado que o contexto IA usa apenas as últimas 15 mensagens, drift já pode ocorrer a partir da 4ª troca, especialmente em conversas sobre disponibilidade onde o modelo tende a prometer agendamento. | MÉDIO | `services/ai_service.py` | 298 | Reduzir threshold para `>= 4`. A âncora é curta (~200 tokens) e o custo de injetá-la 2 turnos mais cedo é desprezível vs. o risco de resposta errada. |
| 4 | **Service description leakage via `\| ref:`** — o formato injetado é `✂️ Nome — R$ X  \| ref: dura Ymin; desc: Z`. O system prompt instrui explicitamente (regra 3 e ANCORA_ANTI_DRIFT) a NÃO incluir campos após `\| ref:` em listas. Porém a instrução não é visível no `_construir_contexto_temporal()` nem no `modo_msg`. Em conversas longas com drift, o LLM pode copiar literalmente o pipe e o campo `ref:` para a resposta. Não há sanitização no output antes de enviar. | MÉDIO | `services/ai_service.py` | 185–193 / `core/prompts.py` | 73–74 | Adicionar sanitização pós-validação: `re.sub(r'\s*\|\s*ref:[^<\n]*', '', resposta)` em `_validar_resposta()`. Isso garante que mesmo em caso de drift o `\| ref:` nunca chegue ao cliente. |
| 5 | **Canonical gap: "qual o horário aí?"** — a query "qual o horário aí?" NÃO casa com o regex de horários porque o token `aí` não é parte do padrão. O padrão exige `\bhor[aá]rio(s)?\b` que casa com "horário" como termo isolado, mas o regex não usa `re.search()` com contexto amplo suficiente — especificamente "qual o horário aí" tem o token `hor[aá]rio` e DEVERIA casar, mas `aí` após o ponto final do regex pode não ser problema. **Confirmação:** O padrão `\bhor[aá]rio(s)?\b` com `re.search()` SIM casa com "qual o horário aí?" porque `horário` está na string. Não é bug. | BAIXO | `core/respostas_canonicas.py` | 130–141 | Não requer fix — já funciona. Registrado para clareza. |
| 6 | **Canonical gap: "o Fred tá lá hoje?"** — NÃO tem match canônico. Vai para IA. A IA deve tratar via regra 11 do system prompt (só dar contato se pedir explicitamente pelo Fred). Porém a pergunta é sobre disponibilidade/presença, não sobre contato. Risco: IA pode confundir e dar o telefone sem ser pedido, ou dar resposta confusa. | MÉDIO | `core/respostas_canonicas.py` | — | Adicionar padrão canônico para "o Fred tá lá / está hoje / está disponível" → resposta: "Não temos informação sobre disponibilidade em tempo real de profissionais. Para agendar com o Fred, acesse: {LINK_APPBARBER}" |
| 7 | **Canonical gap: "quero falar com o dono / proprietário"** — NÃO tem match canônico. Vai para IA. O system prompt (regra 11) trata corretamente: não usa `chamar_recepcao`, dá telefone do Fred. Risco baixo mas desnecessário usar tokens. | BAIXO | `core/respostas_canonicas.py` | — | Adicionar padrão para `falar\s+com\s+(o\s+)?(dono|propriet[aá]rio|chefe\s+do\s+lugar)` → resposta canônica com telefone do Fred. Reduz custo e elimina variação estética. |
| 8 | **Canonical gap: "quanto custa o degradê?" / "quanto custa o fade?"** — NÃO tem match canônico. Correto não ter (são variações do serviço "Corte" cujo preço é dinâmico do banco). A IA via regra 5 mapeia corretamente para "Corte". Porém o price lookup é feito via IA com cache de 5min, não via DB direto. Aceitável. | BAIXO | Fluxo intencional | — | Não requer fix — design correto. Registrado para clareza. |
| 9 | **Canonical gap: "aceitam nubank?"** — NÃO tem match canônico exato. O padrão de pagamento cobre `aceitam?\s+(cart[aã]o|pix|dinheiro|d[eé]bito|cr[eé]dito)` mas NÃO cobre marcas específicas como "nubank", "picpay", "inter". Nubank é banco e cartão de débito/crédito; IA provavelmente responderá corretamente. Mas vai consumir tokens desnecessariamente. | BAIXO | `core/respostas_canonicas.py` | 175–185 | Adicionar ao padrão de pagamento: `nubank|picpay|mercado\s+pago|inter\s+bank|itau|bradesco|santander` como sub-padrão de marcas, respondendo com RESPOSTA_PAGAMENTO genérica. |
| 10 | **Canonical gap: "tem acesso pra deficiente?"** — NÃO tem match canônico direto. O padrão de estrutura cobre `cadeirante` e `acessibilidade`. A query "deficiente" não está coberta. Vai para IA. | BAIXO | `core/respostas_canonicas.py` | 202–215 | Adicionar `deficiente(s)?|pcd|pessoa\s+(com\s+)?defici[eê]ncia` ao padrão de estrutura. |
| 11 | **Pre-AI pipeline: menu items processados dentro da background task** — `_despachar_menu_principal()` e `_despachar_subfluxo()` são chamados dentro de `_processar_mensagem()` que roda dentro de `tarefa_em_segundo_plano_ia()`. Isso significa que mesmo itens de menu puramente determinísticos (sem IA) ficam aguardando o lock do telefone. Se a IA estiver processando uma mensagem anterior, um clique de menu fica bloqueado pelo lock por até 30s. | MÉDIO | `api/webhook.py` | 953–957 / 1006–1013 | Detectar MENU_IDs e SUB_IDs em `receive_message()` ANTES de enfileirar background task, e despachar síncronos (ou numa task separada sem lock). Handoffs já são tratados síncronos como referência. |
| 12 | **Temporal context: DB query por chamada IA** — `_construir_contexto_temporal()` chama `_carregar_horarios_db()` que abre uma nova `SessionLocal()` a cada invocação IA. Sem cache, em 100 msgs/min isso são 100 queries extras ao banco só para horários. O cache de serviços/barbeiros existe mas não cobre horários. | BAIXO | `services/ai_service.py` | 95–157 | Adicionar cache TTL para `_carregar_horarios_db()` similar ao cache de serviços (5-min). Um dict de módulo `_cache_horarios = {"data": None, "expira_em": 0.0}` resolve. |
| 13 | **`response_format: json_object` vs. JSON com newline escapado em key** — a API NVIDIA NIM com `response_format={"type": "json_object"}` deveria retornar JSON válido, mas o erro no log (`'\n  "intencao"'`) indica que o modelo retornou texto com newlines ANTES das keys (pretty-printed JSON). O pré-processamento atual faz só strip das fences, não normaliza pretty-print. O `json.loads()` suporta pretty-print normalmente, mas o erro logado é `'\n  "intencao"'` como mensagem de JSONDecodeError, o que sugere que o texto começou com `\n  "intencao"` (sem `{` de abertura) ou que houve conteúdo extra antes do JSON. | CRÍTICO | `services/ai_service.py` | 308–319 | Adicionar regex fallback: após strip de fences, tentar `match = re.search(r'\{.*\}', text, re.DOTALL)` e se encontrar usar `match.group(0)`. Isso recupera JSON embutido em texto livre. |
| 14 | **Histórico injetado na IA com `role: "model"`** — em `_processar_mensagem()` linha 1001, mensagens do bot são salvas com `role: "model"` no histórico. Em `ai_service.py` linha 293, o mapeamento é `role = "assistant" if msg.get("role") in ["bot", "model", "assistant"] else "user"`. Funciona, mas `"model"` é string atípica do protocolo OpenAI (que usa `"assistant"`). Não é bug operacional mas é smell de inconsistência. | BAIXO | `api/webhook.py` / `services/ai_service.py` | 1001 / 293 | Normalizar para `"assistant"` na gravação do histórico ou garantir que o mapeamento continue cobrindo `"model"`. |

---

## Detalhamento — Seção A: JSON Fragility

### Erro confirmado em `erro_ia_debug.txt`
```
[ERRO AI SERVICE NVIDIA] '\n  "intencao"'
```

Isso é a mensagem de `json.JSONDecodeError` que diz que o token inesperado era `\n  "intencao"`. Dois cenários possíveis:

**Cenário 1 (mais provável):** O modelo retornou o JSON como pretty-printed mas sem a chave de abertura `{` — i.e., retornou algo como:
```
\n  "intencao": "tirar_duvida",\n  "resposta_sugerida": "..."
```
O `json.loads()` falha porque o texto não começa com `{`.

**Cenário 2:** O modelo retornou texto livre seguido de JSON, e após o strip de fences, `json.loads()` encontrou texto antes do `{`.

**Recuperação atual:** Nenhuma. Qualquer falha de parse = `transbordo_falha` = handoff indesejado ou mensagem de erro ao cliente.

**Formatos malformados que NÃO são recuperados atualmente:**
1. Pretty-printed sem `{` inicial (erro confirmado)
2. JSON seguido de explicação em texto: `{"intencao": "tirar_duvida", ...} Aqui está minha resposta.`
3. JSON dentro de markdown sem fence: `Resposta: {"intencao": ...}`
4. JSON com trailing comma: `{"intencao": "tirar_duvida",}`
5. JSON com chave duplicada (Python ignora, mas é indicativo de drift)
6. Texto com múltiplos objetos JSON: `{"a":1} {"b":2}`
7. JSON com BOM (byte order mark) UTF-8 no início

---

## Detalhamento — Seção B: Booking Promise Regex

Regex atual:
```python
r"\b(marquei|agendei|reservei|confirmei seu? hor[aá]rio|seu hor[aá]rio (est[aá]|foi) (marcado|agendado|confirmado|reservado)|"
r"j[aá] (marquei|agendei|reservei)|posso (marcar|agendar|reservar) (para|pra) (voc[eê]|ti)|"
r"vou (marcar|agendar|reservar) (para|pra) (voc[eê]|ti))\b"
```

| Frase de teste | Bloqueada? | Motivo |
|---|---|---|
| "seu agendamento foi realizado com sucesso" | NÃO | Nenhum token do regex casa. "agendamento" não está no regex, "realizado" não está. |
| "reserva confirmada" | NÃO | "reserva" (substantivo) não está; "reservei" (verbo) está mas não "reserva". |
| "já deixei marcado pra você" | NÃO | Não cobre "deixei marcado". |
| "pode ir que já está marcado" | NÃO | Não cobre "está marcado" isolado. |
| "vou deixar reservado" | NÃO | "vou deixar" não está; só "vou reservar". |
| "marquei para você" | SIM | "marquei" casa diretamente. |
| "agendei para você" | SIM | "agendei" casa diretamente. |
| "confirmei seu horário" | SIM | "confirmei seu? horário" casa. |

**4 de 5 frases perigosas escapam ao regex atual.**

---

## Detalhamento — Seção C: Anti-Drift Anchor

Threshold atual: `len(historico_mensagens) >= 6` (linha 298 de `ai_service.py`).

O contexto IA usa últimas 15 mensagens. Em 4 trocas (8 mensagens user+bot), o modelo já tem material suficiente para começar a diluir regras. Conversas sobre disponibilidade/agendamento são as mais suscetíveis: cliente insiste, bot redireciona, cliente insiste de novo — após 4 trocas o modelo pode ceder.

Recomendação: threshold `>= 4` (injetar âncora quando houver 4+ mensagens no histórico enviado para IA, ou seja, 2+ turnos de conversa).

---

## Detalhamento — Seção D: Service Description Leakage

Formato injetado (linha 188–193):
```
✂️ Corte de Cabelo — R$ 50.00  | ref: dura 30min; desc: Corte de cabelo no estilo...
```

O system prompt proíbe explicitamente usar campos após `| ref:` em listas (regra 3, linha 74) e a `ANCORA_ANTI_DRIFT` reforça isso. Proteção em dois lugares.

Porém, não há sanitização no output antes de enviar ao cliente. Se o modelo fizer drift, `| ref: dura 30min` chegará ao WhatsApp. A proteção é apenas instrucional (no prompt), não técnica (no código).

Fix: sanitização técnica em `_validar_resposta()`:
```python
resposta = re.sub(r'\s*\|\s*ref:[^\n<]*', '', resposta)
```

---

## Detalhamento — Seção F: Pre-AI Pipeline Order

Ordem atual em `receive_message()`:
1. Validação assinatura HMAC
2. Dedupe (message_id)
3. Mídia check (MÍDIA_ prefix)
4. Rate limit
5. Upsert usuário
6. Reabertura status (snoozed/resolved)
7. `!reiniciar` command
8. Auto-reativação bot
9. Handoff buttons (síncronos)
10. Background task → dentro desta: menu dispatch, sub-fluxo, primeiro contato, menu request, saudação pura, canonical FAQ, IA

**Problemas de ordem:**
- Menu items (MENU_*, SUB_*) estão dentro da background task aguardando lock. Se IA estiver processando mensagem anterior, clique de menu fica bloqueado. Handoffs (item 9) são síncronos antes do enfileiramento — mesma lógica deveria se aplicar a menus determinísticos.
- O rate limit (item 4) acontece ANTES do upsert do usuário (item 5). Se o telefone não existe ainda (primeiro contato), rate limit é avaliado antes de criar o usuario. Isso é correto e intencional (evita criar usuário de flood), mas merece nota.

**Casos edge que "furam" para IA com input inválido:**
- Mensagem vazia string `""`: `extrair_informacoes_mensagem` pode retornar texto vazio; o check `if not telefone or not texto_cliente` pega isso em `receive_message`. Seguro.
- Mensagem com apenas espaços `"   "`: after strip em `_e_saudacao_pura`, len <= 60 e o regex `^[\s,!?.]*...$` pode ou não casar. Se não casar, chega na IA com `"   "` como `mensagem_atual`. Baixo risco mas possível.
- Muito longa (> 4096 chars): sem truncagem antes de enviar para IA. Pode aumentar tokens e latência.

---

## Detalhamento — Seção G: Temporal Context

`_construir_contexto_temporal()` é chamado dentro de `processar_intencao()` a cada chamada de IA (linha 265). Ele chama `_carregar_horarios_db()` que abre nova `SessionLocal()`. Sem cache para horários, cada mensagem que chega à IA = 1 query extra ao banco.

Risco de inconsistência: baixo. A hora é lida de `datetime.now(_TZ_BR)` a cada chamada, que é o comportamento desejado. O único risco seria se a sessão de banco falhar silenciosamente — mas já há `try/except` com fallback para dict hardcoded.
