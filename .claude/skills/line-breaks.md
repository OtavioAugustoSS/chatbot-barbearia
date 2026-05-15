---
name: line-breaks
description: Audita e corrige o sistema de quebra de linha do chatbot. Invoque quando respostas da IA aparecerem com formatação incorreta no WhatsApp, quando `<br>` aparecer literal no chat, quando o bot usar `\n` em vez de `<br>`, ou antes de qualquer mudança em `api/webhook.py`, `services/whatsapp.py`, `core/prompts.py` ou `core/respostas_canonicas.py`.
---

Você é o especialista em formatação de texto do chatbot Barbearia Bolshoi. Sua função é garantir que o sistema de quebra de linha esteja correto em todas as camadas.

---

## O Sistema de Quebra de Linha (estado correto)

### Regra fundamental

**A IA gera `<br>`. O código converte para `\n` antes de enviar ao WhatsApp.**

O WhatsApp renderiza `\n` como quebra de linha visível. NÃO renderiza `<br>` (enviaria o texto literal `<br>`).

---

## Pipeline Completo (do correto ao incorreto)

### Camada 1 — System Prompt (`core/prompts.py`)

A IA é instruída a usar `<br>` em toda quebra de linha:

```
# REGRA DE FORMATAÇÃO (CRÍTICA)
O WhatsApp não renderiza `\n` corretamente quando o texto vem de JSON.
Por isso você DEVE usar a tag literal `<br>` em todo lugar que quiser uma quebra de linha.
```

**Regras de uso do `<br>` na IA:**
- `<br>` — entre itens de lista (um por item)
- `<br><br>` — entre parágrafos ou antes da frase de encerramento
- Sem `<br>` — em respostas curtas de frase única

**Negrito:** `*texto*` (UM asterisco). `**texto**` NÃO funciona no WhatsApp.

### Camada 2 — Normalização (`api/webhook.py`)

```python
def _normalizar_texto_envio(texto: str) -> str:
    t = re.sub(r"<\s*br\s*/?\s*>", "\n", texto, flags=re.IGNORECASE)  # <br> → \n
    t = t.replace("\\n", "\n")   # literal \n escapado (JSON malformado) → \n real
    return re.sub(r"\n{3,}", "\n\n", t).strip()  # colapsa 3+ quebras → 2
```

Esta função DEVE ser chamada em TODA mensagem saindo para o WhatsApp via `_enviar_e_registrar`.

### Camada 3 — Mensagens fixas (`api/webhook.py`)

Mensagens fixas (boas-vindas, menu, saudação) são definidas em Python com `\n`:

```python
MENSAGEM_BOAS_VINDAS = "Olá! ...\n\nComo posso ajudar?"
```

Antes de passar para `_enviar_e_registrar`, são convertidas:
```python
_enviar_e_registrar(db, user, texto, MENSAGEM_BOAS_VINDAS.replace("\n", "<br>"), ...)
```

O ciclo completo: `\n` → `.replace("\n", "<br>")` → `<br>` → `_normalizar_texto_envio` → `\n` → WhatsApp.

Parece redundante, mas é intencional: `_enviar_e_registrar` sempre recebe texto com `<br>`, normaliza para `\n`, e envia.

### Camada 4 — Histórico injetado na IA (`api/webhook.py`, linha ~393)

```python
contexto_mensagens.append({
    "role": "model",
    "content": h.resposta_bot.replace("<br>", "\n")
})
```

O histórico é injetado com `\n` (não `<br>`) para que a IA veja texto limpo sem tags HTML.

**⚠️ RISCO DE DRIFT:** A IA vê histórico com `\n`, mas o prompt diz para usar `<br>`. Em conversas longas (≥6 turnos), o modelo pode começar a imitar o histórico e usar `\n` em vez de `<br>`. A âncora anti-drift em `ANCORA_ANTI_DRIFT` existe exatamente para combater isso.

### Camada 5 — Respostas canônicas (`core/respostas_canonicas.py`)

Respostas canônicas (FAQ zero-custo) devem usar `<br>` — elas passam por `_enviar_e_registrar` que chama `_normalizar_texto_envio`.

---

## Bugs Conhecidos (estado atual — 2026-05-14)

### BUG 1 — Mensagem "⏳ Processando" bypassa guards (`api/webhook.py`)

```python
# ERRADO — enviado ANTES do background task, fora de qualquer guard
try:
    whatsapp.enviar_mensagem_texto(telefone, "⏳ Processando sua mensagem...")
except Exception:
    pass
background_tasks.add_task(tarefa_em_segundo_plano_ia, telefone, texto_cliente)
```

**Problema:** Enviado antes de verificar `bot_ativo`, dedup, rate limit. Quebra o silêncio do bot quando `bot_ativo=False` (atendente humano). Também envia para mensagens duplicadas.

**Correção esperada:** Mover para dentro da `tarefa_em_segundo_plano_ia`, APÓS verificar `bot_ativo=True`.

### BUG 2 — Risco de drift de formato em conversas longas

A IA vê histórico com `\n` mas é instruída a usar `<br>`. Em conversas longas, pode começar a usar `\n`.

**Sintoma:** Usuário recebe mensagem com `\n` renderizado como quebra de linha (tecnicamente funciona no WhatsApp, mas inconsistente). Ou recebe `<br>` literal se algum código esqueceu de normalizar.

**Mitigação existente:** `ANCORA_ANTI_DRIFT` injetado em conversas ≥6 turnos.

**Correção esperada:** Adicionar explicitamente no `ANCORA_ANTI_DRIFT` um lembrete sobre `<br>`.

---

## Checklist de Auditoria

Execute antes de qualquer mudança em código de envio de mensagens:

- [ ] `_normalizar_texto_envio` é chamada em TODA mensagem saindo para Meta API?
- [ ] Nenhuma `whatsapp.enviar_mensagem_texto()` chamada direta (sem normalização) em código de negócio?
- [ ] Mensagens fixas usam `.replace("\n", "<br>")` antes de `_enviar_e_registrar`?
- [ ] Respostas canônicas em `respostas_canonicas.py` usam `<br>` (não `\n`)?
- [ ] `ANCORA_ANTI_DRIFT` menciona a regra do `<br>`?
- [ ] System prompt tem exemplos com `<br>` corretos?
- [ ] Mensagem "Processando" ou qualquer resposta imediata verifica `bot_ativo` primeiro?

---

## O que NUNCA fazer

- Nunca chamar `whatsapp.enviar_mensagem_texto()` com texto não normalizado em fluxo de negócio
- Nunca colocar `\n` direto em strings que a IA gera (a IA não deve usar `\n` — usa `<br>`)
- Nunca modificar `_normalizar_texto_envio` sem revisar TODOS os callers
- Nunca enviar mensagem automática antes de verificar `bot_ativo` e dedup

---

## Ao finalizar auditoria, escreva em `.claude/handoff-context.md`:

```markdown
## Handoff: line-breaks-skill → [próximo agente]
**Auditoria de quebra de linha**: PASS | FAIL
**Bugs encontrados**: [lista com localização arquivo:linha]
**Bugs já existentes (não introduzidos agora)**: [lista]
**O que precisa de correção**: [lista priorizada]
**Checklist**: [quantos itens passaram / total]
```
