# Agent State — Barbearia Bolshoi

Log permanente de tasks orquestradas. Cada linha é um ciclo completo.

| Task ID | Status | Agente principal | QA Verdict | Data | Resumo |
|---------|--------|------------------|------------|------|--------|
| TASK-INTERACTIVE-LIST-MENU | done | dev-agent | PASS_WITH_NOTES | 2026-05-16 | Substituição dos menus de texto plano por WhatsApp Interactive List Message (6 itens em 3 seções) com fallback automático para texto, mapeamento de seleções para canônicas/IA, e handoff de recepção unificado |
| TASK-INTERACTIVE-LIST-REVIEW | done | orchestrator | PASS_WITH_NOTES | 2026-05-16 | Revisão pré-teste do Interactive List Menu: code review (sem bugs bloqueantes), 4 observações de baixo impacto, checklist de 12 cenários de teste manual entregue ao usuário, lista de env vars necessárias documentada |
| TASK-MENU-SUBFLUXO | done | dev-agent | PASS_WITH_NOTES | 2026-05-16 | Redesign pós-seleção da Interactive List: MENU_SERVICOS_PRECO e MENU_EQUIPE agora abrem sub-fluxo de botões (💈 Barbearia / 💆 Estética / 📅 Agendar). MENU_AGENDAMENTO ganhou botão de recepção. Sub-respostas usam DB direto (sem IA), preservando preços e equipe atualizados. Inclui SUB_VOLTAR_MENU e SUB_AGENDAR como atalhos universais |
| TASK-TEXTOS-REVISAO | done | prompt-engineer | PASS | 2026-05-16 | Revisão completa de textos do cliente: system prompt renumerado e reforçado com 4 novas regras (cancelamento/remarcação, fora de horário, mídia, atendimento feminino); 3 novas canônicas (cancelar/remarcar, estacionamento, atendimento feminino); fechamento padronizado em todas as canônicas; FAQ_ESTRUTURA limpo (pagamento removido — tem canônica própria); textos do webhook neutralizados de emojis casuais e termo "humano" |
| TASK-MENU-MODE-AWARE | done | dev-agent | PASS_WITH_NOTES | 2026-05-16 | Menus e botões agora respondem ao MODO_OPERACAO. Bot_only não exibe mais "Falar c/ Recepção" (item de lista, botões pós-categoria, botão pós-agendamento) — promessa quebrada eliminada. Híbrido renomeia "Recepção" → "Atendente" e expõe botão "Falar c/ Atendente" (20 chars, limite Meta) nos sub-fluxos. Nova RESPOSTA_AGENDAMENTO_HIBRIDO adicionada. _MENU_SECTIONS virou função `_montar_menu_sections()` avaliada em runtime |
| TASK-LIMPEZA-2026-05 | done | orchestrator | PASS | 2026-05-16 | Limpeza geral solicitada pelo dono: (1) removido "⏳ Processando sua mensagem..." de webhook.py (bloco completo + heurística `resposta_sera_instantanea`); (2) removida canônica de estacionamento (constante RESPOSTA_ESTACIONAMENTO + regex em `_PADROES`) — barbearia não tem estacionamento, agora cai na regra 14c do prompt; (3) removido dead code `MENSAGEM_MENU_REPETIDO` em webhook.py (sem callsite ativo); (4) MENSAGEM_BOAS_VINDAS e _montar_saudacao MANTIDOS — são fallback ativo de _enviar_menu_lista quando Meta rejeita Interactive List. Prompt e ai_service.py auditados e sem mudanças necessárias (dados reais do banco já injetados via _carregar_dados_db) |
| TASK-FORMATACAO-FIX | done | dev-agent | PASS | 2026-05-16 | Bug: ao selecionar "📍 Horários e Endereço" no menu, bot retornava "Posso ajudar em algo mais?" duplicado e linhas potencialmente emendadas. Correções: (1) refatorou `respostas_canonicas.py` em corpo+fechamento separáveis; criada `RESPOSTA_HORARIO_ENDERECO` combinada com fechamento ÚNICO; (2) `webhook.py` usa nova constante em `_RESPOSTAS_DIRETAS_MENU`; (3) `_normalizar_texto_envio` endurecido: trata CRLF, remove espaços em fim de linha (causa raiz de "texto emendado"), normaliza `<br>` com whitespace; (4) padronizou negrito `*titulo*` em TODAS as canônicas e textos fixos do webhook (boas-vindas, saudação, mídia, transbordo bot_only); (5) imports não usados removidos de webhook.py |
| TASK-UI-REDESIGN-TELEGRAM | done | dev-agent | PASS | 2026-05-16 | Redesign completo do dashboard admin para paleta Telegram Dark (cinza neutro #212121/#1c1c1c/#2b2b2b + azul Telegram #2481cc). Substituiu paleta híbrida teal/blue anterior nos 4 arquivos (index.html, login.html, atendentes.html, app.js). Caudas das bolhas atualizadas. Classes CSS `<style>` mantêm os mesmos nomes (bolha-*, conv-item, scrollbar) — handlers JS intactos. Bolhas: cliente #2b2b2b, bot #0d3875 (navy escuro), humano #2481cc (azul Telegram brilhante) — distinção clara entre origens. Animações fadeInUp/slideIn/pulseRing(vermelho semântico)/fadeIn preservadas. Mobile sidebar slide preservado. Handler de envio: classes inline migradas para `bolha-falha` (mais robusto que Tailwind arbitrário). Toast/tag-selector/indicador entrega mantêm cores semânticas (verde ok, vermelho erro, azul info, emerald resolvido, yellow follow-up) |
| TASK-UI-CLEANUP | done | dev-agent | PASS | 2026-05-16 | Limpeza de UI/UX no painel admin: (1) Tag-selector convertido de barra horizontal sempre-visível no header (3 botões + label "Tag:") para popover acionado por botão de ícone (tag) no header — preserva endpoint PATCH /conversa/{tel}/tag e ID DOM #tag-selector. (2) Placeholder não preenchido `[endereço da barbearia]` nas RESPOSTAS_RAPIDAS substituído pelo endereço real da barbearia. (3) Emojis decorativos removidos: 🟢/🔴/🤖 dos status do header (texto já é colorido), 🔔/💬 dos toasts (cor do toast já dá semântica), ⚙ do link Atendentes substituído por SVG. (4) Emoji 💬 do botão "Rápidas" substituído por SVG e label expandida para "Respostas rápidas". (5) Textos limpos: empty state perdeu subtítulo verboso, placeholder do composer simplificado de "(Enter envia, Shift+Enter quebra linha)" para "Digite uma mensagem…", label de métrica "Em atend." vira "Atendendo", status "Conversa atendida por outro atendente (id N)" vira "Em atendimento por outro operador". (6) Emojis preservados por valor semântico real: chips de mídia (🎵🖼️📎), badges de tag na sidebar (✓ Resolvido, ↩ Follow-up), indicadores de erro (⚠). Zero alterações em handlers JS, endpoints ou paleta Telegram Dark |
| TASK-CLIENT-INFO-PANEL | done | dev-agent | PASS | 2026-05-16 | Painel lateral direito de informações do cliente no dashboard híbrido. (1) DB: nova coluna `usuarios.foto_url` VARCHAR(500) + `usuarios.foto_atualizada_em` DATETIME (migration TASK_FOTO_URL.sql idempotente via procedure que checa INFORMATION_SCHEMA antes do ALTER). (2) Backend: `WhatsAppSender.buscar_foto_perfil(numero)` chama Meta Graph `/contacts?fields=profile_picture_url` com timeout 8s, try/except amplo (RequestException, ValueError/KeyError/TypeError, Exception genérico) e validação de URL (`startswith("http")`). Novo endpoint `GET /admin/cliente/{telefone}/info` (auth JWT) retorna telefone, nome, criado_em, data_ultima_interacao, tag, bot_ativo, aguardando_humano, atendente_id, total_mensagens, total_atendimentos_humanos, foto_url. Cache de foto com TTL de 30min (não martela Meta API) — refresh sob demanda quando `foto_atualizada_em` expira ou é NULL. Falha de Meta atualiza `foto_atualizada_em` mesmo com `foto_url=None` para respeitar TTL em clientes com privacidade fechada. (3) Frontend: novo `<aside id="info-panel">` à direita da thread com avatar (foto ou iniciais coloridas), nome, telefone, estatísticas (cliente desde, última interação relativa, total de mensagens, atendimentos humanos), status (bot ativo/inativo/atendente, tag) e painel de notas movido para dentro do painel. Painel é colapsável (botão X no header + botão info no header da thread); em telas <1024px vira drawer absoluto com backdrop. Race condition protegida via `_infoCarregandoTelefone` — troca rápida entre conversas descarta resposta obsoleta. Foto carregada via `new Image()` com onerror que cai para iniciais. Endpoint chamado em `abrirConversa()`. |

## Histórico detalhado

### TASK-INTERACTIVE-LIST-MENU (2026-05-16)

**Fluxo:** PO valida → Dev implementa → QA revisa

**PO Agent:** APROVADO COM OBSERVAÇÕES
- Renomear título do item HORARIO_LOCAL para "Horários e Endereço" (vs "Horários e Localização") para evitar confusão com slot
- MENU_RECEPCAO deve reusar exatamente o fluxo do botão "🙋 Falar c/ Recepção" (incluindo branch bot_only)
- Header: "Barbearia Bolshoi 💈"; Footer: "Toque em Ver opções abaixo"; Button: "Ver opções"
- Body personalizado com primeiro nome quando disponível

**Dev Agent:** Implementação em 2 arquivos
- `services/whatsapp.py`:
  - Refatorou `enviar_mensagem_texto` para usar helper `_post_com_retry` (DRY)
  - Adicionou `enviar_lista_interativa()` com validação local de todos os limites Meta
  - Adicionou suporte a `list_reply` em `extrair_informacoes_mensagem`
  - Adicionou return explícito para tipos `interactive` desconhecidos (defensivo)
- `api/webhook.py`:
  - Importou canônicas `RESPOSTA_HORARIO/ENDERECO/AGENDAMENTO/PAGAMENTO`
  - Adicionou constantes `_MENU_ID_*`, `_MENU_IDS`, `_MENU_SECTIONS`, `_RESPOSTAS_DIRETAS_MENU`, `_MAPA_MENU_PARA_TEXTO`
  - Adicionou `_montar_body_menu()` para body personalizado com nome
  - Adicionou `_enviar_menu_lista()` com fallback automático para texto plano
  - Extraiu `_executar_handoff_recepcao()` (deduplica lógica do botão antigo + MENU_RECEPCAO)
  - Substituiu pontos de entrega de menu em `_processar_mensagem` (primeiro contato, pedido de menu, saudação pura) para usar lista interativa
  - Adicionou tratamento de IDs MENU_* antes do pipeline (respostas diretas vs IA)
  - Em `receive_message`: unificou handler de "🙋 Falar c/ Recepção" e MENU_RECEPCAO
  - Suprimiu placeholder "⏳ Processando" para mensagens com resposta instantânea (MENU_*, saudação, canônica)

**QA Agent:** APROVADO COM RESSALVAS
- Todos os 6 itens dentro dos limites Meta API (validados manualmente e em runtime)
- 14 edge cases revisados, todos com comportamento correto
- 5 riscos identificados, todos BAIXA severidade
- Recomendou 10 cenários de teste manual em WhatsApp real antes de produção
- Ressalvas não-bloqueantes:
  - R1: Considerar salvar texto completo do menu em vez de placeholder no histórico
  - R2: Teste manual obrigatório antes de produção (sem suíte automatizada)
  - R3: Avaliar UX híbrida de re-entrega de lista após handoff voltar

**Arquivos modificados:**
- `C:\Users\Home\.vscode\chatbot-barbearia\services\whatsapp.py`
- `C:\Users\Home\.vscode\chatbot-barbearia\api\webhook.py`

**Status final:** DONE

### TASK-MENU-SUBFLUXO (2026-05-16)

**Fluxo:** PO valida → Dev implementa → QA revisa

**PO Agent:** APROVADO
- MENU_SERVICOS_PRECO → 3 botões (💈 Barbearia / 💆 Estética / 📅 Agendar)
- MENU_EQUIPE → 3 botões (💈 Barbeiros / 💆 Estética / 📅 Agendar)
- MENU_AGENDAMENTO → texto canônico + 1 botão (🙋 Falar c/ Recepção)
- MENU_HORARIO_LOCAL, MENU_PAGAMENTO → mantém resposta direta sem botão
- MENU_RECEPCAO → mantém handoff existente
- Listar barbeiros individualmente como botões NÃO faz sentido (limite 3, não há agendamento aqui)
- Após sub-categoria: botões [📅 Agendar] [⬅ Menu] para navegação fluida
- IDs SUB_* para não colidir com MENU_*

**Dev Agent:** Implementação em 2 arquivos

`services/whatsapp.py`:
- Adicionou `enviar_botoes_resposta(numero, body_text, buttons, header_text, footer_text)`
- Validação local completa (max 3 botões, title ≤20, id ≤256, body ≤1024, header/footer ≤60, IDs únicos)
- Reusa `_post_com_retry` (DRY com lista interativa)

`api/webhook.py`:
- Import de `Servico` e `Barbeiro` adicionado
- Constantes `_SUB_ID_*` e set `_SUB_IDS` (6 IDs: SUB_SERV_BARBEARIA, SUB_SERV_ESTETICA, SUB_EQUIPE_BARBEIROS, SUB_EQUIPE_ESTETICA, SUB_AGENDAR, SUB_VOLTAR_MENU)
- `_RESPOSTAS_DIRETAS_MENU` reduzido a PAGAMENTO e HORARIO_LOCAL (AGENDAMENTO movido para fluxo com botão)
- `_MAPA_MENU_PARA_TEXTO` removido inteiramente (não há mais itens delegados à IA)
- Helper `_registrar_envio_botoes()` para enviar texto + botões + log + fallback textual
- `_enviar_subflow_servicos()` e `_enviar_subflow_equipe()` enviam botões de sub-categoria
- `_enviar_agendamento_com_botao_recepcao()` envia canônica + botão recepção
- `_listar_servicos_categoria()` e `_listar_equipe_categoria()` consultam DB sem chamar IA
- `_enviar_servicos_categoria()` e `_enviar_equipe_categoria()` montam resposta + botões [Agendar] [Menu]
- `_despachar_menu_principal()` centraliza tratamento de MENU_* (substitui blocos inline)
- `_despachar_subfluxo()` centraliza tratamento de SUB_*
- Pipeline `_processar_mensagem` simplificado: 2 chamadas de despacho substituem o bloco antigo
- `_SUB_IDS` adicionado à heurística `resposta_sera_instantanea` (sem placeholder "⏳ Processando")

**QA Agent:** APROVADO COM RESSALVAS
- Todos os limites Meta API validados (botões ≤3, títulos ≤20 chars, body ≤1024)
- 11 cenários revisados, todos com comportamento correto
- Edge cases: DB vazio em categoria, anti-loop confirmado, handoff humano preserva mensagem do cliente
- Botão MENU_AGENDAMENTO → MENU_RECEPCAO usa handler legado (correto, sem duplicação)
- Ressalvas BAIXAS:
  - R1: `_listar_equipe_categoria` carrega todos os barbeiros e filtra em Python (aceitável para escala atual <10 profissionais)
  - R2: placeholder "[BOTÕES: ...]" no histórico pode chegar ao contexto da IA — baixíssimo risco de alucinação por formato não-natural
  - R3: cliente recebe 2 balões (texto + botões) — UX intencional e legível
- Recomendado teste manual em WhatsApp real cobrindo: clique em Serviços → Barbearia, Serviços → Estética, Equipe → Barbeiros, Equipe → Estética, Agendamento → Falar Recepção, Voltar ao menu, DB sem serviços de uma categoria, cliente em handoff humano clicando botão

**Arquivos modificados:**
- `C:\Users\Home\.vscode\chatbot-barbearia\services\whatsapp.py`
- `C:\Users\Home\.vscode\chatbot-barbearia\api\webhook.py`

**Status final:** DONE

### TASK-TEXTOS-REVISAO (2026-05-16)

**Fluxo:** Prompt-Engineer analisa → PO valida → Implementa → QA revisa

**Prompt-Engineer:** análise crítica nos 3 arquivos
- `core/prompts.py`: identificou numeração duplicada (duas regras "5"), regras ausentes (mídia, fora de horário, cancelamento), regra de FAQ inconsistente com canônica, falta de regra para atendimento feminino
- `core/respostas_canonicas.py`: faltava "Domingo: fechado" no horário, faltava fechamento "Posso ajudar em algo mais?" em algumas canônicas, faltava canônica para cancelar/remarcar (caía na IA com risco de alucinação), faltavam tópicos comuns (estacionamento, atendimento feminino), FAQ_ESTRUTURA misturava pagamento (duplicação)
- `api/webhook.py`: MENSAGEM_BOAS_VINDAS usava "Em que posso ser útil hoje?" — exatamente a frase que o prompt PROIBE; handoff de recepção usava emoji 🙋 e palavra "humano" (violando regra do próprio prompt); fallback de mídia tinha tom infantilizado ("bot aprendendo"); fallback bot_only usava 🤖 e "humano"

**PO Agent:** APROVADO
- Validou que estacionamento não pode ser afirmado nem negado (sem confirmação oficial) → texto "sugerimos confirmar com a recepção"
- Validou que telefone genérico da barbearia NÃO deve existir como canônica (apenas Fred, pessoal) → não criou
- Confirmou Wi-Fi, AC, infantil, cadeirante, atendimento feminino como verdades do negócio
- Aprovou remoção da palavra "humano" e emojis casuais para alinhar tom

**Implementação:**

`core/prompts.py` (reescrito):
- Renumeração sequencial 1-18 (corrigiu numeração duplicada)
- Adicionada regra 7: CANCELAMENTO E REMARCAÇÃO — nunca prometer executar
- Adicionada regra 16: FORA DO HORÁRIO — comportamento quando barbearia está fechada
- Adicionada regra 17: MÍDIA — caso de borda se mídia vazar até a IA
- Adicionada regra 18: ATENDIMENTO FEMININO — barbearia atende todos
- Regra 13 (preços) reforçada: PROIBIDO inventar pacotes mensais, fidelidade, "primeira vez"
- Regra 8 (serviços não oferecidos) ampliada: pedicure, química, alisamento
- Regra 14 (info não listada) atualiza fallback: redireciona para recepção (sem expor telefone do Fred como fallback genérico)
- Bloco DADOS DA BARBEARIA: adicionada linha sobre atendimento feminino
- Exemplos adicionados: cancelamento, atendimento feminino
- Regras do JSON expandidas (sempre presente, string, sem null, parseável por json.loads)
- ANCORA_ANTI_DRIFT atualizada: inclui "cancelar/remarcar" na lista de proibições

`core/respostas_canonicas.py` (reescrito):
- RESPOSTA_HORARIO: adicionada linha "Domingo: fechado"
- RESPOSTA_ENDERECO: adicionado fechamento "Posso ajudar em algo mais?"
- RESPOSTA_AGENDAMENTO: descreve melhor o que o cliente faz no app (serviço, profissional, data, horário) + fechamento
- RESPOSTA_PAGAMENTO: adicionado fechamento padrão
- RESPOSTA_FAQ_ESTRUTURA: removido pagamento (duplicava RESPOSTA_PAGAMENTO); foco em estrutura física
- RESPOSTA_CANCELAR_REMARCAR (nova): direciona ao AppBarber, sem prometer execução
- RESPOSTA_ESTACIONAMENTO (nova): tom honesto "sugerimos confirmar com a recepção"
- RESPOSTA_ATENDIMENTO_FEMININO (nova): afirma que atende todos os públicos
- Padrões regex adicionados para cancelar/remarcar (com ORDEM antes de agendar), estacionamento, atendimento feminino
- Regex de pagamento ampliada: "tem maquininha?", "posso passar cartão?"
- Regex de FAQ_ESTRUTURA ampliada: cobre "tem internet?"

`api/webhook.py` (textos fixos):
- MENSAGEM_BOAS_VINDAS: removida "Em que posso ser útil hoje?", padronizada com o menu literal do prompt
- `_montar_body_menu`: primeiro contato mais conciso; retorno usa "Olá novamente!" (mais caloroso)
- `_executar_handoff_recepcao` hibrido: removido emoji 🙋, texto profissional ("atendente da nossa recepção" em vez de "atendente humano")
- `_executar_handoff_recepcao` bot_only: removido 🤖, removido "humano", texto direto
- Mensagem de mídia (linha 1080): tom profissional, sem "bot aprendendo"
- Fallback transbordo_falha: removido emoji 😕, tom técnico-neutro ("instabilidade")
- Fallback chamar_recepcao bot_only no `_processar_mensagem`: alinhado com o handoff principal
- Fallback de sub-fluxo de serviços: descrição da estética mais fiel ("procedimentos com a Isabella" em vez de "limpeza, sobrancelha, etc.")

**QA Agent:** APROVADO (PASS)
- Tamanhos: todas as canônicas <300 chars normalizados (UX excelente em WhatsApp)
- Tom: consistente em todas as canônicas com fechamento "Posso ajudar em algo mais?" onde aplicável
- Sem promessas indevidas: nenhum texto promete agendar, cancelar ou transferir manualmente
- Regex: ordem correta (cancelar antes de agendar, específicos antes de genéricos)
- Não-quebra: imports preservados, nenhuma função/assinatura alterada
- Prompt: numeração sequencial limpa, novas regras coerentes com regras existentes, exemplos cobrem casos novos
- Ressalva (não-bloqueante): MENSAGEM_MENU_REPETIDO continua definida mas sem callsite ativo no webhook.py — código morto, manter por possível uso futuro

**Arquivos modificados:**
- `C:\Users\Home\.vscode\chatbot-barbearia\core\prompts.py`
- `C:\Users\Home\.vscode\chatbot-barbearia\core\respostas_canonicas.py`
- `C:\Users\Home\.vscode\chatbot-barbearia\api\webhook.py`

**Status final:** DONE

### TASK-MENU-MODE-AWARE (2026-05-16)

**Fluxo:** PO valida → Dev implementa → QA revisa

**PO Agent:** APROVADO COM AJUSTE
- Bot_only NUNCA prometer atendente. Remover item "Falar com Recepção" da seção Atendimento. Se seção ficar vazia, remover seção inteira (4 seções → 3, bot_only ficou com 2 seções).
- Híbrido manter, mas renomear "Recepção" → "Atendente" para refletir operador no dashboard (não balcão físico).
- Recusou adicionar item "📲 Agendar pelo App" extra (já existe MENU_AGENDAMENTO — duplicaria).
- RESPOSTA_AGENDAMENTO_HIBRIDO: nota suave "Se preferir, nossos atendentes também podem te ajudar com dúvidas sobre o app".
- Em `_enviar_agendamento_com_botao_recepcao` bot_only: SEM botão (só texto). Resolve UX inconsistente onde botão caía em "não temos atendente".

**Dev Agent:** Implementação em 2 arquivos

`core/respostas_canonicas.py`:
- Adicionado `RESPOSTA_AGENDAMENTO_HIBRIDO` (mesma orientação canônica + nota suave de atendente humano disponível para dúvidas do app)

`api/webhook.py`:
- Import de `RESPOSTA_AGENDAMENTO_HIBRIDO`
- Convertido `_MENU_SECTIONS` (constante) em `_montar_menu_sections()` (função runtime, lê MODO_HIBRIDO)
- Híbrido: 3 seções, item "🙋 Falar c/ Atendente" (renomeado). Bot_only: 2 seções, sem Atendimento.
- `_enviar_menu_lista()` agora chama `_montar_menu_sections()` em vez da constante
- Novo `_SUB_ID_FALAR_ATENDENTE = "SUB_FALAR_ATENDENTE"` adicionado a `_SUB_IDS`
- Nova helper `_botoes_acao_pos_lista(incluir_voltar)` produz botões dinâmicos:
  - bot_only: [📅 Agendar pelo App] [Menu principal]
  - híbrido:  [📅 Agendar pelo App] [🙋 Falar c/ Atendente] [Menu principal]
- `_enviar_servicos_categoria()` e `_enviar_equipe_categoria()` agora usam `_botoes_acao_pos_lista()`
- `_enviar_agendamento_com_botao_recepcao()` refatorada:
  - bot_only → `_enviar_e_registrar` com RESPOSTA_AGENDAMENTO puro, sem botão
  - híbrido → RESPOSTA_AGENDAMENTO_HIBRIDO + botão Falar c/ Atendente
- `_despachar_subfluxo` para `_SUB_ID_AGENDAR` agora mode-aware (mesma lógica acima)
- `receive_message`: handoff síncrono via dict `_GATILHOS_HANDOFF` que aceita todos os gatilhos (botão legado "Recepção", "Atendente", MENU_RECEPCAO, SUB_FALAR_ATENDENTE)

**QA Agent:** APROVADO COM RESSALVAS
- Todos os botões dentro do limite Meta (20 chars). "🙋 Falar c/ Atendente" = 20 chars exatos (limite máximo).
- Edge cases revisados: nenhum dead-end, nenhum loop, nenhuma promessa quebrada em bot_only.
- Histórico fiel ao envio (placeholder com títulos reais dos botões varia por modo).
- Defensivo: handler legado de MENU_RECEPCAO permanece (compatibilidade com mensagens antigas).
- Ressalvas BAIXAS:
  - R1: "🙋 Falar c/ Atendente" no limite exato 20 chars (Meta usa codepoints, passa). Se Meta apertar para 19 no futuro, é o primeiro a quebrar — mitigação seria encurtar para "🙋 Atendente humano".
  - R2: Inconsistência cosmética: "📅 Agendar" (9 chars) no subflow categórico inicial vs "📅 Agendar pelo App" (19 chars) pós-categoria. Comportamento idêntico (mesmo SUB_ID_AGENDAR), apenas texto diferente.

**Arquivos modificados:**
- `C:\Users\Home\.vscode\chatbot-barbearia\core\respostas_canonicas.py`
- `C:\Users\Home\.vscode\chatbot-barbearia\api\webhook.py`

**Status final:** DONE

### TASK-UI-REDESIGN-TELEGRAM (2026-05-16)

**Fluxo:** PO valida → QA audita → Dev implementa → QA revisa

**PO Agent:** APROVADO
- Mudança puramente cosmética (CSS/Tailwind classes). Sem impacto em regras de negócio, contrato JSON da IA, fluxo de handoff humano ou experiência do cliente WhatsApp.
- Melhora ergonomia do atendente (paleta Telegram dark fatiga menos em sessões longas que teal-WhatsApp).
- Restrições: NÃO alterar handlers JS, fetch, SSE, IDs DOM, contratos de endpoint. Preservar distinção visual clara bot vs atendente humano. Manter animações.

**QA Agent (auditoria pré-implementação):** Inventário completo dos 4 arquivos
- Catalogou 14 componentes/estados visuais a preservar
- Mapeou 16 cores antigas → novas com contexto de uso (borda vs bg vs hover)
- Listou todas as classes Tailwind injetadas em app.js (toast, tagBadgeHTML, renderListaConversas, atualizarHeaderThread, separadorData, indicadorEntrega, resolverConteudoMensagem, bolha, iniciarRespostasRapidas, setStatusConexao, carregarNotas, handler de envio inline)
- Documentou estados críticos: bolhas com cauda ::before, conv-item.ativo, sidebar mobile transform, pulse-red rgba vermelho semântico

**Dev Agent:** Implementação nos 4 arquivos
- `index.html`: bg #212121, sidebar #1c1c1c, headers #2b2b2b, bordas #3a3a3a, texto branco/#aaaaaa. Métricas reformatadas (badge "Com bot" agora usa #2481cc/20). Botões primários #2481cc/#1a6eb0/#1560a0. CSS das bolhas no `<style>` atualizado para nova paleta. Caudas (::before) com border-color alinhado. Nova regra `.bolha-falha::before { display: none }` evita conflito visual quando bolha azul vira vermelha em runtime. Input do form ganhou borda visível.
- `login.html`: card centralizado paleta Telegram (#1c1c1c sobre #212121, azul #2481cc no logo e botão, focus ring #2481cc).
- `atendentes.html`: tabela #1c1c1c, header #2b2b2b, rows hover #2f2f2f. Modal #1c1c1c overlay bg-black/70. Badge "Você" agora azul Telegram (#2481cc/20 border #2481cc/60). Status ativo/inativo e botão desativar mantêm semântica (verde/vermelho).
- `app.js`: apenas strings de classes Tailwind alteradas em: toast() (info → #2481cc, text-white), tagBadgeHTML() (opacity ajustada), renderListaConversas (badge "Eu" → #2481cc/20, borda #3a3a3a, texto branco/#aaaaaa), atualizarHeaderThread (status text-[#2481cc] para bot ativo, text-[#aaaaaa] para neutros), renderThread (empty state #aaaaaa), separadorData (bg #2b2b2b border #3a3a3a), indicadorEntrega (✓ #2481cc, ⚠ red-500), resolverConteudoMensagem (chip mídia bg #2b2b2b), bolha (text-white + bolha-label class), iniciarRespostasRapidas (hover #2f2f2f), setStatusConexao (dot reconectando #aaaaaa), carregarNotas (li nota #2b2b2b/#3a3a3a, texto branco), handler de envio inline (substituído `bg-blue-600 border-blue-500 → bg-red-900/50` por classes CSS `bolha-outgoing-* → bolha-falha`, mais robusto).
- Paleta `_CORES_AVATAR` mantida inalterada (identidade visual do cliente, não do tema).

**QA Agent (revisão final):** PASS
- Grep 0 ocorrências de todas as 15 cores antigas catalogadas
- Todas as classes CSS `<style>` mantêm os mesmos nomes (bolha-incoming, bolha-outgoing-bot, bolha-outgoing-humano, bolha-falha, bolha-label, conv-item, conv-item.ativo, scrollbar, fade-in, slide-in, pulse-red) — handlers JS continuam funcionando
- Caudas das 3 bolhas atualizadas: incoming #2b2b2b, bot #0d3875, humano #2481cc. Nova `.bolha-falha::before { display: none }` é melhoria além do scope (evita cauda azul gritante quando bolha vira vermelha)
- Nenhum handler JS foi alterado (fetch, SSE, addEventListener, lógica optimistic UI intacta)
- Todos os IDs DOM preservados
- Animações preservadas (pulseRing mantém rgba vermelha — semântica universal de urgência)
- Distinção visual clara: bot navy escuro vs humano azul Telegram brilhante
- Mobile responsivo preservado
- Toast/tag-selector/indicador entrega mantêm cores semânticas

**Ressalvas BAIXAS:**
- R1: Badge "Eu"/"Você" e "Com bot" usam `bg-[#2481cc]/20` Tailwind arbitrary opacity. CDN Play suporta. Em build futuro garantir JIT scan de strings JS.
- R2: `pulseRing` mantém rgba(239,68,68) — intencional (vermelho é semântica universal de urgência em qualquer paleta).

**Arquivos modificados:**
- `C:\Users\Home\.vscode\chatbot-barbearia\static\admin\index.html`
- `C:\Users\Home\.vscode\chatbot-barbearia\static\admin\login.html`
- `C:\Users\Home\.vscode\chatbot-barbearia\static\admin\atendentes.html`
- `C:\Users\Home\.vscode\chatbot-barbearia\static\admin\app.js`

**Status final:** DONE
