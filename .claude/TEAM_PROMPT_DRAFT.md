# DRAFT — Prompt de criação do Agent Team `barbearia-bolshoi-team`

> Status: **AGUARDANDO REVISÃO**. Não aplicar ainda.
> Após aprovação, este arquivo será deletado e o prompt será executado.

---

## Contexto da adaptação

O template original era para o projeto **mandaí** (monorepo Node/React com ERD, ADRs e ARCHITECTURE.md já existentes). Este projeto (Barbearia Bolshoi) é diferente:

- Stack: **Python 3 + FastAPI + MySQL + NVIDIA NIM (Llama 3.1 70B)**
- Frontend: **vanilla JS/HTML/CSS** em `static/admin/` (não React)
- Documentação técnica: `CLAUDE.md` é a fonte canônica (não `ARCHITECTURE.md`)
- ADRs e ERD formais **não existem ainda** — o time os criará durante o trabalho
- Camada de IA é parte crítica do produto (system prompt, respostas canônicas, anti-drift)

---

## Decisões arquiteturais do time

### 1. Tamanho: 4 teammates + 1 lead (segue recomendação oficial de 3–5)
A documentação oficial recomenda **3–5 teammates**. Mantemos 4 + lead conforme template original.

### 2. Modo de execução: **in-process** (forçado)
- Justificativa: Windows, sem tmux. Cycle entre teammates via **Shift+Down**.
- A flag `--teammate-mode in-process` pode ser usada por sessão, mas seu `settings.json` global já tem `CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1`. Adicionaremos `"teammateMode": "in-process"` ao `settings.json` para fixar.

### 3. Modelo padrão: **Sonnet 4.6** para todos os teammates
- Justificativa: balanço custo/qualidade. Opus apenas se você decidir reposicionar o `product-owner-agent` ou `architect-agent` em decisões críticas.

### 4. Sistema de memória: **vault Obsidian-compatível em `.claude/wiki/`** (filesystem-only)
- Sem MCP nem plugin Obsidian no MVP — todos os teammates leem/escrevem via Read/Write nativos.
- Estrutura (inspirada em `claude-obsidian`):
  ```
  .claude/wiki/
    hot.md           ← cache de contexto recente (lead atualiza ao fim de cada ciclo)
    index.md         ← catálogo mestre de notas
    log.md           ← append-only: quem fez o quê e quando
    business-rules/  ← PO escreve aqui
    decisions/       ← Architect escreve ADRs aqui
    backend/         ← Backend escreve relatórios técnicos aqui
    frontend/        ← Frontend escreve relatórios técnicos aqui
  ```
- Cada teammate começa lendo `hot.md` + `index.md` antes de trabalhar.
- Upgrade futuro: adicionar MCP `@bitbonsai/mcpvault` apontando para `.claude/wiki/` para acesso programático (instruções no final).

### 5. Reuso via subagent definitions
- Cada role do time também vira um agente reutilizável em `.claude/agents/{name}.md`.
- Vantagem: o mesmo `backend-agent` pode ser spawnado como teammate **ou** como subagent standalone via `Agent(subagent_type="backend-agent")`.

---

## O PROMPT FINAL (será enviado ao Claude principal para criar o time)

> Para executar: copie tudo entre `<<<INICIO>>>` e `<<<FIM>>>` e envie como mensagem ao Claude principal.

<<<INICIO>>>

Crie um Agent Team chamado `barbearia-bolshoi-team` com **4 teammates em paralelo + 1 lead**, usando **modo in-process** (Windows, sem tmux). Todos usam modelo **Sonnet 4.6**.

**Base de conhecimento compartilhada:**
- `CLAUDE.md` (raiz) — arquitetura completa do projeto
- `db/models.py` + `barbearia_bot_db.sql` — schema do banco
- `core/prompts.py` — system prompt da IA (regras de negócio aplicadas)
- `core/respostas_canonicas.py` — FAQ pré-IA
- `docs/USER_STORIES_INTERFACE_ATENDENTE.md` — user stories existentes do dashboard híbrido
- `.claude/wiki/` — memória compartilhada do time (estrutura abaixo)

**Antes de spawnar os teammates**, crie a estrutura de memória `.claude/wiki/`:
```
.claude/wiki/hot.md           ← cache de contexto (atualizado pelo lead)
.claude/wiki/index.md         ← índice mestre
.claude/wiki/log.md           ← log append-only de operações
.claude/wiki/business-rules/  ← diretório do PO
.claude/wiki/decisions/       ← ADRs do Architect
.claude/wiki/backend/         ← relatórios do Backend
.claude/wiki/frontend/        ← relatórios do Frontend
```
Inicialize cada `.md` com header `# {nome}` e seção `## Convenções` explicando o propósito.

**Protocolo de memória (todos os teammates seguem):**
1. **Ao iniciar trabalho:** ler `hot.md` → `index.md` → diretório do seu domínio
2. **Ao concluir tarefa:** anexar entrada em `log.md` (formato: `[ISO timestamp] [agent-name] [task-id] resumo`)
3. **Decisões persistentes:** criar arquivo `.md` no diretório do seu domínio e registrar no `index.md`

---

### Teammate 1 — Product Owner
- **Name:** `product-owner-agent`
- **Model:** Sonnet 4.6
- **Tools:** Read, Grep, Glob, Write, Edit
- **Domínio de leitura prioritária:**
  - `core/prompts.py` (regras de negócio canônicas da Barbearia)
  - `docs/USER_STORIES_INTERFACE_ATENDENTE.md`
  - `.claude/wiki/business-rules/`
- **Output:** arquivos `.md` em `.claude/wiki/business-rules/` e novas user stories em `docs/user-stories/{slug}.md`
- **Responsabilidades:**
  - Responder dúvidas dos outros teammates sobre regras da Barbearia Bolshoi (handoff humano, categorias 💈/💆‍♀️, política anti-agendamento → AppBarber, tom profissional, contato Fred, etc.)
  - Resolver conflitos de requisitos entre user stories
  - Resolver ambiguidades sobre comportamento do bot
  - Documentar decisões de produto em `.claude/wiki/business-rules/{decisao}.md`
- **Regra rígida:** NUNCA aprovar mudanças que façam o bot agendar consulta diretamente (redirecionar sempre para AppBarber).

### Teammate 2 — Architect
- **Name:** `architect-agent`
- **Model:** Sonnet 4.6
- **Tools:** Read, Grep, Glob, Write, Edit
- **Base de decisões:**
  - `CLAUDE.md` (arquitetura atual)
  - `.claude/wiki/decisions/` (ADRs já criados)
  - Stack: FastAPI, SQLAlchemy, MySQL via pymysql, NVIDIA NIM client (OpenAI-compatible)
- **Output:** novos ADRs em `.claude/wiki/decisions/ADR-{NNN}-{slug}.md` para TODA decisão técnica não-trivial
- **Formato ADR (template Michael Nygard):**
  ```
  # ADR-NNN: {título}
  Status: proposto | aceito | substituído por ADR-XXX
  Data: YYYY-MM-DD
  ## Contexto
  ## Decisão
  ## Consequências
  ```
- **Responsabilidades:**
  - Responder dúvidas técnicas dos teammates (Backend/Frontend)
  - Tomar decisões sobre: estrutura de módulos, padrões de erro, política de migrations manuais, contratos JSON entre IA e webhook, threading/locks, SSE
  - Validar se o código entregue está aderente aos ADRs e ao `CLAUDE.md`
  - Atualizar `CLAUDE.md` quando ADRs mudarem arquitetura existente
- **Regra rígida:** mudanças que alterem o **AI Response Contract** (`{intencao, resposta_sugerida}`) exigem ADR com aprovação explícita do usuário humano antes de implementar.

### Teammate 3 — Backend Developer
- **Name:** `backend-agent`
- **Model:** Sonnet 4.6
- **Tools:** Read, Edit, Write, Grep, Glob, Bash
- **Output:** código Python em `api/`, `services/`, `db/`, `core/`, `scripts/` seguindo padrões existentes
- **Base de convenções:**
  - `CLAUDE.md` (arquitetura, fluxo de mensagens, pre-AI processing layers)
  - ADRs em `.claude/wiki/decisions/`
  - Models existentes em `db/models.py`
- **Responsabilidades:**
  - Ler user stories em `docs/USER_STORIES_INTERFACE_ATENDENTE.md` + `docs/user-stories/`
  - Ler ADRs antes de qualquer mudança estrutural
  - Implementar features começando pelas de menor dependência
  - Cobrir camadas: webhook, IA service, WhatsApp client, admin endpoints, DB models, prompts/respostas canônicas
  - Em dúvida funcional: `SendMessage` para `product-owner-agent`
  - Em dúvida técnica: `SendMessage` para `architect-agent`
  - **Mudanças no DB:** escrever migration SQL em `scripts/migrations/{TASK}-{descricao}.sql` ANTES de alterar `db/models.py`
  - **Mudanças no system prompt da IA:** consultar PO + Architect antes (impacta contrato JSON)
  - Garantir `python -m py_compile` passa em todos arquivos alterados antes de finalizar
- **Regra rígida:** nunca commitar `.env` ou tokens. Sempre rodar validação de compilação ao terminar.

### Teammate 4 — Frontend Developer
- **Name:** `frontend-agent`
- **Model:** Sonnet 4.6
- **Tools:** Read, Edit, Write, Grep, Glob
- **Stack real:** **vanilla JavaScript ES6+, HTML5, CSS3** (não React, não framework)
- **Output:** código em `static/admin/` (`index.html`, `login.html`, `app.js`, CSS embarcado)
- **Base de convenções:**
  - `CLAUDE.md` seção "Admin Dashboard"
  - `docs/USER_STORIES_INTERFACE_ATENDENTE.md`
  - ADRs em `.claude/wiki/decisions/`
- **Responsabilidades:**
  - Conversar com `backend-agent` via `SendMessage` para obter contrato dos endpoints REST/SSE
  - Implementar telas e componentes em vanilla JS (não introduzir React/Vue/etc sem ADR aprovado)
  - Integrar com `/admin/login`, `/admin/assumir`, `/admin/enviar`, `/admin/devolver`, `/admin/eventos/stream` (SSE)
  - Manter compatibilidade com o JWT armazenado em localStorage (padrão atual)
  - Em dúvida técnica: `SendMessage` para `architect-agent`
  - Em dúvida funcional: `SendMessage` para `product-owner-agent`
- **Regra rígida:** mensagens de operador usam `\n` literal (não `<br>`). Mensagens da IA mantêm `<br>` — não confundir.

### Lead — Tech Lead
- **Name:** `lead-agent` (este é o **lead do time**, sessão principal)
- **Model:** Sonnet 4.6 (herdado)
- **Output final:** relatório consolidado em `docs/release/{versao}.md` ao final de cada ciclo
- **Responsabilidades durante o ciclo:**
  - Quebrar pedido do usuário humano em tasks atômicas e colocar na task list compartilhada
  - Atribuir tasks aos teammates corretos (ou deixar self-claim)
  - Manter `.claude/wiki/hot.md` atualizado com snapshot do progresso
  - Mediar quando PO e Architect divergem
  - **Aguardar teammates concluírem** antes de proceder (não implementar ele mesmo)
- **Output do relatório de release** (`docs/release/{versao}.md`):
  ```markdown
  # Release {versão} — {data}

  ## Funcionalidades implementadas
  ## Dúvidas de negócio levantadas
  ## Dúvidas técnicas levantadas
  ## Resumo executivo (para stakeholder não-técnico)
  ## Riscos mapeados
  ## Próximos passos sugeridos
  ## ADRs criados nesta release
  ## Migrations criadas nesta release
  ```

---

### Quality gates (hooks opcionais)
Após teste do time, considerar adicionar em `.claude/settings.json`:
- `TeammateIdle` hook: bloqueia teammate de ir idle se ainda há tasks pendentes do seu domínio
- `TaskCompleted` hook: roda `python -m py_compile` em arquivos `.py` alterados; rejeita se falhar

### Comandos para o usuário humano interagir
- **Ver progresso:** `Shift+Down` cicla entre teammates
- **Falar com teammate específico:** `Shift+Down` até ele, digitar mensagem
- **Pedir release report:** "lead, gere o release report"
- **Encerrar:** "lead, faça shutdown de todos os teammates e cleanup do time"

<<<FIM>>>

---

## Setup adicional necessário (passos para você)

### 1. Adicionar fix do modo in-process ao `settings.json` global
Em `C:\Users\Home\.claude\settings.json`, adicionar:
```json
"teammateMode": "in-process"
```
Isso força in-process mesmo se algum dia você usar tmux.

Resposta: voce poderia fazer isso voce mesmo? me ajudaria 

### 2. (Opcional, upgrade futuro) Integração Obsidian via MCP
Quando quiser memória persistente acessível por MCP (não só filesystem):

```bash
claude mcp add-json obsidian-vault '{
  "type": "stdio",
  "command": "npx",
  "args": ["-y", "@bitbonsai/mcpvault@latest", "C:/Users/Home/.vscode/chatbot-barbearia/.claude/wiki"]
}'
```
Vantagem: agentes consultam memória via tool calls específicas ao invés de Read/Glob.
Desvantagem: dependência extra (Node + npx), latência maior.

**Recomendação:** começar SEM MCP (filesystem-only). Adicionar MCP só se a busca por contexto ficar ruim.

resposta:  melhor deixar isso para la, sem mcp deve ser bom

### 3. (Opcional) Abrir `.claude/wiki/` como vault no Obsidian
Para você (humano) visualizar a memória do time como wiki com backlinks:
1. Instalar Obsidian
2. "Open folder as vault" → apontar para `C:\Users\Home\.vscode\chatbot-barbearia\.claude\wiki`
3. Os agentes continuam escrevendo via filesystem; você lê via Obsidian com graph view, backlinks, etc.

---

## O que mudou vs template original

| Mudança | Razão |
|---|---|
| Removido `apps/api/` e `apps/web/` | Projeto não é monorepo Node/React |
| Frontend = vanilla JS (não React) | Realidade do `static/admin/` |
| Base = `CLAUDE.md` (não `ARCHITECTURE.md`) | É a fonte canônica deste projeto |
| ADRs criados pelo Architect (não pré-existentes) | Não havia `/docs/adr/` ainda |
| Adicionada camada de memória `.claude/wiki/` | Pedido do usuário (Obsidian integration) |
| Backend cobre também IA/prompts | Sem agente AI/prompt dedicado nesta v1 (pode adicionar v2) |
| Backend cria migrations SQL antes de mexer em models | Convenção do projeto (migrations manuais) |
| Regra explícita: bot NUNCA agenda | Regra crítica de negócio da Barbearia |
| Modo in-process fixado | Compatibilidade Windows |
| Modelo padronizado em Sonnet 4.6 | Custo/qualidade |

---

## Decisões que peço seu input antes de aplicar

1. **Manter 4 teammates ou adicionar 5º (AI/Prompt Engineer)?**
   - 4 teammates (atual): Backend cobre prompts da IA também
   - 5 teammates: agente dedicado para `core/prompts.py` + `core/respostas_canonicas.py`

   resposta: já temos os prompts e respostas prontas, mas acho que nao é necessario um agent de prompt engineer, o de backend deve conseguir melhorar oq for preciso

2. **Modelo do PO e Architect: Sonnet 4.6 ou Opus 4.7?**
   - Sonnet 4.6 (atual): mais barato, suficiente para maioria dos casos
   - Opus 4.7: melhor em decisões arquiteturais complexas (3–5× mais caro)

   resposta: usar opus em ambos, se ficar caro a gente muda depois, mas para começar quero o melhor possivel

3. **Memória: filesystem-only ou já configurar MCP do Obsidian?**
   - Filesystem-only (atual): zero setup, agentes leem/escrevem `.claude/wiki/` direto
   - MCP `@bitbonsai/mcpvault`: agentes usam tool calls específicas, melhor para buscas grandes

   resposta: melhor deixar isso para la, sem mcp deve ser bom

4. **Versão inicial do release report:** `0.1.0` ou continuar do estado atual do projeto?

queria pegar algumas coisas desse repositorio do chatwoot, pois o chat deles é muito completo e gostaria que nosso sistema ficasse semelhante ao chat deles, onde tem como mandar audio, video, ter char privado para notificar entre as pessoas q usam, e muitas outras funcionalidades/configurações que achei legal. mas nem tudo é util para esse sistema, gostaria que tomasse-mos as melhores decisoes e melhorassemos a interface o maximo possivel. eu fiz uma interface com o claude design que esta aqui no projeto, é o arquivo Bolshoi_Atendente_standalone_.html, e o repo do chatwoot é https://github.com/chatwoot/chatwoot.git.

Após responder, aplico o prompt e crio a estrutura.


