# Multi-Agent Workflow — Barbearia Bolshoi

## Arquitetura

Claude principal é o coordenador e entry point. Dois modos de operação:

| Modo | Quando usar | Como |
|------|-------------|------|
| **Standalone** | 1-2 agentes, tarefa simples | `Agent(subagent_type=...)` sequencial |
| **Time** | 3+ agentes, feature complexa, ciclos | `TeamCreate` + `Agent(name=..., run_in_background=True)` |

---

## Grafo de Comunicação

```
Claude principal
      │ inicia fluxo
      ▼
  po-agent ──────────────────────→ dev-agent   (aprovação + restrições)
                ↘                 ↗
               db-agent ─────────            (se schema muda: po-agent pede, db entrega ao dev)

  dev-agent ──────────────────────→ qa-agent   (implementação concluída)
  dev-agent ──────────────────────→ prompt-engineer  (se bug de IA encontrado)

  qa-agent  ──→ dev-agent          (FAIL: dev precisa corrigir)
  qa-agent  ──→ prompt-engineer    (problema de comportamento da IA)
  qa-agent  ──→ Claude principal   (PASS/FINAL: veredicto final)

  prompt-engineer ────────────────→ qa-agent   (otimização concluída)
```

Regra: **cada agente sabe quem é seu upstream (quem o aciona) e seu downstream (quem ele aciona).**

---

## Modo Standalone (sequencial, Claude coordena)

Usado para tarefas simples onde Claude principal lê cada resultado e passa para o próximo.

```python
# Bug fix simples
resultado_dev = Agent(subagent_type="dev-agent", prompt="...")
resultado_qa  = Agent(subagent_type="qa-agent",  prompt=f"...{resultado_dev}...")

# Feature com validação
resultado_po  = Agent(subagent_type="po-agent",  prompt="...")
resultado_dev = Agent(subagent_type="dev-agent", prompt=f"PO disse: {resultado_po}. Implemente...")
resultado_qa  = Agent(subagent_type="qa-agent",  prompt=f"Dev fez: {resultado_dev}. Revise...")
```

Cada agente escreve handoff em `.claude/handoff-context.md`. Próximo lê antes de iniciar.

---

## Modo Time (paralelo, agentes se comunicam diretamente)

Usado para features complexas onde agentes precisam trocar mensagens sem esperar Claude principal.

### REGRA CRÍTICA DE TIMING

**Agents não fazem wait loop.** Um agent spawned com tarefa "aguarde mensagens" vai idle imediatamente se a mailbox estiver vazia. SendMessage que chega depois NÃO acorda agent idle automaticamente.

**Anti-padrão (QUEBRADO):**
```python
# ERRADO: QA vai idle antes de po/dev terminarem
Agent(name="qa", prompt="Aguarde mensagens de po e dev...")  # idle imediato
Agent(name="po", ...)  # termina depois — SendMessage para qa que está dormindo
Agent(name="dev", ...)  # idem
```

### Padrão A — Cadeia (sequencial, mais robusto)

Cada agent acorda o próximo via SendMessage só após concluir. Nenhuma race condition.

```python
TeamCreate(name="feat-nome")

# Apenas po e dev em paralelo (fazem trabalho independente)
Agent(name="po", run_in_background=True,
      prompt="[analise]. Depois: SendMessage({to:'dev', ...})")
Agent(name="dev", run_in_background=True,
      prompt="[implemente]. Aguarda mensagem do po. Depois: SendMessage({to:'qa', ...})")

# qa é spawned pelo dev via SendMessage — ou Claude spawna após dev concluir
# QA sempre recebe contexto completo no prompt ou via mensagem de quem o acionou
```

### Padrão B — Paralelo com funil no team-lead (auditorias, reviews)

Quando múltiplos agents fazem trabalho independente e um deve consolidar:

```python
TeamCreate(name="audit-X")

# po e dev trabalham em paralelo, ambos reportam ao team-lead
Agent(name="po", run_in_background=True,
      prompt="[analise]. Depois: SendMessage({to:'team-lead@audit-X', ...})")
Agent(name="dev", run_in_background=True,
      prompt="[analise técnica]. Depois: SendMessage({to:'team-lead@audit-X', ...})")

# Claude principal recebe ambos via notificação de idle
# Depois spawna QA com TODO o contexto no prompt inicial (sem depender de mailbox)
Agent(name="qa", run_in_background=True,
      prompt=f"Contexto po: {resultado_po}. Contexto dev: {resultado_dev}. Consolide e emita veredicto.")
```

### Padrão C — QA com trabalho próprio (quando precisa ser spawned junto)

Se QA precisa ser spawned em paralelo, deve ter trabalho independente suficiente para durar enquanto po/dev terminam:

```python
Agent(name="qa", run_in_background=True,
      prompt="""
      FASE 1 (seu trabalho independente): Leia [arquivos] e forme sua própria análise.
      FASE 2 (após completar fase 1): Verifique mailbox — mensagens de po e dev devem ter chegado.
      Consolide fase 1 + mensagens recebidas e emita veredicto.
      Envie resultado: SendMessage({to:'team-lead@...'})
      """)
```

### Criando o time

```python
# 1. Criar contexto do time
TeamCreate(name="feat-nome-da-feature")

# 2. Spawnar agentes respeitando padrão de timing correto (A, B ou C acima)
```

### Protocolo SendMessage entre agentes

Todo agente ao enviar para outro usa este formato:

```
FROM: [nome-do-agente]
STATUS: DONE | BLOCKED | NEED_INPUT
RESULT: [resumo do que foi feito/decidido]
FILES_MODIFIED: [lista ou "nenhum"]
RESTRICTIONS: [restrições para o receptor respeitar]
NEXT: [o que o receptor deve fazer]
```

Para usar SendMessage, o agente deve primeiro carregar o schema:
```
1. ToolSearch({query: "select:SendMessage"})
2. SendMessage({to: "[nome-do-agente]", message: "..."})
```

### Quem envia para quem (time)

| De | Para | Quando |
|----|------|--------|
| po-agent | dev | Aprovação/rejeição concluída |
| po-agent | db | Se schema precisa mudar (cc dev) |
| db-agent | dev | Migration pronta |
| dev-agent | qa | Implementação concluída |
| dev-agent | prompt-engineer | Bug de comportamento da IA identificado |
| qa-agent | dev | FAIL — correções necessárias |
| qa-agent | prompt-engineer | Problema de IA identificado |
| qa-agent | orchestrator (Claude principal) | PASS — veredicto final |
| prompt-engineer | qa | Otimização concluída |

---

## Fluxos por Tipo de Tarefa

### Feature nova com impacto no cliente
```
po-agent → dev-agent → [db-agent →] qa-agent
```
1. po-agent valida regras de negócio
2. dev-agent implementa (com restrições do PO)
3. [se schema muda] db-agent cria migration → dev-agent aplica
4. qa-agent revisa → veredicto

### Bug técnico (sem impacto no cliente)
```
dev-agent → qa-agent
```

### Problema de IA (alucinação, tom errado, JSON inválido)
```
po-agent → prompt-engineer → qa-agent
```
1. po-agent confirma comportamento esperado
2. prompt-engineer diagnostica e corrige
3. qa-agent valida

### Auditoria paralela
```
po-agent + prompt-engineer (paralelos) → SendMessage("team-lead") → Claude spawna qa com contexto completo
```
Po e prompt-engineer trabalham em paralelo, ambos enviam para `team-lead`. Claude principal recebe resultados e spawna qa COM o contexto completo no prompt — qa nunca depende de mailbox vazia.

---

## Quando Invocar Cada Agente

| Agente | Invocar quando | NÃO invocar quando |
|--------|---------------|-------------------|
| `po-agent` | Mudança com impacto no cliente | Bug técnico puro |
| `dev-agent` | Qualquer implementação de código | — |
| `qa-agent` | Após qualquer implementação | — (sempre usar) |
| `db-agent` | ADD/ALTER/DROP/RENAME no schema MySQL | Só muda lógica Python |
| `prompt-engineer` | Problema de comportamento da IA | Bug de código puro |

---

## Handoff Context (Modo Standalone)

Arquivo: `.claude/handoff-context.md`

Formato que cada agente escreve ao terminar:
```markdown
## Handoff: [agente] → [próximo]
**Resultado**: [decisão ou o que foi implementado]
**Restrições**: [o que o próximo deve respeitar]
**Arquivos modificados**: [lista ou "nenhum"]
**Edge cases para QA**: [lista]
```

---

## Estado das Tarefas

Arquivo permanente: `.claude/AGENT_STATE.md`

```
| TASK-XXX | status | último-agente | QA-verdict | data | resumo |
```
- Status: `pending` | `in_progress` | `done` | `blocked`
- QA: `PASS` | `FAIL` | `PASS_WITH_NOTES`

---

## Agentes

| Agente | subagent_type | Modelo | Papel |
|--------|---------------|--------|-------|
| po-agent | po-agent | claude-opus-4-7 | Regras de negócio |
| dev-agent | dev-agent | claude-sonnet-4-6 | Implementação |
| qa-agent | qa-agent | claude-sonnet-4-6 | Qualidade |
| db-agent | db-agent | claude-haiku-4-5-20251001 | Migrations SQL |
| prompt-engineer | prompt-engineer | claude-opus-4-7 | Comportamento IA |

Working dir: `C:\Users\Home\.vscode\chatbot-barbearia`
