# BR-AUDIT-001: Auditoria de Cobertura — User Stories e Regras de Negocio
Data: 2026-05-21
Stakeholders: product-owner-agent (auditoria autonoma, fase inicial)

## Contexto
Primeira auditoria completa do repositorio. Wiki estava em estado zero. Fontes analisadas:
- `docs/USER_STORIES_INTERFACE_ATENDENTE.md` (149 stories v1.0 + expansao v1.1 + Fase 1-3 Chatwoot)
- `core/prompts.py` (SYSTEM_PROMPT_BARBEARIA + ANCORA_ANTI_DRIFT)
- `core/respostas_canonicas.py` (FAQ pre-IA com regex)
- `services/whatsapp.py` (Meta API wrapper)

---

## A. User Stories com status NAO IMPLEMENTADO ou PARCIAL

### Status NÃO IMPLEMENTADO (exige implementacao do zero)

| US | Titulo | Impacto |
|----|--------|---------|
| US-161 | Seed inicial de labels do sistema | Medio — instalacao nova nao tem labels basicas; atendente vê picker vazio |
| US-219 (area 36) | Atalho de teclado j/k para navegacao entre conversas | Baixo — conforto |
| US-272 equivalente / area Bulk | UI de bulk atribuir nao expoe acao `atribuir` | Medio — backend pronto, frontend incompleto |
| US-276 (area Labels Search) | Filtro por label no GET `/admin/conversas` | Alto — backend nao filtra por labels; feature pendente |

### Status PARCIAL (funcionalidade incompleta ou com bug conhecido)

| US | Titulo | Descricao do Gap |
|----|--------|-----------------|
| US-011 | Filtro por estado via chips (aguardando/meus/bot) | Chips inserem string literal no input de busca; `renderListaConversas()` nao interpreta estados booleanos. VIS-01 documentado. |
| US-029 | Painel de info abre automaticamente em desktop | Inline script intercepta `abrirInfoPanel()` com `_blockInfoPanelAutoOpen`. VIS-02. |
| US-039 | Separadores de evento inline (handoff) | CSS pronto, `renderThread()` nao injeta separadores; backend nao retorna metadados de handoff como eventos. VIS-03. |
| US-175 | Default status `open` ao criar Usuario | Filtro SQL `== "open"` nao captura NULL. Migration de backfill necessaria. |
| US-200..203 (area @mentions) | Editar nota nao re-processa mentions | Salvamento silencioso funciona; edicao de nota e gap. |
| US-209..212 (area Bulk) | UI de bulk nao expoe acoes `atribuir`, `desatribuir`, `resolver` | Backend completo; frontend nao consome. |
| US-217 (area Bulk SSE) | SSE evento bulk_action_completed nao consumido | Backend publica, frontend nao consome. |
| US-218 (area Bulk) | Selecao persiste ao mudar filtro | Falta limpeza de selecao ao trocar chip de filtro. |
| US-233 (area Saved Views) | Backend e api wrapper prontos; UI nao expoe | Funcionalidade de Saved Views sem tela. |
| US-253 (area Global Search) | Busca global abre conversa mas nao rola ate o match | Navegacao incompleta. |
| US-264 (area Shortcuts) | Modal de atalhos de teclado | PARCIAL — Esc nao implementado em settings. |
| US-268 (area Temas) | Selecao de tema apagada em logout | localStorage.clear() remove preferencia de tema. |
| US-271 (area Status) | Bot ativo + resolved gera confusao UX | Status conversa deveria limpar bot ao resolver? Comportamento ambiguo. |

### Stories com GAPs de backend documentados (sem US formal):

| Gap ID | Descricao |
|--------|-----------|
| GAP-01 | Endpoint `PATCH /admin/atendentes/{id}/ativar` nao existe; atendentes desativados nao podem ser reativados pela UI |
| GAP-02 | `/admin/conversas` sem query params de filtro por estado |
| GAP-03 | Paginacao da lista de conversas: limite hardcoded 200 sem cursor |
| GAP-04 | `/admin/notas/{telefone}` sem paginacao; payloads grandes possiveis |
| GAP-05 | Sem DELETE/PATCH de notas |
| GAP-06 | `devolver` sempre envia mensagem de despedida; sem reativacao silenciosa do bot |
| GAP-07 | `/admin/conversa/{telefone}` sem filtro por data / paginacao retroativa |
| GAP-08 | Evento SSE `atendente_assumiu` nao inclui nome do atendente |

---

## B. Regras de Negocio — Validacao contra codigo

### Regras implementadas em codigo mas SEM nota formal em business-rules/

As seguintes regras estao em `core/prompts.py` ou `core/respostas_canonicas.py` e nao possuem arquivo BR dedicado:

1. **Anti-agendamento absoluto**: bot nunca promete agendar; sempre redireciona AppBarber. Hardcoded em regra 6 do prompt e em anti-appointment regex em `ai_service.py`. Nao documentado como BR formal.
2. **Contato do Fred so sob demanda explicita**: regra 11 do prompt (caso especial). Nao documentado como BR formal.
3. **`intencao=chamar_recepcao` NUNCA para perguntas sobre o Fred**: Fred usa `tirar_duvida` + telefone direto. Nao documentado.
4. **Modo bot_only vs hibrido no system prompt**: regra 15(f) e 15(e) tem comportamentos distintos. Nao documentado.
5. **ANCORA_ANTI_DRIFT em conversas >= 6 turnos**: mecanismo de anti-drift nao documentado como BR.
6. **Canônica de cancelamento/remarcacao**: regex em `respostas_canonicas.py` captura antes de IA. Nao documentado.
7. **Resposta de disponibilidade de slot passa para IA** (nao canonicas): `_PADRAO_DISPONIBILIDADE` excluido das canonicas. Nao documentado.
8. **Formato `<br>` obrigatorio na IA vs `\n` direto para operador**: separacao critica, sem BR formal.
9. **Lista interativa de menu (WhatsApp Interactive List)**: `whatsapp.py` tem `enviar_lista_interativa()` para menus scrollaveis (feature de 2026-05-16 per memoria), sem story documentada.
10. **Mensagem de boas-vindas ao assumir**: texto fixo hardcoded em `api/admin.py`. Sem BR formal sobre quando pode ser alterado.
11. **Mensagem de despedida ao devolver**: texto fixo. Sem BR sobre mutabilidade.
12. **Auto-reativacao do bot apos `BOT_REATIVAR_APOS_HORAS`**: comportamento de reativacao automatica sem handoff humano nao documentado como BR.
13. **Deduplicacao de mensagens via tabela `MensagemProcessada`**: pre-processamento critico sem story ou BR.
14. **Rate limit 10 msg/min por telefone**: protecao sem story ou BR formal.
15. **Lock por telefone (30 min TTL)**: mutex de processamento sem documentacao.

### Regras documentadas mas SEM implementacao verificavel

- **GAP-01 (reativar atendente)**: especificado em US-090 CA-04 (conversas abertas liberadas ao desativar) mas nao ha endpoint de reativacao. Story existe, implementacao parcial.
- **US-109 (status ocupado)**: story criada, sem implementacao. Backend nao tem coluna `Atendente.status` para ocupado/disponivel.
- **US-110 (atendente offline via beforeunload)**: story criada, sem endpoint `/admin/atendentes/me/offline`.
- **US-115 (aviso 2min antes de expirar JWT)**: story criada, sem implementacao. Endpoint `/admin/refresh-token` pode nao existir.
- **US-128 (Desktop Notification API)**: story criada, sem implementacao.
- **US-145 (SSE com replay `?desde=`)**: story criada, backend SSE nao tem suporte a buffer/replay.

---

## C. Problemas Visuais sem User Story de Correcao Prioritaria

| Cod | Descricao | US associada |
|-----|-----------|-------------|
| VIS-01 | Chips de filtro quebrados | US-011 PARCIAL |
| VIS-02 | Info panel nao abre auto em desktop | US-029 PARCIAL |
| VIS-03 | Separadores de handoff nao renderizados | US-039 PARCIAL |
| VIS-04 | Botao Emoji permanentemente desabilitado | Sem US de remocao ou implementacao |
| VIS-05 | Botao "Favoritar cliente" sem funcionalidade | Sem US de implementacao ou remocao |
| VIS-06 | Secao "Servicos frequentes" com dado errado | Usa tag da conversa ao inves de servicos reais |
| VIS-07 | Avatar do atendente exibe "?" brevemente | Sem US de correcao |

---

## Regra derivada desta auditoria

As regras de negocio listadas no item B acima (anti-agendamento, contato Fred, modos bot_only/hibrido, `<br>` vs `\n`, etc.) devem ser formalizadas em arquivos BR dedicados nos proximos ciclos. Prioridade alta: anti-agendamento e contato Fred (mais criticas para compliance).

## Impacto em codigo
- VIS-01 (US-011): exige mudanca em `renderListaConversas()` no frontend e possivelmente query param `?estado=` no backend.
- GAP-01 (reativar atendente): novo endpoint PATCH no `api/admin.py`.
- US-161 (seed labels): novo script `scripts/migrations/seed_labels.sql`.
- US-175 (status NULL backfill): migration SQL para `UPDATE usuarios SET status_conversa='open' WHERE status_conversa IS NULL`.

## Excecoes
Nenhuma das regras de negocio principais (anti-agendamento, AppBarber only, categorias servico) esta em risco de quebra — todas hardcoded no prompt e validadas por regex de seguranca em `ai_service.py`.
