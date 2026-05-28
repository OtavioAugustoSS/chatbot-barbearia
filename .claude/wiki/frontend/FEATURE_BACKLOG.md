# FEATURE BACKLOG — Dashboard de Atendentes
**Data:** 2026-05-27
**Autor:** product-owner-agent
**Contexto:** Sprint de usabilidade do dashboard hibrido (`static/admin/`).
**Nota:** Seeds avaliadas individualmente. Funcionalidades ja existentes marcadas como EXISTENTE e descartadas.

---

## Estado atual confirmado (nao propor novamente)

- Indicador "cliente digitando" — EXISTENTE (`#typing-indicator` implementado)
- Atalhos de teclado — EXISTENTE (modal-shortcuts, Ctrl+K, `e`, `s`, `n`, `c`, `/`)
- Som de notificacao (toggle mute) — EXISTENTE (`mute-btn`, `tocarNotificacao()`, `state.muted`)
- Canned responses com atalho `/` — EXISTENTE (sistema completo com API)
- Busca global — EXISTENTE (nome, telefone, mensagem com `?`, mencao com `@`)
- Bulk actions — EXISTENTE (selecao multipla, acoes em lote)
- Labels/tags multiplas — EXISTENTE
- Status FSM (open/pending/resolved/snoozed) — EXISTENTE
- Saved views — EXISTENTE
- Presenca dos atendentes — EXISTENTE (`state.presence`, dot colorido)
- Notas internas com edicao/exclusao — EXISTENTE
- @mencoes — EXISTENTE
- Tema dark/light — EXISTENTE
- Draft salvo por conversa — EXISTENTE
- JWT expiry warning — EXISTENTE
- Skeleton loading + empty states — EXISTENTE
- Waiting badge (tempo de espera em fila) — EXISTENTE (campo `transbordo_em`)

---

## Backlog Priorizado

| # | Feature | Descricao (1 linha) | Valor | Esforco | Prioridade | Observacao de regra de negocio |
|---|---------|---------------------|-------|---------|------------|-------------------------------|
| F-01 | Badges SLA e alerta de fila critica | Destaque visual (cor vermelha progressiva) quando conversa aguardando humano ultrapassa limites de SLA configurados (ex: 5/15/30min) | Alto | M | P1 | Complementa GAP-06 (BR-011): sem auto-atribuicao, mas o alerta visual de espera e a decisao oficial para Sprint 0.3.0 |
| F-02 | Reabertura rapida de conversa resolvida | Botao "Reabrir" inline no card de conversa com status `resolved`, sem necessidade de abrir o painel | Alto | P | P1 | Sem restricao. Status FSM ja suporta transicao resolved→open |
| F-03 | Filtro por data na lista de conversas | Seletor de intervalo de data (hoje / ultimos 7d / personalizado) como filtro adicional na barra lateral | Alto | M | P1 | Sem restricao. Complementa BR-013 (pendencias de cobertura de FAQ — visibilidade de volume) |
| F-04 | Contador de mensagens nao-lidas por aba | Badge numerico nas abas "Aguardando" / "Meus" / "Outros" com contagem de nao-lidos reais | Alto | M | P1 | Sem restricao. TODO ja anotado no codigo (`mensagens_nao_lidas`); requer campo no payload de `/admin/conversas` |
| F-05 | Preview de imagem inline na thread | Renderizar imagens recebidas do cliente diretamente na bolha (sem abrir nova aba) | Alto | M | P2 | Bot nao processa midia (BR-003), mas o ATENDENTE humano recebe midia do cliente via WhatsApp. Preview e para visualizacao no painel, nao processamento pelo bot |
| F-06 | Templates de midia para o atendente | Biblioteca de imagens/documentos pre-aprovados que o atendente pode enviar (ex: cardapio de servicos, QR PIX) | Alto | G | P2 | Atendente humano pode enviar qualquer conteudo. Restricao: nenhum template pode conter texto de agendamento ("marque pelo WhatsApp", "reservo para voce") — revisar templates ao cadastrar |
| F-07 | Nota rapida sem abrir painel | Campo de nota flutuante acessivel via atalho (`n`) diretamente no cabeçalho da conversa, sem exigir abertura do painel lateral | Medio | P | P2 | Sem restricao. Atalho `n` ja existe mas abre o painel inteiro |
| F-08 | Export de conversa (TXT/HTML) | Botao "Exportar" no painel de info que gera arquivo com historico completo da conversa | Medio | M | P2 | Sem restricao. Util para Fred auditar atendimentos. Exportacao e local (sem upload externo) |
| F-09 | Modo compacto da lista | Toggle de densidade: modo padrao (card grande com preview) vs modo compacto (linha fina, so nome + horario) | Medio | P | P3 | Sem restricao. Especialmente util para atendentes com muitas conversas abertas |
| F-10 | Som de notificacao configuravel | Substituir o beep atual por selecao de tom (3-4 opcoes pre-definidas) + controle de volume na pagina de settings | Medio | M | P3 | Sem restricao. Toggle mute ja existe; esta feature expande com granularidade |
| F-11 | Atribuicao rapida por menu contextual | Menu de contexto (clique direito ou icone) no card da conversa para atribuir diretamente a atendente disponivel, sem abrir a conversa | Medio | M | P3 | Requer RBAC (ADR-011) para diferenciar quem pode atribuir forcado. Sem RBAC: atribuicao propria apenas (conflito com GAP identificado em US-197) |
| F-12 | Filtro por atendente atribuido | Chip de filtro adicional "por atendente" alem dos filtros de estado existentes | Medio | P | P3 | Sem restricao. Util para supervisor monitorar carga de trabalho (pre-requisito soft de RBAC) |
| F-13 | Indicador "atendente digitando" visivel ao operador | Mostrar no painel qual atendente esta compondo resposta numa conversa compartilhada | Baixo | G | P4 | Requer SSE novo (`operador_digitando`) — adicionar ao contrato ADR-005 antes de implementar |
| F-14 | Atalho para assumir/devolver via teclado | Tecla `a` para assumir conversa focada, `d` para devolver ao bot — extensao do modal-shortcuts existente | Baixo | P | P4 | Sem restricao. Cuidado com foco: atalho so deve disparar se compositor nao estiver ativo |

---

## Seeds descartadas (com justificativa)

| Seed | Decisao | Justificativa |
|------|---------|---------------|
| Indicador "digitando" do operador visivel ao CLIENTE | **Rejeitar** | Bot nao expoe presenca de atendente ao cliente WhatsApp. Expor "atendente X esta digitando" via mensagem de status quebraria a experiencia e poderia ser confundido com o bot |
| Arrastar para atribuir (drag-and-drop) | **Rejeitar no curto prazo** | Drag-and-drop e anti-padrao em interfaces mobile-first. Substituido por F-11 (menu contextual) com melhor acessibilidade |
| Canned response analytics | **Rejeitar** | BR-AUDIT-002 ja documentou como Baixo valor; nao muda com volume atual |
| Agendamento inline / slots de horario | **REJEITAR DEFINITIVAMENTE** | Viola BR-001 (anti-agendamento absoluto). Qualquer feature que exiba ou sugira slots de horario no dashboard de atendente e vetada — o atendente orienta o cliente a usar o AppBarber |

---

## Top 3 Recomendadas

**F-01 — Badges SLA e alerta de fila critica**
Decisao oficial (GAP-06, BR-011) ja direciona para alerta visual de espera no Sprint 0.3.0; esta feature e a implementacao direta dessa decisao, com infraestrutura de campo `transbordo_em` ja presente no payload.

**F-04 — Contador de mensagens nao-lidas por aba**
O TODO esta comentado no codigo (`mensagens_nao_lidas`), o campo so precisa ser exposto no endpoint `/admin/conversas`; impacto operacional alto (atendente sabe onde ha urgencia sem varrer a lista) por custo de backend minimo (P) + frontend P.

**F-02 — Reabertura rapida de conversa resolvida**
Esforco P (botao simples num card), nenhuma dependencia externa, resolve fluxo de trabalho frequente (cliente retorna apos conversa marcada como resolvida) — ganho de usabilidade imediato.

---

## Notas de produto

- F-06 (templates de midia): todo template de texto cadastrado deve ser revisado pelo PO antes de publicar para garantir que nao contem promessas de agendamento (BR-001). Sugestao: campo `aprovado_po` no cadastro.
- F-11 (atribuicao rapida): bloquear implementacao ate RBAC supervisor/agente estar definido (ADR-011 criterios); sem ele, qualquer atendente pode tomar conversa de outro — risco operacional.
- F-13 (operador digitando): antes de implementar, adicionar evento `operador_digitando` ao catalogo de ADR-005 e solicitar aprovacao do architect-agent.
