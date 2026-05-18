# User Stories — Interface de Atendente (Barbearia Bolshoi)

**Versão:** 1.0  
**Data:** 2026-05-17  
**Analista:** UX Analysis via Claude Code  
**Stack:** FastAPI + MySQL + Meta WhatsApp Cloud API + Vanilla JS  
**Modo:** Híbrido (bot IA + atendente humano)

---

## Índice por Área

1. [Autenticação](#1-autenticação)
2. [Sidebar — Métricas de Fila](#2-sidebar--métricas-de-fila)
3. [Sidebar — Filtros e Chips](#3-sidebar--filtros-e-chips)
4. [Sidebar — Busca de Conversas](#4-sidebar--busca-de-conversas)
5. [Sidebar — Lista de Conversas](#5-sidebar--lista-de-conversas)
6. [Sidebar — Estados Visuais](#6-sidebar--estados-visuais)
7. [Thread — Abertura de Conversa](#7-thread--abertura-de-conversa)
8. [Thread — Bolhas de Mensagem](#8-thread--bolhas-de-mensagem)
9. [Thread — Separadores de Data e Eventos](#9-thread--separadores-de-data-e-eventos)
10. [Thread — Header](#10-thread--header)
11. [Assumir Conversa](#11-assumir-conversa)
12. [Enviar Mensagem](#12-enviar-mensagem)
13. [Respostas Rápidas](#13-respostas-rápidas)
14. [Devolver ao Bot](#14-devolver-ao-bot)
15. [Compositor — 4 Estados](#15-compositor--4-estados)
16. [Painel de Info do Cliente](#16-painel-de-info-do-cliente)
17. [Notas Internas](#17-notas-internas)
18. [Tags de Conversa](#18-tags-de-conversa)
19. [SSE — Tempo Real](#19-sse--tempo-real)
20. [Notificações e Som](#20-notificações-e-som)
21. [Gestão de Atendentes](#21-gestão-de-atendentes)
22. [Responsividade Mobile](#22-responsividade-mobile)
23. [Erros de Rede e Resiliência](#23-erros-de-rede-e-resiliência)

---

## 1. Autenticação

### US-001: Login com credenciais válidas
**Como** atendente  
**Quero** entrar no painel com meu login e senha  
**Para** acessar o dashboard de atendimento

**Critérios de Aceite:**
- [ ] CA-01: POST `/admin/login` com `usuario_login` (lowercase forçado no frontend) e `senha`
- [ ] CA-02: Resposta 200 contém `token`, `nome`, `atendente_id`, `ultimo_login`
- [ ] CA-03: Token é salvo em `localStorage.setItem('token', data.token)`
- [ ] CA-04: `atendente_nome`, `atendente_id` e `ultimo_login` também são salvos no localStorage
- [ ] CA-05: Redirecionamento automático para `/static/admin/index.html` após login bem-sucedido
- [ ] CA-06: Campos têm `autocomplete="username"` e `autocomplete="current-password"` para gerenciadores de senha

**Estado atual:** IMPLEMENTADO  
**Arquivos relevantes:** `static/admin/login.html:39-72`, `api/admin.py:93-119`

---

### US-002: Login com credenciais inválidas
**Como** atendente  
**Quero** receber mensagem de erro clara ao digitar credenciais erradas  
**Para** saber que devo tentar novamente

**Critérios de Aceite:**
- [ ] CA-01: Backend retorna 401 com `detail: "Credenciais inválidas"` para senha errada, usuário inexistente ou conta inativa
- [ ] CA-02: Frontend exibe o `detail` da resposta dentro do elemento `#erro` (inicialmente `hidden`)
- [ ] CA-03: Elemento `#erro` tem classe visual `text-red-400 bg-red-900/30 border-red-800`
- [ ] CA-04: Erro some ao submeter novamente (`.classList.add('hidden')` antes de cada submit)
- [ ] CA-05: Nenhum redirecionamento ocorre em caso de erro

**Estado atual:** IMPLEMENTADO  
**Arquivos relevantes:** `static/admin/login.html:43-57`, `api/admin.py:109-112`

---

### US-003: Rate limit de login (5 tentativas / 60s por IP)
**Como** sistema  
**Quero** bloquear IPs após 5 tentativas de login em 60 segundos  
**Para** prevenir ataques de força bruta

**Critérios de Aceite:**
- [ ] CA-01: Após 5 tentativas falhas, backend retorna 429 com `detail: "Muitas tentativas. Tente novamente em 1 minuto."`
- [ ] CA-02: Frontend exibe a mensagem 429 no elemento `#erro` da mesma forma que 401
- [ ] CA-03: Rate limit é por IP (não por login), reinicia após 60 segundos
- [ ] CA-04: Tentativa bem-sucedida não é contada no rate limit (apenas falhas)

**Estado atual:** IMPLEMENTADO  
**Arquivos relevantes:** `api/admin.py:104-107`, `api/auth.py` (função `login_rate_limited`)

---

### US-004: JWT expirado redireciona para login
**Como** sistema  
**Quero** redirecionar o atendente para a tela de login quando o JWT expira  
**Para** garantir segurança de sessão

**Critérios de Aceite:**
- [ ] CA-01: Qualquer resposta 401 de qualquer endpoint executa `localStorage.clear()` e redireciona para `/static/admin/login.html`
- [ ] CA-02: Comportamento ocorre na função `api()` centralizada, afetando todos os endpoints
- [ ] CA-03: TTL padrão do JWT é 15 minutos (variável `JWT_TTL_MIN`)
- [ ] CA-04: Após redirect, localStorage está limpo (não persiste token expirado)

**Estado atual:** IMPLEMENTADO  
**Arquivos relevantes:** `static/admin/app.js:64-69`, `static/admin/atendentes.html:173-178`

---

### US-005: Logout manual
**Como** atendente  
**Quero** sair do painel clicando no botão de logout  
**Para** encerrar minha sessão com segurança

**Critérios de Aceite:**
- [ ] CA-01: Botão `#btn-sair` exibe `confirm('Sair do painel?')` antes de deslogar
- [ ] CA-02: Se confirmado, executa `localStorage.clear()` e redireciona para `login.html`
- [ ] CA-03: Se cancelado, nada acontece (permanece no painel)
- [ ] CA-04: Botão fica no header da sidebar com ícone de saída

**Estado atual:** IMPLEMENTADO  
**Arquivos relevantes:** `static/admin/app.js:573-577`, `static/admin/index.html:394-400`

---

### US-006: Exibição do último acesso
**Como** atendente  
**Quero** ver quando fiz meu último login  
**Para** identificar acessos não autorizados

**Critérios de Aceite:**
- [ ] CA-01: Backend retorna `ultimo_login` (ISO 8601) na resposta do login — contém o horário do login ANTERIOR (não o atual)
- [ ] CA-02: Frontend salva `ultimo_login` em localStorage e exibe no elemento `#ultimo-acesso` no footer da sidebar
- [ ] CA-03: Formato exibido: `Último acesso: DD/MM/AAAA às HH:mm`
- [ ] CA-04: Se `ultimo_login` é null (primeiro login), o elemento fica com `class="hidden"`
- [ ] CA-05: Erro de parse de data mantém o elemento oculto (tratamento defensivo)

**Estado atual:** IMPLEMENTADO  
**Arquivos relevantes:** `static/admin/app.js:28-45`, `static/admin/index.html:464`, `api/admin.py:114-115`

---

### US-007: Guard de autenticação no carregamento da página
**Como** sistema  
**Quero** redirecionar usuários não autenticados ao abrir qualquer página do painel  
**Para** impedir acesso sem login

**Critérios de Aceite:**
- [ ] CA-01: `app.js` verifica `localStorage.getItem('token')` imediatamente ao carregar
- [ ] CA-02: Se token ausente, redireciona para `login.html` sem carregar o restante do JS
- [ ] CA-03: Mesmo comportamento em `atendentes.html`
- [ ] CA-04: Guard não depende de validação do backend — é defesa client-side; validação real ocorre no servidor via JWT

**Estado atual:** IMPLEMENTADO  
**Arquivos relevantes:** `static/admin/app.js:16-23`, `static/admin/atendentes.html:153-158`

---

## 2. Sidebar — Métricas de Fila

### US-008: Exibição dos 3 cards de métricas
**Como** atendente  
**Quero** ver quantas conversas estão aguardando, em atendimento e com o bot  
**Para** ter visão instantânea do estado da fila

**Critérios de Aceite:**
- [ ] CA-01: Card "Aguardando" (`#metric-aguardando`): conta `conversas.filter(c => c.aguardando_humano === true).length`
- [ ] CA-02: Card "Atendendo" (`#metric-atendimento`): conta `conversas.filter(c => c.atendente_id !== null).length`
- [ ] CA-03: Card "Com bot" (`#metric-bot`): conta `conversas.filter(c => c.bot_ativo && !c.aguardando_humano).length`
- [ ] CA-04: Cards têm barra colorida lateral: vermelho (#ef4858) para aguardando, verde (#00a884) para atendendo, azul (#2481cc) para bot
- [ ] CA-05: Grid de 3 colunas (`#queue-metrics`), cada card com fundo `#233138`

**Estado atual:** IMPLEMENTADO  
**Arquivos relevantes:** `static/admin/app.js:343-350`, `static/admin/index.html:402-416`

---

### US-009: Atualização das métricas em tempo real
**Como** atendente  
**Quero** que os cards de métricas atualizem sem precisar recarregar a página  
**Para** sempre ver o estado atual da fila

**Critérios de Aceite:**
- [ ] CA-01: `atualizarMetricas()` é chamada toda vez que `carregarConversas()` é executada
- [ ] CA-02: `carregarConversas()` é chamada no bootstrap, a cada 30 segundos (`setInterval`) e ao receber eventos SSE
- [ ] CA-03: Eventos SSE `nova_mensagem`, `atendente_assumiu` e `bot_devolveu` disparam `carregarConversas()`
- [ ] CA-04: Números dos cards atualizam sem piscar ou causar layout shift

**Estado atual:** IMPLEMENTADO  
**Arquivos relevantes:** `static/admin/app.js:352-358`, `static/admin/app.js:1141-1144`

---

## 3. Sidebar — Filtros e Chips

### US-010: Filtro "Todas" as conversas
**Como** atendente  
**Quero** ver todas as conversas sem filtro ativo  
**Para** ter visão completa da fila

**Critérios de Aceite:**
- [ ] CA-01: Chip "Todas" é o ativo por padrão (classe `active-chip`)
- [ ] CA-02: Clicar em "Todas" limpa o valor do input `#filtro` e dispara evento `input`
- [ ] CA-03: `renderListaConversas()` exibe todas as conversas quando `filtro` está vazio

**Estado atual:** IMPLEMENTADO  
**Arquivos relevantes:** `static/admin/index.html:431`, `static/admin/index.html:1032-1044`

---

### US-011: Filtro por estado da conversa
**Como** atendente  
**Quero** filtrar conversas por "Aguardando", "Meus" ou "Com bot"  
**Para** focar no subconjunto relevante para minha tarefa

**Critérios de Aceite:**
- [ ] CA-01: Chip "Aguardando" (`data-filter="aguardando"`) filtra conversas onde `aguardando_humano=true`
- [ ] CA-02: Chip "Meus" (`data-filter="meus"`) filtra conversas onde `assumida_por_mim=true`
- [ ] CA-03: Chip "Com bot" (`data-filter="bot"`) filtra conversas onde `bot_ativo=true`
- [ ] CA-04: Ao clicar num chip, remove `active-chip` de todos os outros e adiciona no clicado
- [ ] CA-05: Filtro do chip é aplicado via `filtroInput.value = chip.dataset.filter` + evento `input`

**Estado atual:** PARCIAL — o filtro via chip dispara `renderListaConversas()` passando o valor do chip como string no input de busca, mas `renderListaConversas()` filtra apenas por nome/telefone (string genérica), não por estado boolean. Chips "aguardando", "meus" e "bot" não filtram corretamente a menos que o nome ou telefone do cliente contenha essas strings.  
**Arquivos relevantes:** `static/admin/index.html:1032-1044`, `static/admin/app.js:275-281`

---

## 4. Sidebar — Busca de Conversas

### US-012: Busca por nome do cliente
**Como** atendente  
**Quero** digitar o nome de um cliente para encontrar sua conversa  
**Para** acessar rapidamente um atendimento específico

**Critérios de Aceite:**
- [ ] CA-01: Input `#filtro` filtra em tempo real (evento `input`) sem debounce
- [ ] CA-02: Filtro é case-insensitive: `(c.nome || '').toLowerCase().includes(filtro)`
- [ ] CA-03: Correspondência parcial é aceita (não precisa ser exata)
- [ ] CA-04: Placeholder: "Buscar por nome ou telefone…"

**Estado atual:** IMPLEMENTADO  
**Arquivos relevantes:** `static/admin/app.js:271-281`, `static/admin/index.html:424`

---

### US-013: Busca por número de telefone
**Como** atendente  
**Quero** digitar o telefone de um cliente para encontrar sua conversa  
**Para** localizar atendimentos por número de WhatsApp

**Critérios de Aceite:**
- [ ] CA-01: Filtro também verifica `c.telefone.includes(filtro)` (case-sensitive pois telefones são numéricos)
- [ ] CA-02: Correspondência parcial funciona (ex.: "5538" encontra "553899...")
- [ ] CA-03: Busca ocorre junto com busca por nome (OR lógico, não AND)

**Estado atual:** IMPLEMENTADO  
**Arquivos relevantes:** `static/admin/app.js:277-279`

---

### US-014: Busca sem resultado
**Como** atendente  
**Quero** ver uma mensagem quando nenhuma conversa corresponde ao filtro  
**Para** saber que a busca foi executada mas não encontrou resultados

**Critérios de Aceite:**
- [ ] CA-01: Quando `visiveis.length === 0` e há filtro ativo, exibe: "Nenhuma conversa encontrada"
- [ ] CA-02: Quando `visiveis.length === 0` e não há filtro, exibe: "Sem conversas ainda"
- [ ] CA-03: Texto é exibido como `<li>` centralizado com texto cinza
- [ ] CA-04: Lista fica vazia (sem itens fantasma)

**Estado atual:** IMPLEMENTADO  
**Arquivos relevantes:** `static/admin/app.js:280-286`

---

## 5. Sidebar — Lista de Conversas

### US-015: Ordenação da lista (aguardando primeiro)
**Como** atendente  
**Quero** ver as conversas que aguardam atendimento humano no topo da lista  
**Para** priorizar corretamente meu trabalho

**Critérios de Aceite:**
- [ ] CA-01: Backend ordena via `ORDER BY usuarios.aguardando_humano DESC, usuarios.data_ultima_interacao DESC`
- [ ] CA-02: Clientes com `aguardando_humano=true` aparecem antes de todos os demais
- [ ] CA-03: Dentro do mesmo estado, conversas mais recentes aparecem primeiro
- [ ] CA-04: Limite de 200 conversas por carregamento

**Estado atual:** IMPLEMENTADO  
**Arquivos relevantes:** `api/admin.py:144-151`

---

### US-016: Avatar gerado deterministicamente
**Como** atendente  
**Quero** ver um avatar colorido com as iniciais do cliente na lista  
**Para** identificar visualmente cada conversa

**Critérios de Aceite:**
- [ ] CA-01: Cor é derivada do nome do cliente via hash determinístico (`_hashStr`) — mesma cor sempre para o mesmo nome
- [ ] CA-02: Se nome não disponível, usa telefone como fonte do hash
- [ ] CA-03: Paleta de 12 cores (`_CORES_AVATAR`) via inline style (não classe Tailwind)
- [ ] CA-04: Iniciais mostram até 2 letras (primeira letra do primeiro e segundo nomes)
- [ ] CA-05: Avatar é `w-10 h-10` (estilizado para 48px via CSS override em `#lista-conversas`)

**Estado atual:** IMPLEMENTADO  
**Arquivos relevantes:** `static/admin/app.js:88-117`, `static/admin/index.html:191-194`

---

### US-017: Preview da última mensagem truncado
**Como** atendente  
**Quero** ver um trecho da última mensagem de cada conversa na sidebar  
**Para** ter contexto antes de abrir a conversa

**Critérios de Aceite:**
- [ ] CA-01: Backend gera preview de no máximo 60 caracteres, truncando com "…"
- [ ] CA-02: Tags `<br>` são removidas do preview (substituídas por espaço)
- [ ] CA-03: Frontend aplica defesa adicional: se `preview.length > 60`, trunca com `…`
- [ ] CA-04: Preview exibido em texto cinza (`text-[#aaaaaa]`) abaixo do nome

**Estado atual:** IMPLEMENTADO  
**Arquivos relevantes:** `api/admin.py:176-183`, `static/admin/app.js:311-313`

---

### US-018: Tempo relativo da última mensagem
**Como** atendente  
**Quero** ver há quanto tempo foi a última mensagem de cada conversa  
**Para** identificar conversas stale ou urgentes

**Critérios de Aceite:**
- [ ] CA-01: < 45s → "agora"; < 90s → "1min"; < 1h → "Xmin"; < 2h → "1h"; < 24h → "Xh"
- [ ] CA-02: < 48h → "ontem"; < 7d → "Xd"; ≥ 7d → "DD/MM"
- [ ] CA-03: Para conversas com `aguardando_humano=true`, o timestamp fica vermelho (`#ef4858`) e negrito via CSS `:has()`
- [ ] CA-04: Labels de tempo são re-renderizados a cada 60 segundos via `setInterval`

**Estado atual:** IMPLEMENTADO  
**Arquivos relevantes:** `static/admin/app.js:120-132`, `static/admin/index.html:69-72`, `static/admin/app.js:1146-1150`

---

### US-019: Conversa ativa destacada na sidebar
**Como** atendente  
**Quero** ver qual conversa está aberta atualmente destacada na lista  
**Para** saber minha posição de contexto

**Critérios de Aceite:**
- [ ] CA-01: Item com `conversaAtual === c.telefone` recebe classe `ativo`
- [ ] CA-02: Classe `ativo` aplica fundo `#2a3942` e barra lateral azul de 4px (`#2481cc`)
- [ ] CA-03: Hover em itens não ativos aplica fundo `rgba(255,255,255,0.02)`
- [ ] CA-04: Destaque atualiza imediatamente ao clicar em outro item

**Estado atual:** IMPLEMENTADO  
**Arquivos relevantes:** `static/admin/app.js:289-315`, `static/admin/index.html:56-67`

---

## 6. Sidebar — Estados Visuais

### US-020: Ponto vermelho pulsante (aguardando atendente)
**Como** atendente  
**Quero** ver uma sinalização visual urgente em conversas aguardando atendimento  
**Para** identificar imediatamente quem precisa de atenção

**Critérios de Aceite:**
- [ ] CA-01: Quando `aguardando_humano=true`: ponto vermelho (`#ef4444`) com animação `pulse-red` (ring pulsante via `box-shadow`)
- [ ] CA-02: `title` do ponto: "Aguardando atendente"
- [ ] CA-03: Nome do cliente fica em `font-bold text-white` (destaque adicional)
- [ ] CA-04: Animação: `pulseRing` 1.6s ease-out infinite

**Estado atual:** IMPLEMENTADO  
**Arquivos relevantes:** `static/admin/app.js:299-301`, `static/admin/index.html:23-28`

---

### US-021: Ponto azul (atendendo você)
**Como** atendente  
**Quero** ver um indicador azul nas conversas que estou atendendo  
**Para** identificar minhas conversas ativas

**Critérios de Aceite:**
- [ ] CA-01: Quando `assumida_por_mim=true` (e não aguardando): ponto azul Telegram (`#2481cc`)
- [ ] CA-02: `title` do ponto: "Atendendo você"
- [ ] CA-03: Sem animação (estado estável)

**Estado atual:** IMPLEMENTADO  
**Arquivos relevantes:** `static/admin/app.js:302-304`

---

### US-022: Ponto cinza claro (outro operador)
**Como** atendente  
**Quero** ver um indicador cinza claro em conversas atendidas por outro operador  
**Para** saber que não devo interferir

**Critérios de Aceite:**
- [ ] CA-01: Quando `atendente_id !== null` e `assumida_por_mim=false`: ponto `#aaaaaa`
- [ ] CA-02: `title` do ponto: "Em atendimento por outro operador"
- [ ] CA-03: Sem animação

**Estado atual:** IMPLEMENTADO  
**Arquivos relevantes:** `static/admin/app.js:305-307`

---

### US-023: Ponto verde (bot ativo)
**Como** atendente  
**Quero** ver um indicador verde em conversas onde o bot está respondendo  
**Para** saber que a IA está ativa e não preciso intervir

**Critérios de Aceite:**
- [ ] CA-01: Quando `bot_ativo=true` e não aguardando: ponto `#10b981`
- [ ] CA-02: `title` do ponto: "Bot ativo"

**Estado atual:** IMPLEMENTADO  
**Arquivos relevantes:** `static/admin/app.js:308-310`

---

### US-024: Ponto cinza neutro (estado padrão / desconhecido)
**Como** atendente  
**Quero** ver um ponto neutro em conversas sem estado definido  
**Para** diferenciar de estados com significado específico

**Critérios de Aceite:**
- [ ] CA-01: Estado padrão (`dotColor = '#636e72'`) quando nenhuma das condições anteriores se aplica
- [ ] CA-02: `title` do ponto: "Atendido pelo bot"

**Estado atual:** IMPLEMENTADO  
**Arquivos relevantes:** `static/admin/app.js:298-299`

---

## 7. Thread — Abertura de Conversa

### US-025: Abrir conversa ao clicar na sidebar
**Como** atendente  
**Quero** clicar em uma conversa na sidebar para ver o histórico completo  
**Para** iniciar ou acompanhar um atendimento

**Critérios de Aceite:**
- [ ] CA-01: Click no item da sidebar chama `abrirConversa(c.telefone)`
- [ ] CA-02: `conversaAtual` é atualizado e sidebar re-renderizada (destaque no item)
- [ ] CA-03: GET `/admin/conversa/{telefone}` é chamado com token Bearer
- [ ] CA-04: Resposta contém `{usuario, mensagens}` — até 500 mensagens em ordem cronológica
- [ ] CA-05: Thread renderiza header, bolhas e footer de acordo com o estado do usuário

**Estado atual:** IMPLEMENTADO  
**Arquivos relevantes:** `static/admin/app.js:364-387`, `api/admin.py:202-241`

---

### US-026: Scroll automático para a última mensagem
**Como** atendente  
**Quero** que a thread role automaticamente para a mensagem mais recente ao abrir  
**Para** começar a leitura pelo contexto mais atual

**Critérios de Aceite:**
- [ ] CA-01: `scrollarFim()` é chamado ao final de `renderThread()`
- [ ] CA-02: Usa `requestAnimationFrame` duplo para garantir que o layout termine antes de medir `scrollHeight`
- [ ] CA-03: Em threads com muitas mensagens, o scroll vai ao fundo corretamente

**Estado atual:** IMPLEMENTADO  
**Arquivos relevantes:** `static/admin/app.js:547-559`, `static/admin/app.js:464`

---

### US-027: Estado vazio — nenhuma mensagem ainda
**Como** atendente  
**Quero** ver uma mensagem explicativa quando uma conversa não tem histórico  
**Para** entender que o cliente ainda não enviou mensagens

**Critérios de Aceite:**
- [ ] CA-01: Quando `data.mensagens.length === 0`, exibe div centralizada com texto "Nenhuma mensagem ainda"
- [ ] CA-02: Texto com classe `text-sm text-[#aaaaaa]`
- [ ] CA-03: Nenhuma bolha é renderizada

**Estado atual:** IMPLEMENTADO  
**Arquivos relevantes:** `static/admin/app.js:437-443`

---

### US-028: Estado vazio do dashboard (sem conversa selecionada)
**Como** atendente  
**Quero** ver uma tela de boas-vindas quando nenhuma conversa está selecionada  
**Para** ter orientação visual antes de iniciar o trabalho

**Critérios de Aceite:**
- [ ] CA-01: Elemento `#empty-state` com ícone de barbearia (`💈`), título "Barbearia Bolshoi" e instrução "Selecione uma conversa para começar o atendimento"
- [ ] CA-02: Thread header fica oculto (`hidden`) quando nenhuma conversa está aberta
- [ ] CA-03: Thread footer fica oculto quando nenhuma conversa está aberta

**Estado atual:** IMPLEMENTADO  
**Arquivos relevantes:** `static/admin/index.html:552-557`

---

### US-029: Painel de info abre automaticamente em desktop ao abrir conversa
**Como** atendente (desktop)  
**Quero** ver o painel de informações do cliente abrir automaticamente ao selecionar uma conversa  
**Para** ter contexto do cliente disponível sem ação adicional

**Critérios de Aceite:**
- [ ] CA-01: Se `window.innerWidth >= 1024`, `abrirInfoPanel()` é chamado ao abrir conversa
- [ ] CA-02: Em telas menores, painel fica disponível mas recolhido (usuário abre manualmente)
- [ ] CA-03: Override via inline script (`_blockInfoPanelAutoOpen`) impede abertura automática e exige ação manual mesmo em desktop — comportamento atual é manual-only

**Estado atual:** PARCIAL — código em `app.js` tenta abrir automaticamente em desktop, mas inline script em `index.html` intercepta `abrirInfoPanel()` e mantém painel recolhido. Painel só abre via clique no header da thread ou botão de toggle.  
**Arquivos relevantes:** `static/admin/app.js:378-386`, `static/admin/index.html:771-793`

---

## 8. Thread — Bolhas de Mensagem

### US-030: Bolha do cliente (incoming)
**Como** atendente  
**Quero** ver as mensagens do cliente em bolhas à esquerda  
**Para** distinguir claramente o remetente

**Critérios de Aceite:**
- [ ] CA-01: `origem === 'cliente'`: classe `bolha-incoming` (fundo `#202c33`), alinhamento `justify-start`
- [ ] CA-02: Label "Cliente" em `text-[#e9b884]` (âmbar)
- [ ] CA-03: Texto em branco, `whitespace-pre-wrap`
- [ ] CA-04: Horário exibido no rodapé da bolha (sem indicador de entrega)

**Estado atual:** IMPLEMENTADO  
**Arquivos relevantes:** `static/admin/app.js:506-543`, `static/admin/index.html:206-218`

---

### US-031: Bolha do bot (outgoing-bot)
**Como** atendente  
**Quero** ver as respostas do bot em bolhas à direita com cor diferenciada  
**Para** identificar o que foi respondido pela IA

**Critérios de Aceite:**
- [ ] CA-01: `origem === 'bot'`: classe `bolha-outgoing-bot` (fundo `#04473b`, verde escuro), alinhamento `justify-end`
- [ ] CA-02: Label "Bot" em `text-[#7fe3c4]` (verde menta)
- [ ] CA-03: Tags `<br>` convertidas para `\n` antes de renderizar: `m.resposta.replace(/<\s*br\s*\/?>/gi, '\n')`

**Estado atual:** IMPLEMENTADO  
**Arquivos relevantes:** `static/admin/app.js:456-458`, `static/admin/index.html:220-231`

---

### US-032: Bolha do atendente (outgoing-humano)
**Como** atendente  
**Quero** ver minhas mensagens em bolhas à direita com cor azul  
**Para** identificar minha contribuição no histórico

**Critérios de Aceite:**
- [ ] CA-01: `origem === 'humano'`: classe `bolha-outgoing-humano` (fundo `#1d3d5c`, azul), alinhamento `justify-end`
- [ ] CA-02: Label "Atendente" em `text-[#d6e8fa]` (azul claro)

**Estado atual:** IMPLEMENTADO  
**Arquivos relevantes:** `static/admin/app.js:515-516`, `static/admin/index.html:234-246`

---

### US-033: Bolha de falha (vermelha com borda)
**Como** atendente  
**Quero** ver indicação visual clara quando uma mensagem não foi entregue ao cliente  
**Para** saber que preciso tentar novamente

**Critérios de Aceite:**
- [ ] CA-01: Quando `entregue === false` em bolha outgoing: classe `bolha-falha` (fundo vermelho semitransparente, borda `#cc3333`)
- [ ] CA-02: `bolha-falha::before { display: none }` — cauda oculta pois não combina com fundo vermelho
- [ ] CA-03: Indicador `⚠ não entregue` em `text-red-500` no rodapé da bolha

**Estado atual:** IMPLEMENTADO  
**Arquivos relevantes:** `static/admin/app.js:519-521`, `static/admin/index.html:45-48`

---

### US-034: Cauda nas bolhas (primeira da sequência)
**Como** atendente  
**Quero** que apenas a primeira bolha de cada grupo tenha cauda  
**Para** ter a experiência visual fiel ao WhatsApp

**Critérios de Aceite:**
- [ ] CA-01: `bolha-incoming::before` cria cauda triangular à esquerda
- [ ] CA-02: CSS `:has()` oculta cauda em bolhas incoming precedidas por outra incoming
- [ ] CA-03: Mesma lógica para `bolha-outgoing-bot` e `bolha-outgoing-humano` à direita
- [ ] CA-04: Compatibilidade: Chrome 105+, Firefox 121+, Safari 15.4+

**Estado atual:** IMPLEMENTADO  
**Arquivos relevantes:** `static/admin/index.html:202-246`

---

### US-035: Chip de mídia (áudio, imagem, documento)
**Como** atendente  
**Quero** ver um chip identificador quando o cliente enviou mídia  
**Para** saber que há conteúdo que não pode ser exibido no painel

**Critérios de Aceite:**
- [ ] CA-01: Mensagens com prefixo `MÍDIA_` (ex.: `MÍDIA_audio`, `MÍDIA_image`, `MÍDIA_document`) renderizam chip visual
- [ ] CA-02: Chips: `🎵 Áudio`, `🖼️ Imagem`, `📎 Documento`, `📁 Mídia` (fallback)
- [ ] CA-03: Chip tem fundo `#2b2b2b` e texto `#aaaaaa`, formatado como pill
- [ ] CA-04: Não exibe `escapeHtml(texto)` bruto quando for mídia

**Estado atual:** IMPLEMENTADO  
**Arquivos relevantes:** `static/admin/app.js:487-498`

---

### US-036: Indicador de entrega nas bolhas outgoing
**Como** atendente  
**Quero** ver o status de entrega de cada mensagem enviada  
**Para** confirmar se a mensagem chegou ao cliente

**Critérios de Aceite:**
- [ ] CA-01: `entregue === true`: `✓` azul com `title="Entregue ao WhatsApp"`
- [ ] CA-02: `entregue === false`: `⚠ não entregue` vermelho com tooltip detalhando possíveis causas
- [ ] CA-03: `entregue === null/undefined`: sem indicador
- [ ] CA-04: Indicador não é exibido em bolhas do cliente (incoming)

**Estado atual:** IMPLEMENTADO  
**Arquivos relevantes:** `static/admin/app.js:474-484`

---

## 9. Thread — Separadores de Data e Eventos

### US-037: Separador "Hoje"
**Como** atendente  
**Quero** ver o separador "Hoje" antes das mensagens do dia atual  
**Para** ter referência temporal no histórico

**Critérios de Aceite:**
- [ ] CA-01: `dataLabel(iso)` retorna "Hoje" quando a data da mensagem é o dia atual
- [ ] CA-02: Comparação usa `toLocaleDateString('pt-BR')` para evitar problemas de timezone
- [ ] CA-03: Separador é pill centralizado: `bg-[#2b2b2b] border border-[#3a3a3a] px-3 py-0.5 rounded-full`

**Estado atual:** IMPLEMENTADO  
**Arquivos relevantes:** `static/admin/app.js:160-169`, `static/admin/app.js:467-471`

---

### US-038: Separador "Ontem" e data longa
**Como** atendente  
**Quero** ver separadores de data para dias anteriores  
**Para** navegar temporalmente no histórico

**Critérios de Aceite:**
- [ ] CA-01: Data de ontem → "Ontem"
- [ ] CA-02: Outros dias → formato `{ weekday: 'long', day: '2-digit', month: 'long' }` (ex.: "segunda-feira, 12 de maio")
- [ ] CA-03: Separador renderizado apenas quando o dia muda entre mensagens consecutivas

**Estado atual:** IMPLEMENTADO  
**Arquivos relevantes:** `static/admin/app.js:160-169`

---

### US-039: Separador de evento inline (handoff)
**Como** atendente  
**Quero** ver separadores visuais no histórico quando o atendimento passou de bot para humano ou vice-versa  
**Para** entender o fluxo do atendimento

**Critérios de Aceite:**
- [ ] CA-01: Elemento com classe `event-separator` renderiza linha horizontal com texto central
- [ ] CA-02: Dots (`event-separator-dot`) aparecem antes e depois do texto
- [ ] CA-03: Estilos definidos via CSS (não Tailwind): flexbox, linhas `#2a3942`, texto `#8696a0`
- [ ] CA-04: Exemplos no HTML preview: "Atendimento transferido para humano · Diego assumiu", "Conversa devolvida para o bot · Diego encerrou o atendimento"

**Estado atual:** PARCIAL — estrutura CSS e HTML preview existem, mas `renderThread()` em `app.js` não injeta separadores de evento baseados nos dados do backend. O backend não retorna metadados de handoff como eventos separados na lista de mensagens.  
**Arquivos relevantes:** `static/admin/index.html:276-303`, `static/admin/index.html:577-595`, `static/admin/app.js:431-464`

---

### US-040: Separador de data em mensagens incrementais (SSE)
**Como** atendente  
**Quero** que o separador de data apareça corretamente quando uma nova mensagem chega à meia-noite  
**Para** manter a organização temporal mesmo durante atendimentos longos

**Critérios de Aceite:**
- [ ] CA-01: `appendMensagemIncremental()` verifica `ultimoSeparadorLabel()` antes de inserir a nova bolha
- [ ] CA-02: Se o label do dia mudou, insere novo separador antes da bolha
- [ ] CA-03: Comparação usa `dataLabel(new Date().toISOString())`

**Estado atual:** IMPLEMENTADO  
**Arquivos relevantes:** `static/admin/app.js:852-868`

---

## 10. Thread — Header

### US-041: Header com avatar, nome e telefone
**Como** atendente  
**Quero** ver as informações básicas do cliente no topo da thread  
**Para** confirmar com quem estou conversando

**Critérios de Aceite:**
- [ ] CA-01: `#thread-avatar` contém avatar gerado (mesmo algoritmo de cor/iniciais da sidebar)
- [ ] CA-02: `#thread-nome` exibe `nome || telefone`
- [ ] CA-03: `#thread-telefone` exibe o número de telefone
- [ ] CA-04: Clique na área do cliente (`#thread-customer`) abre o painel de info (cursor pointer)
- [ ] CA-05: Header fica `hidden` até a primeira conversa ser aberta

**Estado atual:** IMPLEMENTADO  
**Arquivos relevantes:** `static/admin/app.js:389-428`, `static/admin/index.html:1007-1018`

---

### US-042: Status text colorido por estado
**Como** atendente  
**Quero** ver o status da conversa em texto colorido no header  
**Para** entender rapidamente minha relação com a conversa

**Critérios de Aceite:**
- [ ] CA-01: Estado `voce` → "Você está atendendo essa conversa." (verde `text-emerald-400`)
- [ ] CA-02: Estado `aguardando` → "Cliente aguardando atendente humano." (vermelho `text-red-400`)
- [ ] CA-03: Estado `bot_ativo` → "Bot ativo. Você pode assumir a conversa." (azul `text-[#2481cc]`)
- [ ] CA-04: Estado `outro` → "Em atendimento por outro operador." (cinza `text-[#aaaaaa]`)
- [ ] CA-05: CSS adicional via `data-state` attribute no `#thread-status`

**Estado atual:** IMPLEMENTADO  
**Arquivos relevantes:** `static/admin/app.js:406-428`, `static/admin/index.html:361-364`

---

### US-043: Botões condicionais no header
**Como** atendente  
**Quero** ver apenas os botões relevantes ao estado atual da conversa  
**Para** evitar ações inválidas

**Critérios de Aceite:**
- [ ] CA-01: Estado `voce`: botão "Devolver a IA" visível; "Assumir" e "Interromper bot" ocultos
- [ ] CA-02: Estado `aguardando`: botão "Assumir" visível
- [ ] CA-03: Estado `bot_ativo`: botão "Interromper bot" visível (verde), "Assumir" oculto
- [ ] CA-04: Estado `outro`: nenhum botão de ação visível
- [ ] CA-05: Botão de tag (ícone label) sempre visível quando conversa está aberta

**Estado atual:** IMPLEMENTADO  
**Arquivos relevantes:** `static/admin/app.js:399-428`, `static/admin/index.html:908-934`

---

## 11. Assumir Conversa

### US-044: Assumir conversa com sucesso
**Como** atendente  
**Quero** clicar em "Assumir" para tomar controle de uma conversa  
**Para** atender o cliente diretamente

**Critérios de Aceite:**
- [ ] CA-01: POST `/admin/assumir/{telefone}` com token Bearer
- [ ] CA-02: Backend executa UPDATE condicional: `atendente_id IS NULL` como condição
- [ ] CA-03: Sets: `atendente_id=me.id`, `bot_ativo=False`, `bot_desativado_em=now()`, `aguardando_humano=False`
- [ ] CA-04: Backend envia mensagem de boas-vindas automática ao cliente via WhatsApp
- [ ] CA-05: Frontend recarrega conversas e reabre a thread para atualizar estado
- [ ] CA-06: Toast verde: "Conversa assumida com sucesso."
- [ ] CA-07: Botão "Assumir" desabilitado durante a requisição para evitar cliques duplos

**Estado atual:** IMPLEMENTADO  
**Arquivos relevantes:** `static/admin/app.js:656-669`, `api/admin.py:244-305`

---

### US-045: Mensagem de boas-vindas enviada ao assumir
**Como** sistema  
**Quero** enviar uma mensagem de apresentação ao cliente quando um atendente assume  
**Para** o cliente saber que um humano está cuidando do atendimento

**Critérios de Aceite:**
- [ ] CA-01: Texto fixo: `"👋 Olá! Sou {nome_atendente}, do atendimento da Barbearia Bolshoi. Vou te ajudar a partir de agora."`
- [ ] CA-02: Mensagem é salva em `HistoricoConversa` com `origem='humano'` e `entregue=bool(ok)`
- [ ] CA-03: Evento SSE `nova_mensagem` é publicado para todos os atendentes conectados
- [ ] CA-04: Evento SSE `atendente_assumiu` também é publicado

**Estado atual:** IMPLEMENTADO  
**Arquivos relevantes:** `api/admin.py:278-304`

---

### US-046: Race condition ao assumir (409)
**Como** sistema  
**Quero** que apenas um atendente consiga assumir uma conversa simultaneamente  
**Para** evitar conflitos de atendimento duplo

**Critérios de Aceite:**
- [ ] CA-01: UPDATE condicional com `atendente_id IS NULL` — apenas o primeiro request vence
- [ ] CA-02: Se `afetadas == 0` e `user.atendente_id != me.id`: 409 "Outro atendente assumiu essa conversa antes de você."
- [ ] CA-03: Se `user.atendente_id` já é de outro: 409 "Conversa já assumida por outro atendente."
- [ ] CA-04: Frontend exibe o erro 409 via toast vermelho (`transbordo`)

**Estado atual:** IMPLEMENTADO  
**Arquivos relevantes:** `api/admin.py:257-276`, `static/admin/app.js:664-666`

---

### US-047: Tentar assumir conversa já assumida por mim mesmo
**Como** atendente  
**Quero** que o sistema ignore silenciosamente o clique em "Assumir" numa conversa já minha  
**Para** não gerar erro desnecessário

**Critérios de Aceite:**
- [ ] CA-01: Backend verifica `user.atendente_id and user.atendente_id != me.id` — se já é minha, não lança 409
- [ ] CA-02: UPDATE com `atendente_id IS NULL` falhará (afetadas=0), mas como `user.atendente_id == me.id`, não lança erro
- [ ] CA-03: Frontend re-abre a conversa e exibe toast de sucesso normalmente

**Estado atual:** IMPLEMENTADO  
**Arquivos relevantes:** `api/admin.py:257-276`

---

## 12. Enviar Mensagem

### US-048: Enviar mensagem de texto livre
**Como** atendente  
**Quero** digitar e enviar uma mensagem para o cliente  
**Para** continuar o atendimento humano

**Critérios de Aceite:**
- [ ] CA-01: POST `/admin/enviar/{telefone}` com `{texto}`, validado como min 1 / max 4096 caracteres
- [ ] CA-02: Texto normalizado: `\n{3,}` colapsado para `\n\n`, stripped
- [ ] CA-03: Mensagem salva em DB com `origem='humano'`, `atendente_id=me.id`
- [ ] CA-04: Resposta: `{status: "ok", entregue: bool}`

**Estado atual:** IMPLEMENTADO  
**Arquivos relevantes:** `api/admin.py:308-343`, `static/admin/app.js:708-776`

---

### US-049: Enviar com tecla Enter (Shift+Enter para nova linha)
**Como** atendente  
**Quero** pressionar Enter para enviar e Shift+Enter para quebrar linha  
**Para** ter atalho de teclado natural similar ao WhatsApp

**Critérios de Aceite:**
- [ ] CA-01: `keydown` em `#texto-msg`: `Enter` sem `shiftKey` e sem `isComposing` → `form.requestSubmit()`
- [ ] CA-02: `Shift+Enter` insere quebra de linha (comportamento padrão do textarea)
- [ ] CA-03: `isComposing` evita envio acidental durante composição de caracteres (IME para idiomas asiáticos)

**Estado atual:** IMPLEMENTADO  
**Arquivos relevantes:** `static/admin/app.js:697-702`

---

### US-050: Envio otimista (bolha aparece imediatamente)
**Como** atendente  
**Quero** ver minha mensagem aparecer instantaneamente na thread  
**Para** não esperar a confirmação do servidor para continuar digitando

**Critérios de Aceite:**
- [ ] CA-01: Bolha com `pending=true` aparece antes da resposta do servidor (opacidade 60%)
- [ ] CA-02: `tempId` gerado: `'temp-' + Date.now() + '-' + Math.random()`
- [ ] CA-03: Campo limpo e botão desabilitado imediatamente após submit
- [ ] CA-04: Em caso de sucesso, opacidade sobe para 100% e indicador muda de "enviando…" para `✓`
- [ ] CA-05: Em caso de falha, bolha fica vermelha (bolha-falha) com opção de retry

**Estado atual:** IMPLEMENTADO  
**Arquivos relevantes:** `static/admin/app.js:708-776`

---

### US-051: Bloqueio de envio com campo vazio
**Como** sistema  
**Quero** impedir o envio de mensagens vazias  
**Para** não gerar erros desnecessários no backend

**Critérios de Aceite:**
- [ ] CA-01: `textarea.value.trim()` vazio → função retorna sem submeter
- [ ] CA-02: Campo tem atributo `required` no formulário
- [ ] CA-03: Backend valida `min_length=1` em `EnviarMensagemIn`

**Estado atual:** IMPLEMENTADO  
**Arquivos relevantes:** `static/admin/app.js:711`, `api/admin.py:64`

---

### US-052: Bloqueio de envio por 403 (não é dono da conversa)
**Como** sistema  
**Quero** impedir que atendentes enviem mensagens em conversas de outros  
**Para** garantir isolamento entre atendimentos

**Critérios de Aceite:**
- [ ] CA-01: Backend verifica `user.atendente_id != me.id` → 403 "Você não assumiu essa conversa."
- [ ] CA-02: Frontend também bloqueia via estado `compositor-inativo`: captura submit em fase capture e chama `preventDefault()` antes do handler do `app.js`
- [ ] CA-03: Toast vermelho exibe erro de rede

**Estado atual:** IMPLEMENTADO  
**Arquivos relevantes:** `api/admin.py:318-319`, `static/admin/index.html:995-1005`

---

### US-053: Textarea com auto-resize
**Como** atendente  
**Quero** que o campo de mensagem cresça automaticamente com o texto  
**Para** ter boa experiência ao escrever mensagens longas

**Critérios de Aceite:**
- [ ] CA-01: `autoResize()` ajusta `textarea.style.height` para `Math.min(scrollHeight, 120)px`
- [ ] CA-02: Altura inicia em 1 linha (`rows="1"`)
- [ ] CA-03: Máximo visual de 120px (não cresce indefinidamente)
- [ ] CA-04: `field-sizing: content` como suporte nativo onde disponível

**Estado atual:** IMPLEMENTADO  
**Arquivos relevantes:** `static/admin/app.js:691-696`, `static/admin/index.html:626-627`

---

## 13. Respostas Rápidas

### US-054: Abrir popover de respostas rápidas
**Como** atendente  
**Quero** clicar no ícone de raio para ver uma lista de respostas pré-definidas  
**Para** responder rapidamente sem digitar textos comuns

**Critérios de Aceite:**
- [ ] CA-01: Botão `#btn-rapidas` (ícone raio) faz toggle do `#popover-rapidas`
- [ ] CA-02: Popover ancorado acima do botão: `bottom-16 left-4`
- [ ] CA-03: Largura `w-72`, fundo `#202c33`, borda `#2a3942`, `rounded-xl`
- [ ] CA-04: Título "Respostas rápidas" em maiúsculas no topo do popover

**Estado atual:** IMPLEMENTADO  
**Arquivos relevantes:** `static/admin/app.js:626-629`, `static/admin/index.html:602-606`

---

### US-055: Selecionar resposta rápida
**Como** atendente  
**Quero** clicar em uma resposta pré-definida para preenchê-la no campo de mensagem  
**Para** agilizar o atendimento

**Critérios de Aceite:**
- [ ] CA-01: Clique no item preenche `textarea.value = texto` e fecha o popover
- [ ] CA-02: `autoResize()` é chamado para ajustar altura
- [ ] CA-03: Foco é retornado ao textarea automaticamente
- [ ] CA-04: 8 respostas rápidas pré-definidas: saudação, obrigado, AppBarber, endereço, aguarde, mais alguma coisa, encerramento, dúvidas WhatsApp

**Estado atual:** IMPLEMENTADO  
**Arquivos relevantes:** `static/admin/app.js:604-619`

---

### US-056: Fechar popover ao clicar fora
**Como** atendente  
**Quero** que o popover de respostas rápidas feche ao clicar em qualquer área fora dele  
**Para** não precisar apertar um botão de fechar

**Critérios de Aceite:**
- [ ] CA-01: Listener no `document` verifica se o clique foi fora do popover e fora do botão de toggle
- [ ] CA-02: Popover não fecha se o clique foi dentro dele
- [ ] CA-03: Popover não fecha se o clique foi no botão `#btn-rapidas`

**Estado atual:** IMPLEMENTADO  
**Arquivos relevantes:** `static/admin/app.js:631-637`

---

## 14. Devolver ao Bot

### US-057: Devolver conversa ao bot com confirmação
**Como** atendente  
**Quero** encerrar meu atendimento e devolver a conversa ao bot  
**Para** liberar minha atenção e deixar a IA continuar

**Critérios de Aceite:**
- [ ] CA-01: Botão `#btn-devolver` exibe `confirm('Devolver essa conversa para a IA? O cliente será avisado.')`
- [ ] CA-02: POST `/admin/devolver/{telefone}` se confirmado
- [ ] CA-03: UPDATE condicional: `atendente_id == me.id` como condição → sets `atendente_id=None`, `bot_ativo=True`, `aguardando_humano=False`
- [ ] CA-04: Mensagem de despedida enviada ao cliente: "Atendimento humano encerrado. O assistente virtual está de volta..."
- [ ] CA-05: Toast verde: "Bot voltou ao atendimento."
- [ ] CA-06: Botão desabilitado durante a requisição

**Estado atual:** IMPLEMENTADO  
**Arquivos relevantes:** `static/admin/app.js:671-685`, `api/admin.py:346-405`

---

### US-058: Erro ao devolver (409)
**Como** sistema  
**Quero** retornar erro se o atendente tentar devolver conversa que não é sua  
**Para** prevenir liberações indevidas

**Critérios de Aceite:**
- [ ] CA-01: `afetadas == 0` (ninguém com `atendente_id == me.id`) → 409 "Conversa não está sob seu atendimento."
- [ ] CA-02: Frontend exibe erro via toast vermelho
- [ ] CA-03: Botão reativado após erro

**Estado atual:** IMPLEMENTADO  
**Arquivos relevantes:** `api/admin.py:376-379`, `static/admin/app.js:682-684`

---

### US-059: SSE notifica outros atendentes ao devolver
**Como** sistema  
**Quero** que todos os atendentes recebam atualização quando uma conversa volta ao bot  
**Para** que a fila da sidebar fique sincronizada em tempo real

**Critérios de Aceite:**
- [ ] CA-01: Backend publica evento `nova_mensagem` com texto de despedida após devolver
- [ ] CA-02: Backend publica evento `bot_devolveu` com `telefone`
- [ ] CA-03: Frontend com evento `bot_devolveu` chama `carregarConversas()` e reabre conversa se for `conversaAtual`

**Estado atual:** IMPLEMENTADO  
**Arquivos relevantes:** `api/admin.py:391-404`, `static/admin/app.js:842-845`

---

## 15. Compositor — 4 Estados

### US-060: Estado "voce" — compositor ativo
**Como** atendente (dono da conversa)  
**Quero** ter o campo de mensagem totalmente funcional  
**Para** enviar mensagens ao cliente

**Critérios de Aceite:**
- [ ] CA-01: Footer sem classe `compositor-inativo`
- [ ] CA-02: Textarea com placeholder "Digite uma mensagem…" e totalmente interativo
- [ ] CA-03: `#compositor-banner` oculto
- [ ] CA-04: Botão de envio com fundo `#2481cc` e shadow ativo
- [ ] CA-05: Foco automático no textarea ao abrir conversa nesse estado

**Estado atual:** IMPLEMENTADO  
**Arquivos relevantes:** `static/admin/index.html:860-866`, `static/admin/app.js:406-410`

---

### US-061: Estado "aguardando" — compositor bloqueado com banner vermelho
**Como** atendente (observando conversa aguardando)  
**Quero** ver por que não posso enviar mensagem e como assumir  
**Para** entender o fluxo e agir corretamente

**Critérios de Aceite:**
- [ ] CA-01: Footer com classe `compositor-inativo` (textarea opaco e `pointer-events:none`)
- [ ] CA-02: Banner vermelho semitransparente com ponto pulsante e texto "Cliente aguardando atendente"
- [ ] CA-03: Link "Assumir agora" no banner dispara `btn-assumir.click()`
- [ ] CA-04: Placeholder: "Assuma a conversa para responder…"

**Estado atual:** IMPLEMENTADO  
**Arquivos relevantes:** `static/admin/index.html:866-876`

---

### US-062: Estado "bot_ativo" — compositor bloqueado com banner verde
**Como** atendente (observando conversa com bot)  
**Quero** ver que o bot está ativo e como interromper  
**Para** tomar controle quando necessário

**Critérios de Aceite:**
- [ ] CA-01: Footer com classe `compositor-inativo`
- [ ] CA-02: Banner verde semitransparente com ícone de bot e texto "O bot está ativo"
- [ ] CA-03: Link "interrompa o bot" no banner dispara `btn-assumir.click()`
- [ ] CA-04: Botão "Interromper bot" visível no header (fundo `bg-emerald-700`)
- [ ] CA-05: `#btn-interromper-bot` clicado → chama `#btn-assumir.click()`

**Estado atual:** IMPLEMENTADO  
**Arquivos relevantes:** `static/admin/index.html:876-887`, `static/admin/index.html:985-993`

---

### US-063: Estado "outro_atendente" — read-only
**Como** atendente (observando conversa de outro)  
**Quero** poder ver o histórico mas não interagir  
**Para** monitorar sem interferir

**Critérios de Aceite:**
- [ ] CA-01: Footer com classe `compositor-inativo`
- [ ] CA-02: Banner azul: "Esta conversa está sendo atendida por outro operador."
- [ ] CA-03: Placeholder: "Conversa com outro operador…"
- [ ] CA-04: Nenhum botão de ação no header
- [ ] CA-05: Submit interceptado em capture phase → `preventDefault()` impede envio mesmo com JS

**Estado atual:** IMPLEMENTADO  
**Arquivos relevantes:** `static/admin/index.html:887-899`, `static/admin/index.html:995-1005`

---

## 16. Painel de Info do Cliente

### US-064: Abrir painel de info do cliente
**Como** atendente  
**Quero** abrir o painel lateral com informações do cliente  
**Para** ver contexto antes de responder

**Critérios de Aceite:**
- [ ] CA-01: Botão `#btn-toggle-info` (ícone pessoa) no header da thread faz toggle do painel
- [ ] CA-02: Clicar na área de avatar+nome (`#thread-customer`) também abre o painel
- [ ] CA-03: Painel tem CSS `transition` suave de abertura/fechamento (width + opacity)
- [ ] CA-04: Em telas < 1024px, painel aparece como drawer sobreposto com backdrop

**Estado atual:** IMPLEMENTADO  
**Arquivos relevantes:** `static/admin/app.js:1101-1133`, `static/admin/index.html:1007-1018`

---

### US-065: Fechar painel de info do cliente
**Como** atendente  
**Quero** fechar o painel lateral de info  
**Para** ter mais espaço na thread

**Critérios de Aceite:**
- [ ] CA-01: Botão `#btn-fechar-info` (X) fecha o painel
- [ ] CA-02: Clicar no backdrop (`#info-panel-backdrop`) fecha o painel em mobile/tablet
- [ ] CA-03: `fecharInfoPanel()` adiciona classe `colapsado` → width 0, opacity 0 em desktop
- [ ] CA-04: Em mobile, `colapsado` = `translateX(100%)`

**Estado atual:** IMPLEMENTADO  
**Arquivos relevantes:** `static/admin/app.js:1111-1116`, `static/admin/index.html:1131-1133`

---

### US-066: Exibir avatar DiceBear do cliente
**Como** atendente  
**Quero** ver a foto ou avatar do cliente no painel de info  
**Para** ter referência visual do interlocutor

**Critérios de Aceite:**
- [ ] CA-01: GET `/admin/cliente/{telefone}/info` retorna `foto_url` (URL DiceBear gerada via `whatsapp.gerar_url_avatar`)
- [ ] CA-02: Frontend tenta carregar a imagem via `new Image()`; em caso de sucesso, aplica como `background-image: cover center`
- [ ] CA-03: Em caso de falha no carregamento da imagem, mantém as iniciais coloridas (fallback silencioso)
- [ ] CA-04: Se `foto_url` é null, exibe iniciais coloridas determinísticas

**Estado atual:** IMPLEMENTADO  
**Arquivos relevantes:** `static/admin/app.js:1050-1072`, `api/admin.py:441-442`

---

### US-067: Exibir estatísticas do cliente
**Como** atendente  
**Quero** ver total de mensagens e atendimentos humanos do cliente  
**Para** entender o histórico de relacionamento

**Critérios de Aceite:**
- [ ] CA-01: `total_mensagens`: `COUNT(*)` em `HistoricoConversa` para o telefone
- [ ] CA-02: `total_atendimentos_humanos`: `COUNT(*)` onde `origem='humano'`
- [ ] CA-03: Ambos exibidos em cards `bg-[#111b21]` com rótulo e valor
- [ ] CA-04: Número formatado com `toLocaleString('pt-BR')` (separador de milhar)
- [ ] CA-05: Data de cadastro e última interação também exibidas

**Estado atual:** IMPLEMENTADO  
**Arquivos relevantes:** `static/admin/app.js:1078-1079`, `api/admin.py:425-441`

---

### US-068: Status atual do cliente no painel de info
**Como** atendente  
**Quero** ver o estado atual do bot e da tag no painel de info  
**Para** ter um resumo rápido sem precisar olhar o header

**Critérios de Aceite:**
- [ ] CA-01: Campo "Bot": "Aguardando atendente" (vermelho) / "Atendendo você" / "Outro operador" (azul) / "Ativo" (verde) / "Inativo" (cinza)
- [ ] CA-02: Campo "Tag": badge visual ou "sem marcação"

**Estado atual:** IMPLEMENTADO  
**Arquivos relevantes:** `static/admin/app.js:1082-1098`

---

### US-069: Fallback imediato enquanto info carrega
**Como** atendente  
**Quero** ver as informações básicas do cliente imediatamente ao abrir o painel  
**Para** não ver tela em branco durante o carregamento

**Critérios de Aceite:**
- [ ] CA-01: `preencherInfoBasica()` chamada imediatamente com `{telefone, nome_cliente: null}` antes do fetch
- [ ] CA-02: Campos mostram iniciais coloridas e "—" como placeholder
- [ ] CA-03: `_infoCarregandoTelefone` previne race: se atendente abre outra conversa durante o fetch, resultado descartado
- [ ] CA-04: Erro no fetch mantém os fallbacks sem exibir toast invasivo

**Estado atual:** IMPLEMENTADO  
**Arquivos relevantes:** `static/admin/app.js:1007-1024`

---

## 17. Notas Internas

### US-070: Listar notas internas de um cliente
**Como** atendente  
**Quero** ver as notas internas registradas sobre um cliente  
**Para** ter contexto de atendimentos anteriores

**Critérios de Aceite:**
- [ ] CA-01: GET `/admin/notas/{telefone}` retorna lista de notas em ordem decrescente de criação
- [ ] CA-02: Cada nota tem: `id`, `texto`, `atendente_id`, `criado_em`
- [ ] CA-03: Frontend exibe em `<ul id="lista-notas">` dentro do painel de info
- [ ] CA-04: Formato do timestamp: `DD/MM/AAAA HH:mm`
- [ ] CA-05: Estado vazio: "Nenhuma nota ainda." em itálico
- [ ] CA-06: Estado de carregamento: "Carregando…" em itálico

**Estado atual:** IMPLEMENTADO  
**Arquivos relevantes:** `static/admin/app.js:919-957`, `api/admin.py:556-573`

---

### US-071: Adicionar nota interna
**Como** atendente  
**Quero** registrar uma nota sobre o cliente  
**Para** compartilhar informações com outros atendentes

**Critérios de Aceite:**
- [ ] CA-01: POST `/admin/notas/{telefone}` com `{texto}` (min 1, max 4096, sem espaços apenas)
- [ ] CA-02: Botão "Adicionar nota" e Enter (sem Shift) submetem a nota
- [ ] CA-03: Campo vazio → foco retorna ao textarea, sem submeter
- [ ] CA-04: Após sucesso, textarea é limpo e lista recarregada
- [ ] CA-05: Toast verde: "Nota adicionada."
- [ ] CA-06: Botão desabilitado durante a requisição

**Estado atual:** IMPLEMENTADO  
**Arquivos relevantes:** `static/admin/app.js:959-979`, `api/admin.py:576-582`

---

### US-072: Campo de nota vazio rejeitado pelo backend
**Como** sistema  
**Quero** validar que notas não contenham apenas espaços  
**Para** evitar registros sem conteúdo útil

**Critérios de Aceite:**
- [ ] CA-01: `field_validator("texto")` em `NotaIn` verifica `v.strip()` — lança `ValueError` se vazio
- [ ] CA-02: Frontend também verifica `ta.value.trim()` antes de submeter
- [ ] CA-03: Erro do servidor exibido via toast vermelho

**Estado atual:** IMPLEMENTADO  
**Arquivos relevantes:** `api/admin.py:74-79`, `static/admin/app.js:964`

---

### US-073: Painel de notas colapsável
**Como** atendente  
**Quero** expandir/recolher a seção de notas no painel de info  
**Para** controlar o espaço visual disponível

**Critérios de Aceite:**
- [ ] CA-01: Botão `#btn-toggle-notas` faz toggle de `#corpo-notas` (hidden/visible)
- [ ] CA-02: Chevron rotaciona 180° quando a seção está aberta (`rotate-180`)
- [ ] CA-03: Estado padrão: aberto

**Estado atual:** IMPLEMENTADO  
**Arquivos relevantes:** `static/admin/app.js:982-988`

---

## 18. Tags de Conversa

### US-074: Aplicar tag "Resolvido"
**Como** atendente  
**Quero** marcar uma conversa como resolvida  
**Para** indicar que o atendimento foi concluído com sucesso

**Critérios de Aceite:**
- [ ] CA-01: Popover de tag abre via `#btn-toggle-tag` (ícone label)
- [ ] CA-02: Clique em "Resolvido" → PATCH `/admin/conversa/{telefone}/tag` com `{tag: "resolvido"}`
- [ ] CA-03: Badge sidebar atualiza imediatamente (sem re-fetch): `tagBadgeHTML('resolvido')` = badge verde com `✓ Resolvido`
- [ ] CA-04: Seletor no header destaca botão "Resolvido" com `bg-[#2f2f2f]`
- [ ] CA-05: Toast verde: "Tag Resolvido."

**Estado atual:** IMPLEMENTADO  
**Arquivos relevantes:** `static/admin/app.js:236-264`, `api/admin.py:459-475`

---

### US-075: Aplicar tag "Follow-up"
**Como** atendente  
**Quero** marcar uma conversa como precisando de acompanhamento  
**Para** lembrar de retornar ao cliente

**Critérios de Aceite:**
- [ ] CA-01: Clique em "Follow-up" → PATCH com `{tag: "follow_up"}`
- [ ] CA-02: Badge sidebar: texto amarelo `↵ Follow-up` com `bg-yellow-900/50`
- [ ] CA-03: Backend valida: `tag in ("resolvido", "follow_up", None)` → 400 se inválido

**Estado atual:** IMPLEMENTADO  
**Arquivos relevantes:** `static/admin/app.js:231-234`, `api/admin.py:468`

---

### US-076: Remover tag
**Como** atendente  
**Quero** remover a tag de uma conversa  
**Para** limpar marcações incorretas ou desnecessárias

**Critérios de Aceite:**
- [ ] CA-01: Botão "Remover marcacao" (`data-tag=""`) → PATCH com `{tag: null}`
- [ ] CA-02: Backend aceita `null` (sem tag)
- [ ] CA-03: Badge sidebar fica vazio, seletor no header sem item destacado
- [ ] CA-04: Toast: "Tag removida."

**Estado atual:** IMPLEMENTADO  
**Arquivos relevantes:** `static/admin/app.js:236-264`, `static/admin/index.html:510-513`

---

### US-077: Fechar popover de tag ao clicar fora
**Como** atendente  
**Quero** que o seletor de tag feche ao clicar fora  
**Para** dispensar o popover sem ação extra

**Critérios de Aceite:**
- [ ] CA-01: Listener no `document` fecha `#tag-selector` se clique fora do popover e fora do botão de toggle
- [ ] CA-02: Popover fecha também após selecionar uma tag (`fecharPopoverTag()`)

**Estado atual:** IMPLEMENTADO  
**Arquivos relevantes:** `static/admin/app.js:906-913`

---

### US-078: Tag row na thread (sub-header)
**Como** atendente  
**Quero** ver a tag atual exibida abaixo do header da thread  
**Para** ter contexto sem abrir o painel de info

**Critérios de Aceite:**
- [ ] CA-01: `#thread-tags-row` visível apenas quando há tag definida
- [ ] CA-02: Conteúdo sincronizado com `#info-tag` via MutationObserver no inline script
- [ ] CA-03: Ao remover tag, row volta a `hidden`

**Estado atual:** IMPLEMENTADO  
**Arquivos relevantes:** `static/admin/index.html:815-828`, `static/admin/index.html:545-548`

---

## 19. SSE — Tempo Real

### US-079: Nova mensagem aparece sem refresh
**Como** atendente (com conversa aberta)  
**Quero** ver as mensagens chegando em tempo real  
**Para** acompanhar o atendimento sem recarregar

**Critérios de Aceite:**
- [ ] CA-01: GET `/admin/eventos/stream` com `Authorization: Bearer` inicia stream SSE (fetch streaming, não EventSource)
- [ ] CA-02: Evento `nova_mensagem` com `telefone === conversaAtual`: `appendMensagemIncremental()` insere bolha
- [ ] CA-03: Posição de scroll mantida se atendente está lendo histórico antigo; auto-scroll apenas se `estaNoFim()` (< 100px do fim)
- [ ] CA-04: Mensagens enviadas pelo próprio atendente não duplicam (verificação `temBolhaPendente()`)

**Estado atual:** IMPLEMENTADO  
**Arquivos relevantes:** `static/admin/app.js:782-869`

---

### US-080: Notificação de novo transbordo via SSE
**Como** atendente  
**Quero** ser notificado imediatamente quando um cliente solicita atendimento humano  
**Para** agir rapidamente

**Critérios de Aceite:**
- [ ] CA-01: Evento `novo_transbordo` → toast vermelho ("cliente aguardando atendimento") + som de notificação
- [ ] CA-02: `carregarConversas()` chamado para atualizar a sidebar
- [ ] CA-03: Som: dois tons (880Hz e 1175Hz) via Web Audio API

**Estado atual:** IMPLEMENTADO  
**Arquivos relevantes:** `static/admin/app.js:824-832`

---

### US-081: Atualização de estado da conversa via SSE
**Como** atendente  
**Quero** ver a sidebar atualizar quando outro atendente assume ou devolve uma conversa  
**Para** manter visão consistente da fila

**Critérios de Aceite:**
- [ ] CA-01: Evento `atendente_assumiu` → `carregarConversas()` + se é `conversaAtual`, `abrirConversa()` para atualizar header
- [ ] CA-02: Evento `bot_devolveu` → mesmo comportamento
- [ ] CA-03: Métricas dos cards também atualizam

**Estado atual:** IMPLEMENTADO  
**Arquivos relevantes:** `static/admin/app.js:842-845`

---

### US-082: Reconexão automática do SSE
**Como** sistema  
**Quero** que a conexão SSE reconecte automaticamente após queda  
**Para** manter o atendente sincronizado sem precisar recarregar

**Critérios de Aceite:**
- [ ] CA-01: `conectarSSE()` usa `fetch` com streaming; ao fechar o stream (done=true ou erro), aguarda 3s e reconecta
- [ ] CA-02: Status de conexão (`#status-conexao`) mostra ponto verde "conectado" ou cinza pulsante "reconectando…"
- [ ] CA-03: Heartbeat do servidor a cada 25s para manter conexão ativa (evita timeout de proxies)

**Estado atual:** IMPLEMENTADO  
**Arquivos relevantes:** `static/admin/app.js:782-813`

---

### US-083: Indicador de status de conexão
**Como** atendente  
**Quero** saber se estou conectado ao servidor de eventos  
**Para** ter confiança na atualização em tempo real

**Critérios de Aceite:**
- [ ] CA-01: `setStatusConexao(true)`: ponto verde + texto "conectado"
- [ ] CA-02: `setStatusConexao(false)`: ponto cinza pulsante + "reconectando…"
- [ ] CA-03: Indicador visível no footer da sidebar

**Estado atual:** IMPLEMENTADO  
**Arquivos relevantes:** `static/admin/app.js:815-822`, `static/admin/index.html:451-458`

---

## 20. Notificações e Som

### US-084: Toast de notificação
**Como** atendente  
**Quero** ver toasts informativos sobre eventos do sistema  
**Para** ser informado sem interromper meu fluxo de trabalho

**Critérios de Aceite:**
- [ ] CA-01: Tipos: `info` (azul `#2481cc`), `transbordo` (vermelho `bg-red-700`), `ok` (verde `bg-emerald-700`)
- [ ] CA-02: Animação `slideIn` ao aparecer
- [ ] CA-03: Desaparece após 4.5 segundos com fade-out (opacity 0 + translateX)
- [ ] CA-04: Múltiplos toasts podem coexistir (coluna vertical, `gap-2`)
- [ ] CA-05: Container `#toast-container` na posição `fixed bottom-4 right-4 z-50`

**Estado atual:** IMPLEMENTADO  
**Arquivos relevantes:** `static/admin/app.js:180-196`

---

### US-085: Som de notificação (dois tons)
**Como** atendente  
**Quero** ouvir um som quando chegam novas mensagens ou transbordos  
**Para** ser alertado mesmo sem olhar para a tela

**Critérios de Aceite:**
- [ ] CA-01: Web Audio API: dois oscillators (880Hz e 1175Hz), tipo `sine`, amplitude 0.18
- [ ] CA-02: Som tocado em: `novo_transbordo` e `nova_mensagem` de cliente em conversa não aberta
- [ ] CA-03: Erro no AudioContext é capturado silenciosamente (try/catch)

**Estado atual:** IMPLEMENTADO  
**Arquivos relevantes:** `static/admin/app.js:198-220`

---

### US-086: Mute/unmute de notificações
**Como** atendente  
**Quero** silenciar as notificações sonoras  
**Para** trabalhar em ambiente que exige silêncio

**Critérios de Aceite:**
- [ ] CA-01: Botão `#btn-mute` alterna `muted` boolean e salva em `localStorage('atendente_mute')`
- [ ] CA-02: Ícone muda: som ativo (ícone speaker) vs. silenciado (ícone speaker com X + `text-red-500`)
- [ ] CA-03: `title` do botão atualiza de acordo com o estado
- [ ] CA-04: Estado persiste entre sessões (localStorage)

**Estado atual:** IMPLEMENTADO  
**Arquivos relevantes:** `static/admin/app.js:579-597`

---

## 21. Gestão de Atendentes

### US-087: Listar atendentes
**Como** supervisor  
**Quero** ver todos os atendentes cadastrados com nome, login, status e último login  
**Para** gerenciar a equipe

**Critérios de Aceite:**
- [ ] CA-01: GET `/admin/atendentes` retorna lista ordenada por nome
- [ ] CA-02: Colunas: Nome, Login (monospace, font-mono), Status (badge), Último login (relativo), Ação
- [ ] CA-03: Badge "Ativo": verde com `✓ Ativo`; Badge "Inativo": cinza
- [ ] CA-04: Minha conta identificada com badge "Voce" azul ao lado do nome
- [ ] CA-05: Estado de carregamento: spinner animado

**Estado atual:** IMPLEMENTADO  
**Arquivos relevantes:** `static/admin/atendentes.html:238-315`, `api/admin.py:497-511`

---

### US-088: Criar novo atendente
**Como** supervisor  
**Quero** cadastrar um novo atendente  
**Para** dar acesso ao painel para novos membros da equipe

**Critérios de Aceite:**
- [ ] CA-01: Modal abre ao clicar em "Novo Atendente"
- [ ] CA-02: Campos: Nome completo, Login, Senha, Confirmar senha
- [ ] CA-03: Validação cliente: nome não vazio, login não vazio, senha ≥ 8 chars, senhas conferem
- [ ] CA-04: Validação servidor: `login` padrão `^[a-z0-9_]+$`, min 3 chars
- [ ] CA-05: POST `/admin/atendentes` → 201 em sucesso
- [ ] CA-06: Modal fecha e lista recarrega após sucesso
- [ ] CA-07: Toast verde: "Atendente '{nome}' criado com sucesso."

**Estado atual:** IMPLEMENTADO  
**Arquivos relevantes:** `static/admin/atendentes.html:391-446`, `api/admin.py:514-523`

---

### US-089: Login duplicado retorna 409
**Como** sistema  
**Quero** impedir criação de dois atendentes com o mesmo login  
**Para** garantir unicidade de acesso

**Critérios de Aceite:**
- [ ] CA-01: Backend verifica existência do `usuario_login` → 409 "Login já existe"
- [ ] CA-02: Frontend exibe o erro no `#erro-modal` dentro do modal
- [ ] CA-03: Modal permanece aberto para correção

**Estado atual:** IMPLEMENTADO  
**Arquivos relevantes:** `api/admin.py:517-518`, `static/admin/atendentes.html:433-438`

---

### US-090: Desativar atendente
**Como** supervisor  
**Quero** desativar a conta de um atendente que saiu da equipe  
**Para** revogar seu acesso ao painel

**Critérios de Aceite:**
- [ ] CA-01: Botão "Desativar" visível apenas para atendentes ativos e que não são a própria conta
- [ ] CA-02: `confirm()` antes de desativar
- [ ] CA-03: PATCH `/admin/atendentes/{id}/desativar` → `ativo=False`
- [ ] CA-04: Conversas abertas do atendente desativado são liberadas: `atendente_id=None`, `bot_ativo=True`
- [ ] CA-05: Lista recarrega após sucesso

**Estado atual:** IMPLEMENTADO  
**Arquivos relevantes:** `static/admin/atendentes.html:340-353`, `api/admin.py:526-548`

---

### US-091: Não pode desativar a própria conta
**Como** sistema  
**Quero** impedir que um atendente desative sua própria conta  
**Para** evitar auto-lockout acidental

**Critérios de Aceite:**
- [ ] CA-01: Frontend: botão "Desativar" não renderizado para `ehEuMesmo=true`; texto "Sua conta" exibido no lugar
- [ ] CA-02: Backend: verificação `atual.id == atendente_id` → 400 "Não é possível desativar sua própria conta"
- [ ] CA-03: Defesa dupla (frontend + backend)

**Estado atual:** IMPLEMENTADO  
**Arquivos relevantes:** `static/admin/atendentes.html:267-279`, `api/admin.py:529-530`

---

### US-092: Fechar modal com Escape e click fora
**Como** supervisor  
**Quero** fechar o modal de criação sem usar o botão X  
**Para** ter atalho rápido de descarte

**Critérios de Aceite:**
- [ ] CA-01: Tecla `Escape` fecha o modal
- [ ] CA-02: Clique no overlay (fora do modal) fecha o modal
- [ ] CA-03: Formulário é resetado ao abrir (não mantém dados anteriores)

**Estado atual:** IMPLEMENTADO  
**Arquivos relevantes:** `static/admin/atendentes.html:382-385`, `static/admin/atendentes.html:376-380`

---

## 22. Responsividade Mobile

### US-093: Sidebar como drawer em mobile
**Como** atendente (mobile)  
**Quero** que a sidebar apareça como menu deslizante  
**Para** ter espaço suficiente na tela do celular

**Critérios de Aceite:**
- [ ] CA-01: Sidebar com `position: fixed`, `z-index: 40` e classe `-translate-x-full` por padrão em mobile
- [ ] CA-02: Em sm+ (≥ 640px): sidebar é estática (`sm:translate-x-0 sm:static`)
- [ ] CA-03: Backdrop `#sidebar-backdrop` visível apenas em mobile (`sm:hidden`)
- [ ] CA-04: Botão `#btn-hamburger` visível apenas em mobile (`sm:hidden`), no header da thread

**Estado atual:** IMPLEMENTADO  
**Arquivos relevantes:** `static/admin/index.html:382`, `static/admin/index.html:379`, `static/admin/index.html:474-482`

---

### US-094: Fechar sidebar ao abrir conversa (mobile)
**Como** atendente (mobile)  
**Quero** que a sidebar feche automaticamente ao clicar em uma conversa  
**Para** ver a thread em tela cheia

**Critérios de Aceite:**
- [ ] CA-01: `abrirConversa()` verifica `window.innerWidth < 640` → chama `fecharSidebar()`
- [ ] CA-02: Sidebar desliza de volta para esquerda
- [ ] CA-03: Backdrop some

**Estado atual:** IMPLEMENTADO  
**Arquivos relevantes:** `static/admin/app.js:371`

---

### US-095: Painel de info como drawer em tablet/mobile
**Como** atendente (tablet/mobile)  
**Quero** que o painel de info do cliente apareça como overlay ao invés de coluna fixa  
**Para** não ocupar espaço da thread permanentemente

**Critérios de Aceite:**
- [ ] CA-01: Em telas < 1024px: `#info-panel` vira `position: fixed`, `z-index: 35`, coberto por backdrop
- [ ] CA-02: Classe `colapsado` aplica `translateX(100%)` em vez de `width: 0`
- [ ] CA-03: `#info-panel-backdrop` só visível em `lg:hidden`
- [ ] CA-04: Fechar backdrop fecha o painel

**Estado atual:** IMPLEMENTADO  
**Arquivos relevantes:** `static/admin/index.html:159-176`, `static/admin/index.html:760`

---

## 23. Erros de Rede e Resiliência

### US-096: Falha de fetch genérica
**Como** atendente  
**Quero** ser informado quando uma ação falha por erro de rede  
**Para** saber que devo tentar novamente

**Critérios de Aceite:**
- [ ] CA-01: `api()` lança `Error(\`${res.status}: ${txt}\`)` para respostas não-ok
- [ ] CA-02: Catch blocks exibem toast vermelho com o erro
- [ ] CA-03: `carregarConversas()` e `carregarInfoCliente()` logam no console sem exibir toast invasivo
- [ ] CA-04: Botões desabilitados durante request são reabilitados no `finally`

**Estado atual:** IMPLEMENTADO  
**Arquivos relevantes:** `static/admin/app.js:60-75`

---

### US-097: Bolha de falha com retry
**Como** atendente  
**Quero** poder tentar reenviar uma mensagem que falhou por erro de rede  
**Para** não precisar redigitar o texto

**Critérios de Aceite:**
- [ ] CA-01: Em falha de rede (catch): bolha fica vermelha (`bolha-falha`)
- [ ] CA-02: Indicador no rodapé da bolha: "⚠ falha ao enviar — clique para tentar de novo" (texto clicável)
- [ ] CA-03: Clique no indicador: remove a bolha, restaura texto no textarea, foca textarea
- [ ] CA-04: Atendente pode então editar e reenviar manualmente

**Estado atual:** IMPLEMENTADO  
**Arquivos relevantes:** `static/admin/app.js:754-770`

---

### US-098: Bolha de falha por rejeição da Meta API
**Como** atendente  
**Quero** ser avisado quando a mensagem chegou ao servidor mas foi rejeitada pelo WhatsApp  
**Para** entender que o problema é externo

**Critérios de Aceite:**
- [ ] CA-01: `resp.entregue === false` (sucesso HTTP mas Meta rejeitou): bolha fica vermelha com `⚠ não entregue`
- [ ] CA-02: Toast: "⚠ Meta API rejeitou — mensagem não chegou ao cliente." (tipo `transbordo`)
- [ ] CA-03: Diferente do erro de rede: não há opção de retry automático

**Estado atual:** IMPLEMENTADO  
**Arquivos relevantes:** `static/admin/app.js:742-750`

---

### US-099: Fallback de conexão SSE com 3s de espera
**Como** sistema  
**Quero** que a reconexão SSE não ocorra imediatamente  
**Para** não sobrecarregar o servidor em caso de falha massiva

**Critérios de Aceite:**
- [ ] CA-01: `setTimeout(conectarSSE, 3000)` após qualquer desconexão
- [ ] CA-02: Status de conexão atualiza imediatamente para "reconectando…"
- [ ] CA-03: Não há limite de reconexões (retry infinito)

**Estado atual:** IMPLEMENTADO  
**Arquivos relevantes:** `static/admin/app.js:787`, `static/admin/app.js:811`

---

### US-100: Refresh periódico da sidebar como fallback do SSE
**Como** sistema  
**Quero** que a sidebar atualize periodicamente mesmo se o SSE perder eventos  
**Para** garantir consistência eventualmente

**Critérios de Aceite:**
- [ ] CA-01: `setInterval(carregarConversas, 30000)` — refresh completo a cada 30s
- [ ] CA-02: `setInterval(renderListaConversas, 60000)` — re-render local dos labels de tempo relativos a cada 60s (sem chamada API)
- [ ] CA-03: Esses intervalos são complementares ao SSE, não substitutos

**Estado atual:** IMPLEMENTADO  
**Arquivos relevantes:** `static/admin/app.js:1141-1150`

---

## Gaps Identificados

### Funcionalidades faltando no backend

**GAP-01: Endpoint de reativar atendente**  
O backend tem `PATCH /admin/atendentes/{id}/desativar` mas não tem `PATCH /admin/atendentes/{id}/ativar`. Atendentes desativados nunca podem ser reativados via interface — só via SQL direto no banco.

**GAP-02: Filtros reais de estado no endpoint `/admin/conversas`**  
O endpoint não aceita query params de filtro (`?estado=aguardando`). Os chips da sidebar tentam filtrar via string no input de busca, o que não funciona para estados booleanos como "aguardando", "meus" ou "bot". O filtro real só funciona para nome e telefone.

**GAP-03: Paginação no endpoint `/admin/conversas`**  
Limite hardcoded de 200 conversas sem cursor ou página. Barbearias com muitos clientes terão conversas antigas invisíveis na sidebar.

**GAP-04: Paginação no histórico de notas**  
`GET /admin/notas/{telefone}` retorna todas as notas sem limite. Clientes com muitas notas podem causar payloads grandes.

**GAP-05: Nenhum endpoint de edição ou exclusão de notas**  
Notas internas só podem ser criadas. Não há `DELETE /admin/notas/{id}` nem `PATCH /admin/notas/{id}`.

**GAP-06: Sem endpoint para reativar bot manualmente (sem devolver)**  
O endpoint `devolver` sempre envia mensagem de despedida ao cliente. Não há forma de reativar o bot silenciosamente (sem notificar o cliente) — útil para correções internas.

**GAP-07: `GET /admin/conversa/{telefone}` sem filtro por data**  
Retorna sempre as últimas 500 mensagens. Históricos muito longos podem ser lentos sem paginação.

**GAP-08: Eventos SSE não incluem todos os estados**  
O evento `atendente_assumiu` não inclui o nome do atendente para exibição inline no separador de handoff. Sem esse dado, o separador "Diego assumiu" não pode ser renderizado corretamente.

---

### Problemas visuais identificados

**VIS-01: Chips de filtro não funcionam corretamente (US-011 PARCIAL)**  
`data-filter="aguardando"` insere a string "aguardando" no input de busca, que então filtra por nome/telefone contendo "aguardando". Nenhum cliente tem "aguardando" no nome, então o resultado é sempre vazio. A função `renderListaConversas()` precisa de um segundo critério de filtro por estado.

**VIS-02: Painel de info não abre automaticamente em desktop**  
O inline script em `index.html` intercepta `abrirInfoPanel()` com `_blockInfoPanelAutoOpen=true` e mantém o painel recolhido mesmo em desktop. A experiência esperada (painel abre automaticamente em ≥1024px) não ocorre.

**VIS-03: Separadores de evento inline de handoff não são renderizados**  
CSS e HTML de preview estão prontos, mas `renderThread()` não insere `event-separator` no histórico. O backend também não retorna metadados de handoff como eventos distintos na lista de mensagens.

**VIS-04: Botão "Emoji" permanentemente desabilitado**  
Existe no compositor mas com `disabled` e `cursor-not-allowed`. Não há plano de implementação visível.

**VIS-05: Botão "Favoritar cliente" sem funcionalidade**  
`#btn-favoritar-cliente` no painel de info existe mas não tem listener de evento, endpoint de backend ou coluna no banco para persistir favoritos.

**VIS-06: Seção "Serviços frequentes" sem dados**  
`#servicos-frequentes` e `#servicos-chips` existem no HTML mas a lógica `syncServicosFrequentes()` usa o conteúdo de `#info-tag` (a tag da conversa) ao invés de dados reais de serviços. Resultado incorreto.

**VIS-07: Avatar do atendente no header da sidebar exibe "?"**  
O HTML inicial do `#avatar-atendente` tem o texto "?" como placeholder. O script inline chama `updateOperatorAvatar()` no DOMContentLoaded para injetar as iniciais do `atendente_nome` do localStorage, mas há uma janela onde o placeholder "?" é visível.

---

### Edge cases sem tratamento

**EDGE-01: Mensagem enviada enquanto a conversa é devolvida ao bot**  
Se o atendente envia uma mensagem exatamente quando outro atendente devolve a conversa, o frontend pode estar em estado `voce` (compositor ativo) mas o backend retornará 403. O retry manual via bolha-falha resolve, mas o UX é confuso.

**EDGE-02: Sem indicação de nome do atendente que assumiu na sidebar**  
A lista de conversas mostra o ponto cinza para "outro operador" mas não exibe o nome. Para identificar quem está atendendo, é necessário abrir a conversa.

**EDGE-03: Timeout do JWT não avisado ao usuário**  
Quando o JWT expira, a próxima ação HTTP disparará redirect automático para login. O atendente perde qualquer texto que estava digitando no textarea sem aviso prévio.

**EDGE-04: Atendente desconectado do SSE não recebe `novo_transbordo`**  
Durante os 3 segundos de reconexão, eventos `novo_transbordo` são perdidos. O refresh de 30s recupera o estado, mas o som e o toast não são disparados retroativamente.

**EDGE-05: Preview da sidebar não atualiza após envio do atendente**  
`carregarConversas()` é chamado após envio, mas pode haver latência. A sidebar pode mostrar preview desatualizado por alguns segundos.

**EDGE-06: Conversas sem nenhuma mensagem ainda aparecem na lista**  
`GET /admin/conversas` inclui usuários que nunca enviaram mensagem (preview vazio). Esses aparecem na lista com preview em branco, o que pode confundir.

**EDGE-07: Não há validação de comprimento máximo no textarea de nota (client-side)**  
O textarea de nota não tem `maxlength` definido. O backend valida `max=4096`, mas o usuário só descobre o erro após tentar salvar.

**EDGE-08: JWT_SECRET ausente retorna 503 no login, mas o erro não é user-friendly**  
Frontend exibe a mensagem técnica "Servidor não configurado: JWT_SECRET ausente." ao invés de uma mensagem mais amigável para o usuário final.

---

*Documento gerado em 2026-05-17. Baseado na análise dos arquivos:*  
- `static/admin/app.js` (1151 linhas)  
- `static/admin/index.html` (1047 linhas)  
- `static/admin/login.html` (75 linhas)  
- `static/admin/atendentes.html` (455 linhas)  
- `api/admin.py` (583 linhas)
