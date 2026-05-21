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
24. [Histórico de Conversa — Navegação Avançada](#24-histórico-de-conversa--navegação-avançada) (US-101 a US-108)
25. [Status e Ciclo de Vida do Atendente](#25-status-e-ciclo-de-vida-do-atendente) (US-109 a US-114)
26. [Gestão de Sessão JWT](#26-gestão-de-sessão-jwt) (US-115 a US-119)
27. [Cenários Multi-Atendente](#27-cenários-multi-atendente) (US-120 a US-126)
28. [Notificações Avançadas](#28-notificações-avançadas) (US-127 a US-131)
29. [Respostas Rápidas Avançadas](#29-respostas-rápidas-avançadas) (US-132 a US-136)
30. [Mensagens com Falha — Recuperação](#30-mensagens-com-falha--recuperação) (US-137 a US-141)
31. [Edge Cases Formalizados](#31-edge-cases-formalizados) (US-142 a US-149)

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

---

## Expansão v1.1 — User Stories Adicionais (US-101 a US-149)

**Data da expansão:** 2026-05-19  
**Escopo:** 49 novas stories cobrindo histórico avançado, ciclo de vida do atendente, gestão de JWT, cenários multi-atendente, notificações avançadas, respostas rápidas customizáveis, recuperação de falhas e formalização dos 8 edge cases já documentados.

---

## 24. Histórico de Conversa — Navegação Avançada

### US-101 — Scroll até topo carrega mensagens mais antigas (infinite scroll)
**Como** atendente, **quero** rolar até o topo da thread e ver mensagens anteriores carregadas automaticamente, **para** consultar o histórico completo de clientes antigos sem precisar abrir outra view.

**Critérios de aceite:**
- [ ] CA-01: Detecção de scroll no topo via `IntersectionObserver` num sentinel no início da thread ou via `scrollTop < 80` no `#thread-mensagens`
- [ ] CA-02: GET `/admin/conversa/{telefone}?antes_de={id_mensagem_mais_antiga}&limite=100` retorna lote anterior
- [ ] CA-03: Mensagens são prepended (no topo) sem alterar a posição visual de leitura (offset preservado via `scrollHeight` antes/depois)
- [ ] CA-04: Loading espacial é injetado no topo durante o fetch (spinner pequeno)
- [ ] CA-05: Se retorno < 100 mensagens, marca a thread como "não há mais histórico" (ver US-103) e desabilita novos disparos

**Status:** NOVO

---

### US-102 — Indicador visual de carregamento ao buscar histórico
**Como** atendente, **quero** ver um spinner durante o fetch de mensagens antigas, **para** entender que o sistema está respondendo e não travou.

**Critérios de aceite:**
- [ ] CA-01: Elemento `#thread-loading-top` injetado no topo da `#thread-mensagens` durante request
- [ ] CA-02: Spinner CSS (não imagem) usando `animation: spin 1s linear infinite`
- [ ] CA-03: Spinner removido em `finally` (sucesso ou erro), garantindo que nunca permaneça preso
- [ ] CA-04: Em erro de rede, spinner é substituído por mensagem "Erro ao carregar — clique para tentar de novo" com retry

**Status:** NOVO

---

### US-103 — Mensagem de "início da conversa" quando não há mais histórico
**Como** atendente, **quero** ver uma indicação clara quando cheguei à primeira mensagem do cliente, **para** entender que não há mais conteúdo anterior.

**Critérios de aceite:**
- [ ] CA-01: Quando o último fetch retorna < limite (ex.: 100), exibe pill centralizado no topo com texto "Início da conversa"
- [ ] CA-02: Pill segue o mesmo estilo dos separadores de data (`bg-[#2b2b2b] border border-[#3a3a3a] px-3 py-0.5 rounded-full`)
- [ ] CA-03: Após exibido, o listener de scroll-no-topo é desligado para evitar requests inúteis
- [ ] CA-04: Estado é resetado ao abrir outra conversa

**Status:** NOVO

---

### US-104 — Timestamp completo ao passar mouse sobre mensagem (tooltip)
**Como** atendente, **quero** ver a data e hora completas de uma mensagem ao passar o mouse, **para** confirmar a cronologia exata sem depender do separador de dia.

**Critérios de aceite:**
- [ ] CA-01: Cada bolha tem atributo `title="DD/MM/AAAA HH:mm:ss"` gerado a partir do `data_envio` ISO
- [ ] CA-02: Tooltip nativo do browser exibe o título após hover (delay ~700ms padrão)
- [ ] CA-03: Em mobile (sem hover), atributo permanece como fallback acessível para screen readers
- [ ] CA-04: Formato em pt-BR com `toLocaleString('pt-BR', { dateStyle: 'short', timeStyle: 'medium' })`

**Status:** NOVO

---

### US-105 — Botão "novas mensagens" para scroll rápido até o fim
**Como** atendente, **quero** clicar em um botão flutuante para voltar ao fim da thread quando há mensagens novas, **para** retornar rapidamente ao contexto atual após ler histórico.

**Critérios de aceite:**
- [ ] CA-01: Botão flutuante `#btn-scroll-fim` (ícone ↓) aparece quando `scrollTop` está a mais de 200px do final
- [ ] CA-02: Posicionado no canto inferior-direito da thread, acima do compositor (`position: absolute; bottom: 88px; right: 16px`)
- [ ] CA-03: Badge numérico exibe quantas mensagens novas chegaram desde a última posição (ex.: "↓ 3 novas")
- [ ] CA-04: Clique no botão chama `scrollarFim()` com `behavior: 'smooth'` e zera o contador
- [ ] CA-05: Botão some quando `estaNoFim()` (< 100px do fim) é true

**Status:** NOVO

---

### US-106 — Busca de texto dentro da conversa ativa
**Como** atendente, **quero** pesquisar uma palavra ou frase no histórico da conversa aberta, **para** localizar rapidamente um ponto específico do atendimento.

**Critérios de aceite:**
- [ ] CA-01: Atalho `Ctrl+F` (ou `Cmd+F` no Mac) abre input de busca no topo da thread (não usa o do browser)
- [ ] CA-02: Digitar destaca via `<mark>` todas as ocorrências case-insensitive em mensagens visíveis
- [ ] CA-03: Botões "Próximo" e "Anterior" navegam entre matches, fazendo `scrollIntoView({block:'center'})`
- [ ] CA-04: Contador exibido: "3 de 12 resultados"
- [ ] CA-05: Tecla `Esc` fecha a busca e remove os destaques
- [ ] CA-06: Busca aplica-se apenas a mensagens já carregadas (não força fetch de histórico antigo)

**Status:** NOVO

---

### US-107 — Contador de mensagens não lidas ao voltar ao topo
**Como** atendente, **quero** ver um contador de mensagens recebidas enquanto estava lendo histórico antigo, **para** saber quantas novidades chegaram durante minha consulta.

**Critérios de aceite:**
- [ ] CA-01: Contador acoplado ao botão `#btn-scroll-fim` (US-105): "↓ N novas"
- [ ] CA-02: Incrementa a cada `nova_mensagem` SSE com `telefone === conversaAtual` enquanto `estaNoFim() === false`
- [ ] CA-03: Reseta para 0 ao clicar no botão ou rolar manualmente até o fim
- [ ] CA-04: Limite visual: "9+" quando contagem ≥ 10

**Status:** NOVO

---

### US-108 — Performance: conversa com 500+ mensagens não trava a UI
**Como** atendente, **quero** que threads muito longas continuem fluidas ao rolar e abrir, **para** atender clientes recorrentes sem lag perceptível.

**Critérios de aceite:**
- [ ] CA-01: Renderização inicial usa `DocumentFragment` (já feito em `renderThread`) — manter ao expandir
- [ ] CA-02: Considerar virtualização (windowing) quando `mensagens.length > 500`: renderizar apenas ±50 itens em torno do viewport
- [ ] CA-03: `scroll` event listener com `requestAnimationFrame` throttle (não chamar handler em cada pixel)
- [ ] CA-04: Lighthouse: tempo de renderização inicial < 500ms para conversa de 1000 msgs
- [ ] CA-05: Sem reflow durante scroll (medições com DevTools Performance < 16ms por frame)

**Status:** NOVO

---

## 25. Status e Ciclo de Vida do Atendente

### US-109 — Sinalizar status "ocupado" (não recebe novas conversas)
**Como** atendente, **quero** marcar meu status como "ocupado" durante pausas ou atendimentos complexos, **para** não receber novos transbordos enquanto estou indisponível.

**Critérios de aceite:**
- [ ] CA-01: Botão de toggle no header da sidebar com 3 estados: "Disponível" (verde) / "Ocupado" (amarelo) / "Pausa" (cinza)
- [ ] CA-02: PATCH `/admin/atendentes/me/status` com `{status: "ocupado"}`
- [ ] CA-03: Backend persiste `Atendente.status` (nova coluna) e considera no roteamento (clientes em transbordo não notificam atendentes ocupados via SSE)
- [ ] CA-04: Conversas já assumidas continuam sob o atendente independente do status
- [ ] CA-05: Mudança de status publica evento SSE `atendente_status_mudou` para os demais

**Status:** NOVO

---

### US-110 — Atendente fica offline (fecha aba) — conversas em estado especial
**Como** sistema, **quero** detectar quando um atendente fecha o painel e marcar suas conversas em atendimento como "operador offline", **para** que supervisores possam reagir.

**Critérios de aceite:**
- [ ] CA-01: `beforeunload` envia `navigator.sendBeacon('/admin/atendentes/me/offline')` ao fechar a aba
- [ ] CA-02: Backend marca `Atendente.online=False` e timestamp `ultimo_visto`
- [ ] CA-03: Heartbeat: enquanto SSE conectado, backend atualiza `ultimo_visto` automaticamente; sem heartbeat por 60s → considerado offline
- [ ] CA-04: Conversas com `atendente_id` de operador offline recebem flag `operador_offline=True` no payload de `/admin/conversas`
- [ ] CA-05: Sidebar exibe ícone de relógio amarelo nesses itens com tooltip "Operador desconectado há Xmin"

**Status:** NOVO

---

### US-111 — Quando atendente volta online, vê conversas que ficaram abertas
**Como** atendente, **quero** ao logar novamente ver claramente quais conversas estavam sob meu nome quando fechei o painel, **para** retomar o trabalho sem perder contexto.

**Critérios de aceite:**
- [ ] CA-01: No login (ou no bootstrap do dashboard), `/admin/conversas?filtro=meus` retorna conversas com `atendente_id == me.id`
- [ ] CA-02: Toast informativo no bootstrap: "Você tem N conversas em atendimento aguardando retorno."
- [ ] CA-03: Chip "Meus" recebe contador `(N)` em destaque visual
- [ ] CA-04: Clique no chip filtra apenas essas conversas (resolve dependência com US-011 e GAP-02)

**Status:** NOVO

---

### US-112 — Timeout de inatividade exibe aviso
**Como** sistema, **quero** detectar quando o atendente está inativo por mais de X minutos, **para** alertar antes de transferir conversas a outros operadores.

**Critérios de aceite:**
- [ ] CA-01: Monitor de inatividade via `mousemove`, `keydown`, `click` no document (throttle 5s)
- [ ] CA-02: Após 5 minutos sem interação, exibe modal "Você ainda está aí?" com botão "Sim, continuar" e contador regressivo de 60s
- [ ] CA-03: Se contador expirar sem resposta, status muda para "Pausa" automaticamente (US-109)
- [ ] CA-04: Mover o mouse ou clicar fecha o modal e reinicia o timer
- [ ] CA-05: Timer pausado quando o documento está com `visibilityState === 'hidden'` (não conta tempo de aba em background)

**Status:** NOVO

---

### US-113 — Múltiplas abas do mesmo atendente (somente uma ativa)
**Como** sistema, **quero** detectar quando o mesmo atendente abriu o painel em duas abas e desativar a primeira, **para** evitar conflitos de envio e duplicação de SSE.

**Critérios de aceite:**
- [ ] CA-01: Cada aba gera um `tab_id` (UUID v4) salvo em `sessionStorage`
- [ ] CA-02: Broadcast via `BroadcastChannel('barbearia-admin')` quando uma nova aba abre — todas as outras recebem mensagem `claim`
- [ ] CA-03: A aba mais recente vence; as antigas exibem overlay "Painel ativo em outra aba — clique para reassumir aqui"
- [ ] CA-04: Aba inativa fecha o SSE para reduzir carga
- [ ] CA-05: Clicar em "reassumir aqui" repete o ciclo (envia novo `claim`) e reativa SSE

**Status:** NOVO

---

### US-114 — Indicador de presença: ver quem está online
**Como** atendente, **quero** ver quais outros atendentes estão online no momento, **para** coordenar atendimentos e pedir ajuda quando necessário.

**Critérios de aceite:**
- [ ] CA-01: GET `/admin/atendentes/online` retorna lista `[{id, nome, status, ultimo_visto}]` filtrada por `online=True`
- [ ] CA-02: Painel colapsável no footer da sidebar com avatares pequenos dos online (até 5 visíveis + "+N" se mais)
- [ ] CA-03: Tooltip em cada avatar mostra nome + status (Disponível/Ocupado/Pausa)
- [ ] CA-04: Atualização via SSE `atendente_status_mudou` (US-109) e `atendente_online`/`atendente_offline`
- [ ] CA-05: Em mobile, painel acessível via clique no avatar próprio

**Status:** NOVO

---

## 26. Gestão de Sessão JWT

### US-115 — Aviso 2 minutos antes da expiração do JWT
**Como** atendente, **quero** receber um aviso antes do meu token expirar, **para** poder renovar a sessão sem perder trabalho em andamento.

**Critérios de aceite:**
- [ ] CA-01: Frontend decodifica `exp` do JWT (payload base64) ao logar e agenda `setTimeout` para `exp - 120s`
- [ ] CA-02: Banner amarelo fixo no topo da tela: "Sua sessão expira em 2 minutos. [Renovar agora]"
- [ ] CA-03: Botão "Renovar agora" dispara `POST /admin/refresh-token` (usa o token atual ainda válido)
- [ ] CA-04: Backend valida JWT existente e emite novo com `exp` estendido por `JWT_TTL_MIN`
- [ ] CA-05: Token novo substitui o antigo em `localStorage`, banner some, novo timer agendado

**Status:** NOVO

---

### US-116 — Salvar draft ao expirar token com texto digitado
**Como** atendente, **quero** que o texto que estou digitando seja salvo quando o token expirar, **para** não perder o conteúdo após re-login.

**Critérios de aceite:**
- [ ] CA-01: Antes do `localStorage.clear()` em qualquer 401, salvar `{telefone, texto, timestamp}` em `localStorage('draft_compositor')`
- [ ] CA-02: Salvar somente se `texto.trim().length > 0`
- [ ] CA-03: Draft inclui também o `conversaAtual` para reabrir contexto correto
- [ ] CA-04: Draft expira após 24h (descartado se `timestamp` antigo)
- [ ] CA-05: Limpar `localStorage` mas preservar a chave `draft_compositor`

**Status:** NOVO

---

### US-117 — Recuperar draft após re-login
**Como** atendente, **quero** ver o texto que estava digitando restaurado após relogar, **para** continuar exatamente de onde parei.

**Critérios de aceite:**
- [ ] CA-01: Após login bem-sucedido, verifica `localStorage('draft_compositor')`
- [ ] CA-02: Se existe e não expirou: abre automaticamente `conversaAtual` salvo (US-025) e preenche textarea com o texto
- [ ] CA-03: Toast informativo: "Texto recuperado da sessão anterior"
- [ ] CA-04: Após restaurar, remove a chave do localStorage
- [ ] CA-05: Se a conversa não existe mais (cliente removido), exibe o texto num modal "Não foi possível reabrir a conversa. Texto recuperado:" com botão copiar

**Status:** NOVO

---

### US-118 — Refresh token automático silencioso
**Como** sistema, **quero** renovar o JWT silenciosamente antes de expirar, **para** que o atendente nunca seja deslogado durante uso ativo.

**Critérios de aceite:**
- [ ] CA-01: A cada interação HTTP bem-sucedida com `exp - now < 5min`, faz fetch a `POST /admin/refresh-token` em background
- [ ] CA-02: Refresh só ocorre se houve atividade do usuário nos últimos 60s (não renovar para sessões idle)
- [ ] CA-03: Falha do refresh: cai no fluxo normal (banner US-115 dispara em seguida)
- [ ] CA-04: Refresh bem-sucedido: substitui token sem notificação visual (silencioso)
- [ ] CA-05: Backend invalida o token antigo (blacklist em memória com TTL) após emitir o novo

**Status:** NOVO

---

### US-119 — Logout forçado em outra aba quando token invalidado
**Como** sistema, **quero** propagar logout para todas as abas abertas do mesmo atendente quando o token é invalidado, **para** garantir consistência de segurança.

**Critérios de aceite:**
- [ ] CA-01: Ao receber 401 em qualquer aba, envia mensagem `logout` via `BroadcastChannel('barbearia-admin')`
- [ ] CA-02: Todas as abas escutam e executam `localStorage.clear()` + redirect para login
- [ ] CA-03: Listener de `storage` event também detecta remoção da chave `token` em outra aba e dispara logout local
- [ ] CA-04: Antes de redirecionar, salva draft (US-116) se houver
- [ ] CA-05: Modal opcional explicando "Você foi desconectado em outra aba por inatividade ou logout."

**Status:** NOVO

---

## 27. Cenários Multi-Atendente

### US-120 — Sidebar mostra nome do atendente em conversas de outros
**Como** atendente, **quero** ver o nome de quem está atendendo cada conversa "em outro operador", **para** saber a quem pedir contexto ou supervisionar.

**Critérios de aceite:**
- [ ] CA-01: Backend retorna `atendente_nome` no payload de `/admin/conversas` (JOIN com tabela `atendentes`)
- [ ] CA-02: No item da sidebar, abaixo do preview, exibe linha "Com {nome}" em texto cinza pequeno quando `atendente_id !== null && !assumida_por_mim`
- [ ] CA-03: Quando `assumida_por_mim`, texto fica "Você está atendendo" em azul (`#2481cc`)
- [ ] CA-04: Resolve EDGE-02 documentado

**Status:** NOVO

---

### US-121 — Toast informativo: outro atendente assumiu a conversa antes
**Como** atendente, **quero** ver uma mensagem clara explicando quem assumiu a conversa que tentei pegar, **para** entender o contexto da concorrência.

**Critérios de aceite:**
- [ ] CA-01: Backend retorna no 409 de `/admin/assumir/{telefone}` o `atendente_nome` que assumiu (não só a mensagem genérica)
- [ ] CA-02: Frontend exibe toast vermelho: "Conversa assumida por {nome} antes de você."
- [ ] CA-03: Após o toast, `carregarConversas()` é disparado para sincronizar a sidebar
- [ ] CA-04: Header da thread atualiza para mostrar estado "outro" com nome do atendente

**Status:** NOVO

---

### US-122 — Dois atendentes enviam ao mesmo tempo: o segundo recebe 403
**Como** sistema, **quero** garantir que se dois operadores tentarem enviar mensagem na mesma conversa, apenas um vença, **para** evitar duplicação.

**Critérios de aceite:**
- [ ] CA-01: Backend (já implementado) retorna 403 "Você não assumiu essa conversa." quando `user.atendente_id != me.id`
- [ ] CA-02: Frontend exibe toast vermelho específico: "Outro atendente está respondendo essa conversa."
- [ ] CA-03: Bolha otimista é convertida em `bolha-falha` com indicador de erro
- [ ] CA-04: Listener SSE atualiza o estado da conversa em até 3s, refletindo no header

**Status:** NOVO

---

### US-123 — Modo supervisão: ler conversa de outro sem compositor
**Como** supervisor, **quero** abrir conversas de outros atendentes em modo leitura para acompanhar a qualidade do atendimento, **para** dar feedback ou treinar a equipe.

**Critérios de aceite:**
- [ ] CA-01: Atendente com papel `supervisor` (nova coluna `Atendente.papel`) pode abrir qualquer conversa
- [ ] CA-02: Quando supervisor abre conversa de outro: header mostra "Modo supervisão — somente leitura" com badge roxo
- [ ] CA-03: Compositor permanece em estado `outro_atendente` (read-only) mesmo se quisesse digitar
- [ ] CA-04: Notas internas continuam acessíveis para criação (supervisor pode adicionar contexto)
- [ ] CA-05: Backend permite GET mas bloqueia POST `/admin/enviar` mesmo para supervisor sem assumir antes

**Status:** NOVO

---

### US-124 — Transferência: atendente A devolve, atendente B recebe notificação
**Como** atendente B, **quero** ser notificado imediatamente quando uma conversa volta ao bot (ou para fila), **para** poder reassumir se necessário.

**Critérios de aceite:**
- [ ] CA-01: Evento SSE `bot_devolveu` (já implementado) é recebido por todos os atendentes online
- [ ] CA-02: Se `aguardando_humano=true` após devolver: toast informativo "Conversa devolvida ao bot por {nome}. Aguarda novo atendente." para os outros
- [ ] CA-03: Se a conversa estava aberta no painel de B: header atualiza e botão "Assumir" reaparece
- [ ] CA-04: Som de notificação suave (não o de transbordo, distinto)

**Status:** NOVO

---

### US-125 — Compositor bloqueado visualmente quando outro detém
**Como** atendente, **quero** ver claramente que o compositor está bloqueado quando outro atendente assumiu a conversa que estou observando, **para** não perder tempo tentando digitar.

**Critérios de aceite:**
- [ ] CA-01: Estado `outro` (US-063) já aplica `compositor-inativo`; adicionar overlay com ícone de cadeado discreto
- [ ] CA-02: Mensagem do banner: "Atendendo: {nome}. Você não pode enviar mensagens." (com nome dinâmico)
- [ ] CA-03: Hover no compositor exibe tooltip "Bloqueado — assumida por {nome}"
- [ ] CA-04: Cursor sobre o textarea: `not-allowed`

**Status:** NOVO

---

### US-126 — SSE notifica todos quando conversa muda de dono
**Como** sistema, **quero** propagar mudanças de propriedade de conversa para todos os atendentes em tempo real, **para** manter consistência visual da sidebar.

**Critérios de aceite:**
- [ ] CA-01: Evento `atendente_assumiu` já é publicado (US-081) — incluir `atendente_id` e `atendente_nome` no payload
- [ ] CA-02: Novo evento `conversa_transferida` quando supervisor força transferência (futuro)
- [ ] CA-03: Frontend reaplica `renderListaConversas()` imediatamente; se `telefone === conversaAtual`, recarrega thread para atualizar header e compositor
- [ ] CA-04: Resolve parcialmente GAP-08

**Status:** NOVO

---

## 28. Notificações Avançadas

### US-127 — Badge no título da aba com contagem de aguardando
**Como** atendente, **quero** ver no título da aba do browser quantas conversas estão aguardando, **para** monitorar mesmo com a aba minimizada.

**Critérios de aceite:**
- [ ] CA-01: `document.title` atualiza dinamicamente: `(N) Bolshoi` onde N = `metric-aguardando`
- [ ] CA-02: Quando N=0, título volta a "Bolshoi — Atendimento"
- [ ] CA-03: Atualização ocorre em todas as chamadas a `atualizarMetricas()`
- [ ] CA-04: Em browsers que suportam, opcionalmente usar `navigator.setAppBadge(N)` (PWA)

**Status:** NOVO

---

### US-128 — Desktop notification via Notification API
**Como** atendente, **quero** receber notificações do sistema operacional para novos transbordos, **para** ser alertado mesmo com a janela do browser em background.

**Critérios de aceite:**
- [ ] CA-01: No primeiro carregamento, exibe banner pedindo permissão: "Ative as notificações do sistema para ser alertado de novos atendimentos" com botão
- [ ] CA-02: `Notification.requestPermission()` é chamada após clique explícito (não automaticamente, para evitar bloqueio pelo browser)
- [ ] CA-03: Em `novo_transbordo` SSE, se permissão `granted` e `document.visibilityState !== 'visible'`: `new Notification(title, {body, icon, tag})`
- [ ] CA-04: Tag única por telefone evita stacking infinito de notificações do mesmo cliente
- [ ] CA-05: Clicar na notificação foca a aba e abre a conversa
- [ ] CA-06: Estado da permissão exibido no botão de mute (US-086) — três estados: ativo, mudo, sem permissão

**Status:** NOVO

---

### US-129 — Sons diferenciados: transbordo vs. mensagem em conversa ativa
**Como** atendente, **quero** distinguir auditivamente o som de novo transbordo (urgente) do som de nova mensagem em conversa já em andamento, **para** priorizar minha atenção.

**Critérios de aceite:**
- [ ] CA-01: `novo_transbordo`: dois bips ascendentes (880Hz + 1175Hz) — já implementado
- [ ] CA-02: `nova_mensagem` em conversa ativa minha: um bip único suave (660Hz, 100ms)
- [ ] CA-03: `nova_mensagem` em outra conversa (não ativa): sem som (apenas badge na sidebar)
- [ ] CA-04: Mute (US-086) silencia ambos
- [ ] CA-05: Volume configurável via slider no painel de configurações futuro (placeholder por ora — volume fixo 0.18)

**Status:** NOVO

---

### US-130 — Histórico de notificações (ícone de sino com últimas 5)
**Como** atendente, **quero** ver as últimas notificações recebidas em um menu, **para** revisar eventos que talvez não tenha percebido em tempo real.

**Critérios de aceite:**
- [ ] CA-01: Ícone de sino no header da sidebar; badge mostra contagem de não-lidas
- [ ] CA-02: Clique abre dropdown com até 5 últimas notificações: tipo (transbordo/mensagem/handoff), texto, tempo relativo, link
- [ ] CA-03: Cada item clicável abre a conversa associada (`abrirConversa(telefone)`)
- [ ] CA-04: Botão "Marcar todas como lidas" no rodapé do dropdown
- [ ] CA-05: Persistência em `localStorage('notif_history')` com TTL de 24h
- [ ] CA-06: Histórico limitado a 50 entradas (FIFO)

**Status:** NOVO

---

### US-131 — Mute por conversa individual
**Como** atendente, **quero** silenciar notificações de uma conversa específica (ex.: cliente que envia muitas mensagens curtas), **para** não ser interrompido por ela enquanto trabalho em outra.

**Critérios de aceite:**
- [ ] CA-01: Opção "Silenciar conversa" no popover de ações da thread (próximo ao botão de tag)
- [ ] CA-02: Persistência em `localStorage('muted_telefones')` como array
- [ ] CA-03: Em `nova_mensagem` SSE, se `muted_telefones.includes(telefone)`: não tocar som e não exibir toast
- [ ] CA-04: Indicador visual na sidebar: ícone de sino-cortado ao lado do nome
- [ ] CA-05: Mute por conversa expira após 4h automaticamente (configurável)
- [ ] CA-06: Botão "Reativar som" na thread silenciada

**Status:** NOVO

---

## 29. Respostas Rápidas Avançadas

### US-132 — Adicionar resposta rápida personalizada
**Como** atendente, **quero** criar respostas rápidas próprias além das pré-definidas, **para** acelerar atendimentos com textos que uso frequentemente.

**Critérios de aceite:**
- [ ] CA-01: Botão "+ Nova" no popover de respostas rápidas abre formulário inline com campos "Atalho" e "Texto"
- [ ] CA-02: Validação: atalho obrigatório (max 30 chars), texto obrigatório (max 1000 chars)
- [ ] CA-03: Persistência em `localStorage('respostas_rapidas_custom')` como array de `{id, atalho, texto, criado_em}`
- [ ] CA-04: Respostas customizadas aparecem após as pré-definidas, com badge "minha" pequeno
- [ ] CA-05: Limite de 20 respostas customizadas por atendente
- [ ] CA-06: Botão "Salvar" inativo se limite atingido com mensagem clarificadora

**Status:** NOVO

---

### US-133 — Remover resposta rápida personalizada
**Como** atendente, **quero** excluir respostas rápidas que não uso mais, **para** manter minha lista organizada.

**Critérios de aceite:**
- [ ] CA-01: Hover em resposta customizada exibe ícone X (lixeira) no canto direito
- [ ] CA-02: Clique no X exibe `confirm('Remover essa resposta rápida?')`
- [ ] CA-03: Confirmado: remove do array em `localStorage` e re-renderiza popover
- [ ] CA-04: Respostas pré-definidas (8 padrão) não exibem botão de remover
- [ ] CA-05: Toast: "Resposta rápida removida."

**Status:** NOVO

---

### US-134 — Atalho "/" abre lista de respostas rápidas
**Como** atendente, **quero** digitar "/" no compositor para abrir rapidamente o popover de respostas, **para** não precisar tirar a mão do teclado.

**Critérios de aceite:**
- [ ] CA-01: `keydown` no textarea com `key === '/'` e cursor na primeira coluna (ou textarea vazio) abre `#popover-rapidas`
- [ ] CA-02: O caractere "/" não é inserido no textarea (preventDefault)
- [ ] CA-03: Foco move-se para o primeiro item da lista; setas ↑↓ navegam; Enter seleciona; Esc fecha
- [ ] CA-04: Se houver texto antes do cursor, "/" é inserido normalmente (atalho só vale com textarea vazio)

**Status:** NOVO

---

### US-135 — Busca dentro do popover de respostas rápidas
**Como** atendente, **quero** filtrar respostas rápidas digitando parte do atalho ou texto, **para** localizar rapidamente em listas grandes.

**Critérios de aceite:**
- [ ] CA-01: Input de busca no topo do popover, abaixo do título
- [ ] CA-02: Filtragem em tempo real (case-insensitive, contém em atalho OU texto)
- [ ] CA-03: Lista exibe contador "X de Y respostas"
- [ ] CA-04: Esc limpa busca e fecha popover; Esc novamente fecha
- [ ] CA-05: Atalho "/" + texto já preenche o input automaticamente (ex.: "/sa" busca "sa")

**Status:** NOVO

---

### US-136 — Variáveis substituídas em respostas rápidas ({nome})
**Como** atendente, **quero** que respostas rápidas com a variável `{nome}` sejam preenchidas automaticamente com o primeiro nome do cliente atual, **para** personalizar saudações.

**Critérios de aceite:**
- [ ] CA-01: Ao selecionar resposta com `{nome}`, substitui pelo primeiro nome do `conversaAtual` (`usuario.nome.split(' ')[0]`)
- [ ] CA-02: Se cliente sem nome, substitui por "tudo bem" ou similar fallback neutro
- [ ] CA-03: Outras variáveis suportadas: `{telefone}`, `{atendente}` (nome do atendente logado), `{data}` (data atual em pt-BR)
- [ ] CA-04: Variáveis não reconhecidas permanecem literais para evitar bugs silenciosos
- [ ] CA-05: Documentação inline ao criar resposta (US-132) — placeholder "Use {nome} para inserir o nome do cliente"

**Status:** NOVO

---

## 30. Mensagens com Falha — Recuperação

### US-137 — Bolha de falha com ícone de aviso e botão "Tentar novamente"
**Como** atendente, **quero** ver um botão claro para reenviar mensagens que falharam, **para** não precisar redigitar.

**Critérios de aceite:**
- [ ] CA-01: Bolha-falha exibe ícone `⚠` em vermelho (`#ef4444`) no canto superior direito da bolha
- [ ] CA-02: Botão "Tentar novamente" (link clicável azul) abaixo do indicador de erro
- [ ] CA-03: Botão chama função `reenviarMensagem(tempId)` que dispara novo POST `/admin/enviar`
- [ ] CA-04: Durante a tentativa, botão fica desabilitado e bolha volta a `pending` (opacidade 60%)
- [ ] CA-05: Sucesso: bolha vira `bolha-outgoing-humano` normal; falha: permanece falha com nova tentativa disponível

**Status:** NOVO

---

### US-138 — "Tentar novamente" reenvia sem duplicar na UI
**Como** sistema, **quero** que o reenvio aproveite a mesma bolha visual ao invés de criar uma duplicata, **para** manter o histórico limpo.

**Critérios de aceite:**
- [ ] CA-01: `reenviarMensagem(tempId)` busca o elemento pela `data-temp-id` e reutiliza
- [ ] CA-02: O `tempId` é preservado durante o retry; apenas o estado visual muda
- [ ] CA-03: Backend grava em DB apenas em sucesso — falhas anteriores não criam registros órfãos
- [ ] CA-04: Se a mensagem original havia sido gravada com `entregue=false`, o retry deve atualizar o mesmo registro via PATCH ou recriar

**Status:** NOVO

---

### US-139 — Descartar mensagem falha (remover bolha)
**Como** atendente, **quero** poder descartar uma bolha de falha sem retry, **para** limpar mensagens que decidi não enviar mais.

**Critérios de aceite:**
- [ ] CA-01: Botão "Descartar" (X cinza) ao lado de "Tentar novamente"
- [ ] CA-02: Confirm antes de descartar: "Descartar essa mensagem?"
- [ ] CA-03: Confirmação remove a bolha do DOM
- [ ] CA-04: Se a mensagem foi gravada em DB com `entregue=false`, fazer DELETE `/admin/historico/{id}` (novo endpoint)
- [ ] CA-05: Toast: "Mensagem descartada."

**Status:** NOVO

---

### US-140 — Diferenciação de falha: rede vs. Meta API
**Como** atendente, **quero** entender se a falha foi por internet (minha) ou rejeição do WhatsApp (Meta), **para** saber se devo tentar de novo ou contatar o cliente por outro canal.

**Critérios de aceite:**
- [ ] CA-01: Falha de rede (catch em fetch, sem resposta HTTP): badge "Sem conexão" + ícone wi-fi cortado
- [ ] CA-02: Falha HTTP 5xx: badge "Servidor indisponível" + ícone servidor
- [ ] CA-03: Sucesso HTTP com `entregue: false` (Meta rejeitou): badge "WhatsApp recusou" + ícone Meta
- [ ] CA-04: Tooltip detalhado em cada caso explica causa provável e ação recomendada
- [ ] CA-05: Retry só é oferecido nos dois primeiros casos; no terceiro, sugere descartar ou contato externo

**Status:** NOVO

---

### US-141 — Botão "Reenviar todas as falhas" em massa
**Como** atendente, **quero** reenviar todas as mensagens falhas de uma vez após restabelecer conexão, **para** recuperar rapidamente de uma queda de rede.

**Critérios de aceite:**
- [ ] CA-01: Quando há ≥ 2 bolhas-falha na thread, exibe botão flutuante no topo da thread: "Reenviar N falhas"
- [ ] CA-02: Clique no botão exibe `confirm()` com contagem
- [ ] CA-03: Confirmado: itera sequencialmente (não paralelo, para preservar ordem) chamando `reenviarMensagem(tempId)` para cada
- [ ] CA-04: Progresso visual: botão muda para "Reenviando X/N…"
- [ ] CA-05: Ao final, toast resumo: "N reenviadas, M falharam novamente."

**Status:** NOVO

---

## 31. Edge Cases Formalizados

### US-142 — EDGE-01: Mensagem enviada durante race condition de devolução
**Como** sistema, **quero** lidar elegantemente com a situação em que o atendente envia uma mensagem exatamente quando a conversa é devolvida ao bot, **para** evitar UX confuso.

**Critérios de aceite:**
- [ ] CA-01: Quando POST `/admin/enviar` retorna 403 logo após uma operação SSE `bot_devolveu`, exibir toast específico: "Essa conversa foi devolvida ao bot durante seu envio."
- [ ] CA-02: Bolha vira `bolha-falha` com botão "Reassumir e reenviar" ao invés do retry padrão
- [ ] CA-03: "Reassumir e reenviar" chama POST `/admin/assumir/{telefone}` e, se sucesso, dispara `reenviarMensagem`
- [ ] CA-04: Se assumir falha (409 — outro pegou), exibe toast informativo e mantém a bolha-falha
- [ ] CA-05: Header da thread sincroniza com novo estado dentro de 2s

**Status:** NOVO (formaliza EDGE-01)

---

### US-143 — EDGE-02: Conversa sem nome de atendente exibido no status
**Como** atendente, **quero** sempre ver quem está com a conversa quando ela está "em outro operador", **para** poder coordenar ou supervisionar.

**Critérios de aceite:**
- [ ] CA-01: Backend (`/admin/conversas`) inclui `atendente_nome` via JOIN com tabela `atendentes`
- [ ] CA-02: Sidebar exibe linha auxiliar: "Atendendo: {nome}" para conversas com `atendente_id !== null && !assumida_por_mim`
- [ ] CA-03: Header da thread exibe "Em atendimento por {nome}" no lugar do genérico "Em atendimento por outro operador"
- [ ] CA-04: Quando `atendente_nome` for null (operador deletado mas conversa órfã), exibe "Atendente desconhecido" e libera a conversa via job manutenção
- [ ] CA-05: Resolve EDGE-02 e relaciona-se com US-120

**Status:** NOVO (formaliza EDGE-02)

---

### US-144 — EDGE-03: JWT expira com texto digitado no compositor
**Como** atendente, **quero** que o texto que estou compondo seja preservado se o JWT expirar durante a digitação, **para** não perder trabalho.

**Critérios de aceite:**
- [ ] CA-01: Implementa US-115, US-116, US-117 em conjunto
- [ ] CA-02: Antes de qualquer redirect por 401, executa `salvarDraftLocal()`
- [ ] CA-03: `salvarDraftLocal()` persiste `{telefone, texto, ts}` em `localStorage('draft_compositor')`
- [ ] CA-04: No primeiro carregamento pós-login, `restaurarDraft()` busca a chave, abre a conversa e preenche o textarea
- [ ] CA-05: Toast: "Continuando de onde parou: rascunho restaurado."

**Status:** NOVO (formaliza EDGE-03)

---

### US-145 — EDGE-04: Perda de eventos SSE durante janela de reconexão (3s)
**Como** sistema, **quero** recuperar eventos SSE perdidos durante uma reconexão, **para** não deixar atendentes sem notificação retroativa.

**Critérios de aceite:**
- [ ] CA-01: SSE endpoint passa a aceitar query param `?desde={ts_iso}` com timestamp da última mensagem recebida
- [ ] CA-02: Frontend salva `ultimoEventoTs` no localStorage a cada evento processado
- [ ] CA-03: Em reconexão, fetch passa `?desde={ultimoEventoTs}` — backend envia eventos pendentes em buffer (até 50 eventos / 5min)
- [ ] CA-04: Eventos antigos disparam UI mas sem som (para não bombardear ao reconectar)
- [ ] CA-05: Se gap > 5min: dispara `carregarConversas()` completo como fallback

**Status:** NOVO (formaliza EDGE-04)

---

### US-146 — EDGE-05: Preview do sidebar desatualizado após envio
**Como** atendente, **quero** ver o preview da sidebar atualizar instantaneamente após eu enviar uma mensagem, **para** ter feedback imediato.

**Critérios de aceite:**
- [ ] CA-01: Em sucesso de POST `/admin/enviar`, atualiza localmente o objeto `conversas[telefone]`: `preview = texto.slice(0,60)`, `data_ultima_interacao = now()`
- [ ] CA-02: Chama `renderListaConversas()` imediatamente (sem esperar refresh de 30s)
- [ ] CA-03: O item da conversa atual sobe para o topo (re-ordenação local) se não estava lá
- [ ] CA-04: Se o `carregarConversas()` periódico vier antes do envio confirmado, o preview otimista é mantido até reconciliação
- [ ] CA-05: Resolve EDGE-05

**Status:** NOVO (formaliza EDGE-05)

---

### US-147 — EDGE-06: Conversa sem mensagens ainda aparece na lista
**Como** sistema, **quero** que conversas sem nenhuma mensagem sejam ocultas da lista por padrão, **para** evitar itens vazios confusos.

**Critérios de aceite:**
- [ ] CA-01: Backend `/admin/conversas` adiciona filtro `INNER JOIN historico_conversa` ou subquery `EXISTS (SELECT 1 FROM historico ...)`
- [ ] CA-02: Conversas sem histórico não aparecem na lista padrão
- [ ] CA-03: Filtro opcional `?incluir_vazias=true` para diagnóstico/admin
- [ ] CA-04: Se um cliente novo manda primeira mensagem, SSE `nova_mensagem` faz a conversa aparecer naturalmente
- [ ] CA-05: Resolve EDGE-06

**Status:** NOVO (formaliza EDGE-06)

---

### US-148 — EDGE-07: Validação client-side de comprimento de nota
**Como** atendente, **quero** ser alertado imediatamente se uma nota exceder o limite, **para** não perder tempo escrevendo texto que será rejeitado.

**Critérios de aceite:**
- [ ] CA-01: Textarea de nota recebe atributo `maxlength="4096"` no HTML
- [ ] CA-02: Contador visual abaixo do textarea: "X / 4096 caracteres" — fica laranja em > 90%, vermelho em > 100%
- [ ] CA-03: Botão "Adicionar nota" desabilitado se length > 4096
- [ ] CA-04: Aviso ao colar texto longo: "Texto truncado para o limite de 4096 caracteres"
- [ ] CA-05: Resolve EDGE-07

**Status:** NOVO (formaliza EDGE-07)

---

### US-149 — EDGE-08: JWT_SECRET ausente exibe mensagem amigável
**Como** atendente, **quero** ver uma mensagem clara e não-técnica se houver problema de configuração do servidor, **para** saber a quem pedir ajuda.

**Critérios de aceite:**
- [ ] CA-01: Backend continua retornando 503 com `detail: "JWT_SECRET ausente"` (mantém para debug do desenvolvedor)
- [ ] CA-02: Frontend intercepta especificamente 503 no login e exibe: "Sistema temporariamente fora do ar. Contate o suporte: suporte@bolshoi.com"
- [ ] CA-03: Detalhes técnicos ficam disponíveis em `console.error` para diagnóstico
- [ ] CA-04: Botão "Tentar novamente" ao invés de redirect automático
- [ ] CA-05: Se sysadmin estiver online, envia notificação interna (canal Slack/Teams via webhook) — fora do escopo desta US, marcar como dependência
- [ ] CA-06: Resolve EDGE-08

**Status:** NOVO (formaliza EDGE-08)

---

*Expansão v1.1 gerada em 2026-05-19. Novas stories US-101 a US-149 (49 stories adicionais) cobrindo histórico avançado, ciclo de vida do atendente, gestão de JWT, cenários multi-atendente, notificações avançadas, respostas rápidas customizáveis, recuperação de falhas e formalização dos 8 edge cases originais (EDGE-01 a EDGE-08 → US-142 a US-149).*

*Total de user stories no documento: 149.*
## Fase 1-3 — Features Chatwoot-style (2026-05-21)

**Versão:** 2.0
**Data:** 2026-05-21
**Escopo:** 12 features novas (Labels múltiplas, Status de conversa, Canned dinâmicas, Atribuição, @mentions, Bulk, Presence, Saved Views, Search global, Atalhos, Tema, Integrações).
**Numeração:** US-150 em diante (continuação de US-149).
**Stack relevante:** `api/admin.py`, `db/models.py`, `static/admin/index.html`, `static/admin/settings.html`, `static/admin/js/app.js`, `static/admin/js/api.js`, `static/admin/js/sse.js`.

---

## 32. Labels Múltiplas Coloridas (Fase 1)

### US-150: Listar labels disponíveis para atribuir
**Como** atendente
**Quero** ver todas as etiquetas ativas no catálogo
**Para** escolher quais aplicar a conversas

**Critérios de Aceite:**
- [ ] CA-01: GET `/admin/labels` retorna lista ordenada por `nome` apenas com `ativo=True` (padrão)
- [ ] CA-02: Cada item contém `{id, nome, cor (hex #RRGGBB), descricao, ativo, criado_em}`
- [ ] CA-03: Frontend chama `carregarLabelsGlobais()` no bootstrap e cacheia em `state.allLabels`
- [ ] CA-04: Picker do info panel (`#label-picker-list`) renderiza apenas labels ainda não atribuídas à conversa atual
- [ ] CA-05: Lista vazia exibe "Sem etiquetas disponíveis" em itálico cinza

**Estado atual:** IMPLEMENTADO
**Arquivos relevantes:** `api/admin.py:1127-1145`, `static/admin/js/app.js:694-783`, `static/admin/js/api.js:97-98`

---

### US-151: Criar nova label via settings
**Como** supervisor
**Quero** cadastrar uma etiqueta nova com nome, cor e descrição
**Para** organizar conversas em categorias customizadas

**Critérios de Aceite:**
- [ ] CA-01: Tab "Etiquetas" em `/static/admin/settings.html` exibe tabela com botão "Nova Etiqueta"
- [ ] CA-02: Modal abre com inputs: `label-nome` (pattern `^[a-z0-9_-]+$`, 1-50 chars), `label-cor` (color picker + hex text), `label-descricao` (opcional, max 200)
- [ ] CA-03: Color picker e campo hex são sincronizados (input bidirecional)
- [ ] CA-04: POST `/admin/labels` com `{nome, cor, descricao}` retorna 201 com objeto criado
- [ ] CA-05: Backend valida pattern e unicidade (`Label.nome` é único) — 409 com mensagem clara
- [ ] CA-06: Após sucesso: toast verde "Etiqueta criada", modal fecha, tabela recarrega

**Estado atual:** IMPLEMENTADO
**Arquivos relevantes:** `api/admin.py:1148-1166`, `static/admin/settings.html:213-247`, `static/admin/settings.html:667-690`

---

### US-152: Criar label inline na conversa (autocomplete)
**Como** atendente
**Quero** criar uma etiqueta diretamente do picker da conversa quando não existe
**Para** etiquetar rapidamente sem navegar até settings

**Critérios de Aceite:**
- [ ] CA-01: Quando atendente digita query no `#label-search` e nenhuma label corresponde exatamente: exibe item "+ Criar etiqueta {query}"
- [ ] CA-02: Item de criar só aparece se a query é válida pelo pattern `^[a-z0-9_-]+$`
- [ ] CA-03: Clique chama `criarEAplicarLabel(query)` — POST `/admin/labels` com cor aleatória de paleta de 8 (`#6366f1, #10b981, #f59e0b, #ef4444, #a855f7, #3b82f6, #ec4899, #14b8a6`)
- [ ] CA-04: Após criação, `aplicarLabel(novaId)` atribui automaticamente à conversa
- [ ] CA-05: `state.allLabels` é atualizado em memória sem precisar refazer GET `/admin/labels`

**Estado atual:** IMPLEMENTADO
**Arquivos relevantes:** `static/admin/js/app.js:766-827`

---

### US-153: Editar label existente
**Como** supervisor
**Quero** alterar nome, cor ou descrição de uma etiqueta já criada
**Para** corrigir typos ou refinar o catálogo

**Critérios de Aceite:**
- [ ] CA-01: Botão "Editar" na linha da tabela de etiquetas reabre o modal com dados pré-preenchidos via `editarLabel(l)`
- [ ] CA-02: PATCH `/admin/labels/{id}` com campos opcionais: `nome`, `cor`, `descricao`, `ativo`
- [ ] CA-03: Backend valida pattern e unicidade ao mudar nome (409 se duplicado, ignora se igual ao atual)
- [ ] CA-04: Alterar `cor` é refletido imediatamente nos chips das conversas (após próximo carregamento)
- [ ] CA-05: Resposta retorna objeto completo da label (id, nome, cor, descricao, ativo)

**Estado atual:** IMPLEMENTADO
**Arquivos relevantes:** `api/admin.py:1168-1194`, `static/admin/settings.html:507-515`, `static/admin/settings.html:667-690`

---

### US-154: Desativar label (soft delete)
**Como** supervisor
**Quero** remover uma etiqueta sem perder o histórico de quais conversas a tinham
**Para** descontinuar categorias sem corromper dados

**Critérios de Aceite:**
- [ ] CA-01: Botão "Desativar" na tabela exibe `confirm('Desativar etiqueta? Conversas mantêm a associação até serem editadas.')`
- [ ] CA-02: DELETE `/admin/labels/{id}` marca `ativo=False` (NÃO remove fisicamente)
- [ ] CA-03: Associações em `usuario_labels` são preservadas — chips ainda aparecem nas conversas até serem removidos manualmente
- [ ] CA-04: GET `/admin/labels` (padrão) deixa de listar labels inativas; `?incluir_inativas=true` mostra todas
- [ ] CA-05: Tab settings com `?incluir_inativas=true` mostra badge "Inativa" cinza e botão "Reativar"

**Estado atual:** IMPLEMENTADO
**Arquivos relevantes:** `api/admin.py:1197-1209`, `static/admin/settings.html:517-532`

---

### US-155: Reativar label previamente desativada
**Como** supervisor
**Quero** voltar a usar uma etiqueta que havia desativado
**Para** restaurar categorias sem ter que recriar e perder histórico

**Critérios de Aceite:**
- [ ] CA-01: Botão "Reativar" só aparece para labels com `ativo=false` na tab settings
- [ ] CA-02: PATCH `/admin/labels/{id}` com `{ativo: true}` reativa
- [ ] CA-03: Label volta a aparecer no picker da conversa e no GET padrão
- [ ] CA-04: Toast verde "Etiqueta reativada"

**Estado atual:** IMPLEMENTADO
**Arquivos relevantes:** `static/admin/settings.html:526-532`

---

### US-156: Atribuir label a uma conversa (info panel)
**Como** atendente
**Quero** adicionar uma etiqueta à conversa aberta via picker no info panel
**Para** classificar o contexto do atendimento

**Critérios de Aceite:**
- [ ] CA-01: Botão "+ Adicionar" na seção "ETIQUETAS" do info panel abre `#label-picker`
- [ ] CA-02: Input `#label-search` filtra labels disponíveis em tempo real (não-debounce)
- [ ] CA-03: Picker mostra apenas labels que ainda não estão atribuídas (já assinadas são excluídas via `assigned` Set)
- [ ] CA-04: POST `/admin/conversa/{telefone}/labels` body `{label_id}` retorna 201
- [ ] CA-05: Chip aparece imediatamente no info panel e no card da sidebar (atualização local em `state.usuarioAtual.labels` e `conv.labels`)
- [ ] CA-06: Picker é fechado após seleção; input é limpo

**Estado atual:** IMPLEMENTADO
**Arquivos relevantes:** `api/admin.py:1212-1246`, `static/admin/js/app.js:785-812`, `static/admin/index.html:486-496`

---

### US-157: Idempotência ao atribuir label duplicada (race condition)
**Como** sistema
**Quero** que duas requisições simultâneas para atribuir a mesma label não falhem
**Para** evitar erros visíveis em cenários de concorrência (cliques rápidos, abas múltiplas)

**Critérios de Aceite:**
- [ ] CA-01: Backend tenta INSERT direto; em `IntegrityError` por PK composta duplicada (`telefone_usuario, label_id`), faz rollback e retorna 200 com `{ok: true, ja_atribuida: true}`
- [ ] CA-02: `IntegrityError` que NÃO é "Duplicate entry" é logado como warning (ex.: FK violation por dado corrompido)
- [ ] CA-03: Frontend trata 200 normalmente — não exibe erro
- [ ] CA-04: `atribuido_em` e `atribuido_por` da primeira inserção são preservados

**Estado atual:** IMPLEMENTADO
**Arquivos relevantes:** `api/admin.py:1228-1245`

---

### US-158: Remover label de uma conversa
**Como** atendente
**Quero** clicar no X de um chip para tirar a etiqueta da conversa
**Para** corrigir classificação incorreta

**Critérios de Aceite:**
- [ ] CA-01: Cada chip no info panel tem botão `×` (renderizado por `labelChipRemovableHTML`)
- [ ] CA-02: Clique chama `removerLabelConversa(labelId)` → DELETE `/admin/conversa/{telefone}/labels/{label_id}` retorna 204
- [ ] CA-03: Backend retorna 404 se associação não existe (`result.rowcount == 0`)
- [ ] CA-04: Frontend atualiza `state.usuarioAtual.labels`, `conv.labels` em memória e re-renderiza info panel + sidebar
- [ ] CA-05: Toast vermelho "Erro ao remover etiqueta" em falha

**Estado atual:** IMPLEMENTADO
**Arquivos relevantes:** `api/admin.py:1249-1266`, `static/admin/js/app.js:714-730`

---

### US-159: Chips coloridos visíveis no card da conversa (sidebar)
**Como** atendente
**Quero** ver as etiquetas de uma conversa diretamente no card da sidebar
**Para** identificar categoria sem abrir a conversa

**Critérios de Aceite:**
- [ ] CA-01: GET `/admin/conversas` retorna `labels: [{id, nome, cor}, ...]` por item (batch query em `usuario_labels` JOIN `labels` filtrada `ativo=true`)
- [ ] CA-02: `renderConvList()` injeta chips abaixo do nome+preview via `labelChipsHTML(c.labels)`
- [ ] CA-03: Cada chip tem `background: {cor}20` (12.5% alpha) e `color: {cor}` para legibilidade no fundo do card
- [ ] CA-04: Quando `labels.length > 0`, chips substituem o badge legacy `tag` (fallback para `tagBadgeHTML` se ainda houver tag e nenhuma label)
- [ ] CA-05: Conversa sem labels não exibe nenhum chip

**Estado atual:** IMPLEMENTADO
**Arquivos relevantes:** `api/admin.py:343-374`, `static/admin/js/app.js:179-186`, `static/admin/js/app.js:258`

---

### US-160: Coexistência label nova + tag legacy
**Como** sistema
**Quero** preservar conversas com o `tag` string antigo enquanto migra para labels múltiplas
**Para** não quebrar dados pré-existentes durante a transição

**Critérios de Aceite:**
- [ ] CA-01: Coluna `Usuario.tag` permanece e endpoint `PATCH /admin/conversa/{telefone}/tag` continua funcional (legacy)
- [ ] CA-02: GET `/admin/conversas` retorna ambos: `tag` (string ou null) e `labels` (array)
- [ ] CA-03: Card da sidebar prioriza renderizar `labels` se houver; senão usa `tag` legacy
- [ ] CA-04: Header da thread continua exibindo `thread-tag-badge` baseado em `usuario.tag`
- [ ] CA-05: Não há migração automática de `tag` → `Label` (decisão consciente para permitir convivência)

**Estado atual:** IMPLEMENTADO
**Arquivos relevantes:** `api/admin.py:1100-1120`, `static/admin/js/app.js:258`, `static/admin/js/app.js:499-509`

---

### US-161: Seed inicial de labels do sistema
**Como** sistema
**Quero** que uma instalação nova venha com etiquetas básicas pré-criadas
**Para** o atendente ter referência imediata sem precisar criar do zero

**Critérios de Aceite:**
- [ ] CA-01: Seed contém: `resolvido` (verde), `follow_up` (laranja), `vip` (dourado/púrpura), `reclamacao` (vermelho), `fidelidade` (azul)
- [ ] CA-02: Seed executado em script de bootstrap ou migration; idempotente (não duplica em re-execução)
- [ ] CA-03: Labels seed têm `descricao` explicativa cada uma
- [ ] CA-04: Atendente pode editar nome/cor das seed ou desativar normalmente

**Estado atual:** NÃO IMPLEMENTADO — modelo `Label` existe e endpoint cria labels, mas não há script de seed inicial no repositório (`scripts/migrations/`).
**Arquivos relevantes:** `db/models.py:163-174`, `scripts/migrations/0001_notas_editado.sql` (sem seed de labels)

---

### US-162: Validação de cor inválida ao criar label
**Como** sistema
**Quero** rejeitar cores que não sigam o formato hexadecimal `#RRGGBB`
**Para** garantir consistência visual e evitar quebras de CSS

**Critérios de Aceite:**
- [ ] CA-01: `LabelIn.cor` valida pattern `^#[0-9a-fA-F]{6}$` no Pydantic
- [ ] CA-02: Cor com 3 dígitos (`#fff`), sem `#`, RGB(), ou nome (`red`) → 422 Unprocessable Entity
- [ ] CA-03: Frontend exibe erro genérico "Erro ao salvar" no `#modal-label-erro`
- [ ] CA-04: Input HTML5 `type="color"` no modal sempre gera formato válido (fallback seguro)
- [ ] CA-05: Input `label-cor-hex` (text) tem pattern HTML5 `#[0-9a-fA-F]{6}` para feedback do browser

**Estado atual:** IMPLEMENTADO
**Arquivos relevantes:** `api/admin.py:92`, `static/admin/settings.html:230-232`

---

### US-163: Permissões — qualquer atendente cria/edita/deleta label
**Como** atendente
**Quero** poder criar labels mesmo sem ser supervisor
**Para** flexibilidade na operação do dia-a-dia

**Critérios de Aceite:**
- [ ] CA-01: Endpoints `POST/PATCH/DELETE /admin/labels` exigem apenas `atendente_atual` (qualquer JWT válido)
- [ ] CA-02: Não há diferenciação de papel (supervisor vs atendente) no backend atual
- [ ] CA-03: Frontend não esconde botões de "Nova/Editar/Desativar" baseado em papel
- [ ] CA-04: GAP documentado: não há audit log de quem criou/desativou label

**Estado atual:** IMPLEMENTADO (sem role-based)
**Arquivos relevantes:** `api/admin.py:1148-1209`

---

## 33. Status de Conversa (Fase 1)

### US-164: Filtrar conversas por status na sidebar
**Como** atendente
**Quero** ver apenas conversas "Abertas", "Pendentes", "Resolvidas" ou "Adiadas"
**Para** focar em subconjuntos por estado de ciclo de vida

**Critérios de Aceite:**
- [ ] CA-01: Row `#status-filter-row` com 5 botões: `open`, `pending`, `resolved`, `snoozed`, `todas`
- [ ] CA-02: Default é `open` (esconde resolved/snoozed do dashboard normal)
- [ ] CA-03: Clique aplica `state.statusFiltro` e dispara `carregarConversas()`
- [ ] CA-04: GET `/admin/conversas?status=open` filtra via `Usuario.status_conversa == "open"`
- [ ] CA-05: Botão ativo recebe `color: var(--accent)` e `background: rgba(99,102,241,0.15)`

**Estado atual:** IMPLEMENTADO
**Arquivos relevantes:** `api/admin.py:209-275`, `static/admin/index.html:280-287`, `static/admin/js/app.js:1770-1786`

---

### US-165: Alterar status via dropdown no header da thread
**Como** atendente
**Quero** mudar o status da conversa aberta com um clique
**Para** registrar o avanço do atendimento (resolver, adiar etc.)

**Critérios de Aceite:**
- [ ] CA-01: Botão `#btn-status` no header da thread abre `#status-popover` com 4 opções
- [ ] CA-02: Cada opção (`.status-option`) tem `data-status` e cor visual (azul/laranja/verde/cinza)
- [ ] CA-03: Clique em "Aberta", "Pendente" ou "Resolvida" chama `alterarStatus(novo)` → PATCH `/admin/conversa/{telefone}/status`
- [ ] CA-04: Label do botão `#btn-status-label` atualiza para refletir status atual ("Aberta", "Pendente", "Resolvida", "Adiada")
- [ ] CA-05: Cor do botão muda dinamicamente via `statusColor(s)`
- [ ] CA-06: Popover fecha ao clicar fora (listener global no document)

**Estado atual:** IMPLEMENTADO
**Arquivos relevantes:** `api/admin.py:1273-1330`, `static/admin/index.html:356-375`, `static/admin/js/app.js:839-896`, `static/admin/js/app.js:1805-1812`

---

### US-166: Confirmação ao marcar como resolvida
**Como** atendente
**Quero** confirmar antes de marcar uma conversa como resolvida
**Para** evitar resolver acidentalmente e ver a conversa sumir do dashboard

**Critérios de Aceite:**
- [ ] CA-01: Antes do PATCH, `confirm('Marcar conversa como resolvida? Ela sairá da lista padrão.')` é exibido
- [ ] CA-02: Cancelar não chama o endpoint
- [ ] CA-03: Confirmar dispara PATCH com `{status: "resolved"}`
- [ ] CA-04: Backend grava `resolved_em = now()` e `resolved_por = me.id` na transição `não-resolved → resolved`
- [ ] CA-05: Conversa some da lista se filtro atual não inclui resolvidas

**Estado atual:** IMPLEMENTADO
**Arquivos relevantes:** `static/admin/js/app.js:853-855`, `api/admin.py:1306-1308`

---

### US-167: Adiar conversa (snooze) com prompt de horas
**Como** atendente
**Quero** adiar uma conversa por X horas
**Para** despriorizar atendimentos que precisam aguardar (ex.: cliente disse que retornará amanhã)

**Critérios de Aceite:**
- [ ] CA-01: Selecionar "Adiar (snooze)…" chama `alterarStatus('snoozed')`
- [ ] CA-02: `prompt('Adiar conversa por quantas horas?', '24')` solicita input
- [ ] CA-03: Validação: `1 <= h <= 720` (1h a 30 dias); fora do range → toast vermelho "Horas inválidas (1-720)"
- [ ] CA-04: `snoozed_until = new Date(Date.now() + h * 3600 * 1000).toISOString()`
- [ ] CA-05: PATCH com `{status: "snoozed", snoozed_until: ISO}`
- [ ] CA-06: Backend valida que `snoozed_until` é futuro (não pode ser <= now) — 400 se inválido

**Estado atual:** IMPLEMENTADO
**Arquivos relevantes:** `static/admin/js/app.js:842-852`, `api/admin.py:1288-1298`

---

### US-168: Auto-unsnooze quando prazo expira
**Como** sistema
**Quero** rebater conversas snoozed para `open` automaticamente quando `snoozed_until` passa
**Para** garantir que conversas adiadas voltem à fila no horário marcado

**Critérios de Aceite:**
- [ ] CA-01: `_auto_unsnooze(db)` executado no início de cada GET `/admin/conversas`
- [ ] CA-02: UPDATE em batch: `status_conversa = "open"`, `snoozed_until = NULL` para todas onde `snoozed_until <= now()`
- [ ] CA-03: Não publica evento SSE — atendente vê a mudança no próximo carregamento da lista
- [ ] CA-04: Trade-off aceito: latência de até 60s (refresh periódico do dashboard) entre prazo expirar e conversa reaparecer

**Estado atual:** IMPLEMENTADO
**Arquivos relevantes:** `api/admin.py:184-195`, `api/admin.py:235`

---

### US-169: snoozed_until com timezone naive interpretado como UTC
**Como** sistema
**Quero** aceitar `snoozed_until` ISO sem timezone e interpretá-lo como UTC
**Para** evitar bugs de fuso na transição backend ↔ frontend

**Critérios de Aceite:**
- [ ] CA-01: Backend parseia `datetime.fromisoformat(s.replace("Z","+00:00"))`
- [ ] CA-02: Se resultado é naive (sem tzinfo), aplica `replace(tzinfo=timezone.utc)`
- [ ] CA-03: Comparação `dt <= now(UTC)` é sempre tz-aware
- [ ] CA-04: Resposta sempre serializa com sufixo Z via `_iso_utc()`
- [ ] CA-05: Frontend gera ISO via `toISOString()` (que sempre inclui Z)

**Estado atual:** IMPLEMENTADO
**Arquivos relevantes:** `api/admin.py:1290-1298`, `api/admin.py:20-32`

---

### US-170: Transição resolved → outro limpa marcadores de resolução
**Como** sistema
**Quero** que reabrir uma conversa resolvida limpe `resolved_em` e `resolved_por`
**Para** não manter timestamp inconsistente em conversas reabertas

**Critérios de Aceite:**
- [ ] CA-01: Se `status_anterior == "resolved"` e `novo != "resolved"`: `resolved_em=NULL`, `resolved_por=NULL`
- [ ] CA-02: Em transições `não-resolved → não-resolved` (ex.: open → pending), preserva campos (irrelevantes mas não há cleanup)
- [ ] CA-03: Em `resolved → resolved` (no-op): preserva timestamp e autor originais (não sobrescreve)
- [ ] CA-04: Comportamento documentado em comment no código

**Estado atual:** IMPLEMENTADO
**Arquivos relevantes:** `api/admin.py:1300-1314`

---

### US-171: SSE event `status_alterado` propaga mudança a outros atendentes
**Como** atendente
**Quero** ver a sidebar atualizar quando outro operador resolve/adia uma conversa
**Para** manter consistência multi-atendente em tempo real

**Critérios de Aceite:**
- [ ] CA-01: Backend publica `{tipo: "status_alterado", telefone, status, snoozed_until, por_atendente_id}` após PATCH
- [ ] CA-02: Frontend atualiza `conv.status_conversa` e `conv.snoozed_until` em memória
- [ ] CA-03: Se `conversaAtual === ev.telefone`: atualiza `state.usuarioAtual` e chama `atualizarStatusBadgeHeader()`
- [ ] CA-04: Se status mudou e não corresponde ao filtro atual: chama `carregarConversas()` para reordenar
- [ ] CA-05: Caso contrário: apenas `renderConvList()`

**Estado atual:** IMPLEMENTADO
**Arquivos relevantes:** `api/admin.py:1318-1324`, `static/admin/js/app.js:1558-1576`

---

### US-172: Conversa some da lista local quando muda status fora do filtro atual
**Como** atendente
**Quero** que conversas mudem de lista automaticamente quando troco o status
**Para** ver feedback imediato da minha ação

**Critérios de Aceite:**
- [ ] CA-01: Após sucesso de `alterarStatus(novo)`, se `state.statusFiltro !== 'todas' && state.statusFiltro !== novoStatus`: remove a conversa de `state.conversas` localmente e re-renderiza
- [ ] CA-02: Se o filtro inclui o novo status: apenas atualiza o card existente
- [ ] CA-03: Toast verde `Status alterado para {label}` em todos os casos
- [ ] CA-04: Não há necessidade de re-fetch da lista completa (otimização)

**Estado atual:** IMPLEMENTADO
**Arquivos relevantes:** `static/admin/js/app.js:866-878`

---

### US-173: Status snoozed exige snoozed_until obrigatório
**Como** sistema
**Quero** rejeitar mudança para `snoozed` sem prazo de retorno
**Para** evitar conversas eternamente adiadas

**Critérios de Aceite:**
- [ ] CA-01: PATCH com `{status: "snoozed"}` e sem `snoozed_until` → 400 "snoozed_until obrigatório para status=snoozed"
- [ ] CA-02: Formato ISO inválido → 400 "snoozed_until com formato inválido (use ISO 8601)"
- [ ] CA-03: `snoozed_until <= now()` → 400 "snoozed_until deve ser futuro"
- [ ] CA-04: Status não-snoozed ignora `snoozed_until` se enviado (set como `NULL`)

**Estado atual:** IMPLEMENTADO
**Arquivos relevantes:** `api/admin.py:1288-1302`

---

### US-174: Status conversa não interage com bot_ativo (ortogonal)
**Como** sistema
**Quero** que status de conversa seja ortogonal a `bot_ativo` e `aguardando_humano`
**Para** permitir combinações como "bot ativo + resolved" sem conflito

**Critérios de Aceite:**
- [ ] CA-01: PATCH `/admin/conversa/{telefone}/status` não altera `bot_ativo`, `aguardando_humano` ou `atendente_id`
- [ ] CA-02: Resolver uma conversa não desliga o bot — cliente pode continuar interagindo
- [ ] CA-03: Bot pode responder em conversa `resolved` (cliente envia nova mensagem, bot recebe, atendente vê na busca)
- [ ] CA-04: Decisão consciente: status é "marcador organizacional", não interrompe fluxo

**Estado atual:** IMPLEMENTADO
**Arquivos relevantes:** `api/admin.py:1273-1330` (não toca em bot_ativo)

---

### US-175: Default status open ao criar Usuario
**Como** sistema
**Quero** que todo Usuario novo nasça com `status_conversa = "open"`
**Para** garantir consistência inicial

**Critérios de Aceite:**
- [ ] CA-01: Coluna `Usuario.status_conversa` tem `default="open"` no SQLAlchemy
- [ ] CA-02: Usuários pré-existentes (antes da migration) podem ter NULL → frontend trata como "open" (`status_conversa: u.status_conversa or "open"`)
- [ ] CA-03: GET `/admin/conversa/{telefone}` também aplica fallback `or "open"`
- [ ] CA-04: Filtro `status=open` no GET `/admin/conversas` captura tanto `NULL` quanto `"open"` (após próxima migration recomendada)

**Estado atual:** PARCIAL — fallback aplicado no resposta JSON, mas filtro SQL `Usuario.status_conversa == "open"` NÃO captura NULL. Migration de backfill recomendada.
**Arquivos relevantes:** `db/models.py:33`, `api/admin.py:370`, `api/admin.py:418`, `api/admin.py:274-275`

---

## 34. Canned Responses com Placeholders (Fase 1)

### US-176: Listar canned responses (globais + pessoais)
**Como** atendente
**Quero** ver respostas rápidas globais e as minhas pessoais
**Para** ter acesso ao catálogo completo no compositor

**Critérios de Aceite:**
- [ ] CA-01: GET `/admin/canned` retorna `CannedResponse` onde `atendente_id IS NULL OR atendente_id == me.id`
- [ ] CA-02: Ordenação por `atalho` ASC
- [ ] CA-03: Cada item: `{id, atalho, texto, atendente_id, criado_em, atualizado_em}`
- [ ] CA-04: Frontend cacheia em `CANNED_RESPONSES` no bootstrap
- [ ] CA-05: Tab "Respostas rápidas" em settings mostra todas com badge "Global" (verde) ou "Pessoal" (azul)

**Estado atual:** IMPLEMENTADO
**Arquivos relevantes:** `api/admin.py:1356-1379`, `static/admin/js/app.js:33-41`, `static/admin/settings.html:537-576`

---

### US-177: Criar canned response pessoal
**Como** atendente
**Quero** criar uma resposta rápida que só eu vejo
**Para** ter atalhos personalizados sem poluir o catálogo global

**Critérios de Aceite:**
- [ ] CA-01: Tab settings > "Nova Resposta" abre modal `#modal-canned`
- [ ] CA-02: Campos: `canned-atalho` (pattern `/[a-z0-9_-]+`, 2-30 chars), `canned-texto` (max 4096), `canned-escopo` (select `pessoal`/`global`)
- [ ] CA-03: Escopo padrão = "pessoal" — backend cria com `atendente_id = me.id`
- [ ] CA-04: POST `/admin/canned` retorna 201
- [ ] CA-05: Atalho duplicado no mesmo escopo → 409 "Atalho '{x}' já existe nesse escopo"

**Estado atual:** IMPLEMENTADO
**Arquivos relevantes:** `api/admin.py:1382-1406`, `static/admin/settings.html:249-283`, `static/admin/settings.html:693-717`

---

### US-178: Criar canned response global
**Como** atendente
**Quero** criar uma resposta rápida disponível para todos os atendentes
**Para** padronizar respostas frequentes da equipe

**Critérios de Aceite:**
- [ ] CA-01: Select escopo = "global" no modal → backend cria com `atendente_id = NULL`
- [ ] CA-02: Validação de atalho único entre globais (separado de pessoais)
- [ ] CA-03: Outros atendentes veem a global no próximo refresh da lista
- [ ] CA-04: Decisão consciente: qualquer atendente pode criar globais (sem role check)
- [ ] CA-05: Toast "Resposta criada" após sucesso

**Estado atual:** IMPLEMENTADO
**Arquivos relevantes:** `api/admin.py:1389`, `static/admin/settings.html:268-273`

---

### US-179: Editar canned pessoal — só o dono pode
**Como** sistema
**Quero** que apenas o autor de uma canned pessoal possa editá-la
**Para** garantir privacidade dos atalhos pessoais

**Critérios de Aceite:**
- [ ] CA-01: PATCH `/admin/canned/{id}` verifica `c.atendente_id != me.id` quando `c.atendente_id is not None`
- [ ] CA-02: Em violação: 403 "Você não pode editar canned response de outro atendente"
- [ ] CA-03: Frontend só mostra botões "Editar/Excluir" se `!c.atendente_id || c.atendente_id === EU_ID`
- [ ] CA-04: Lista mostra "—" no lugar dos botões para canned pessoais de outros (não devem aparecer mesmo no GET, mas defesa em profundidade)

**Estado atual:** IMPLEMENTADO
**Arquivos relevantes:** `api/admin.py:1420-1421`, `static/admin/settings.html:560-564`

---

### US-180: Editar canned global — qualquer atendente
**Como** sistema
**Quero** que qualquer atendente possa editar canned globais
**Para** permitir colaboração no catálogo compartilhado

**Critérios de Aceite:**
- [ ] CA-01: Para canned com `atendente_id IS NULL`, não há check de ownership no PATCH
- [ ] CA-02: Mesmo para DELETE — qualquer atendente pode excluir globais
- [ ] CA-03: Risco aceito: não há audit log de quem editou
- [ ] CA-04: GAP futuro: log de alterações em globais para reverter mudanças indevidas

**Estado atual:** IMPLEMENTADO (sem audit)
**Arquivos relevantes:** `api/admin.py:1416-1443`

---

### US-181: Autocomplete /xxx no compositor
**Como** atendente
**Quero** digitar `/sa` para ver respostas rápidas que começam com "sa"
**Para** inserir canned sem tirar a mão do teclado

**Critérios de Aceite:**
- [ ] CA-01: `input` no `#msg-input` detecta padrão regex `(^|\s)(\/[a-z0-9_-]*)$` no final do texto
- [ ] CA-02: Match abre `#canned-popover` com lista filtrada via `renderCannedPopover(match[2])`
- [ ] CA-03: Filtro: `c.atalho.toLowerCase().includes(q) || c.texto.toLowerCase().includes(q)`
- [ ] CA-04: Sem match (texto sem `/` no fim): popover fecha
- [ ] CA-05: Posição do popover: `bottom-full left-0 mb-2`

**Estado atual:** IMPLEMENTADO
**Arquivos relevantes:** `static/admin/js/app.js:1702-1720`, `static/admin/js/app.js:1421-1473`

---

### US-182: Inserir canned via clique (substitui atalho digitado)
**Como** atendente
**Quero** clicar numa canned do popover para substituir o atalho `/xxx` pelo texto completo
**Para** evitar ter que apagar o atalho manualmente

**Critérios de Aceite:**
- [ ] CA-01: Clique no `.canned-item` chama handler que detecta `matchAtalho` no texto atual do input
- [ ] CA-02: Se há match: `input.value = atual.substring(0, matchAtalho.index) + (matchAtalho[1] || '') + previewCanned(item.texto)`
- [ ] CA-03: Se não há match (popover aberto manualmente via botão): substitui valor inteiro
- [ ] CA-04: Foco retorna ao input, `Event('input')` re-dispara para auto-resize
- [ ] CA-05: Popover fecha após seleção

**Estado atual:** IMPLEMENTADO
**Arquivos relevantes:** `static/admin/js/app.js:1450-1472`

---

### US-183: Tab/Enter no popover seleciona primeira opção
**Como** atendente
**Quero** apertar Tab ou Enter para inserir a primeira canned da lista
**Para** fluxo de teclado completo sem mouse

**Critérios de Aceite:**
- [ ] CA-01: `keydown` no `#msg-input` com popover visível: `Tab` ou `Enter` (sem Shift) → `preventDefault()` + `first.click()`
- [ ] CA-02: Esc com popover visível: fecha popover (sem enviar mensagem)
- [ ] CA-03: Enter sem popover visível: comportamento normal (envia mensagem)
- [ ] CA-04: Funciona mesmo com popover aberto via botão (não só via atalho `/`)

**Estado atual:** IMPLEMENTADO
**Arquivos relevantes:** `static/admin/js/app.js:1721-1742`

---

### US-184: Placeholders substituídos no envio
**Como** atendente
**Quero** que `{nome_cliente}`, `{primeiro_nome}`, `{atendente}` e `{barbearia}` sejam trocados pelos valores reais antes de enviar
**Para** personalizar saudações sem ter que editar manualmente

**Critérios de Aceite:**
- [ ] CA-01: Backend `POST /admin/enviar` chama `_substituir_placeholders(texto, user, me)` antes do envio WhatsApp
- [ ] CA-02: `{nome_cliente}` → `user.nome_cliente` (ou "cliente" se NULL/vazio)
- [ ] CA-03: `{primeiro_nome}` → primeira palavra do nome (split por espaço)
- [ ] CA-04: `{atendente}` → `atendente.nome` (do JWT)
- [ ] CA-05: `{barbearia}` → string fixa "Barbearia Bolshoi"
- [ ] CA-06: Placeholders desconhecidos (ex.: `{telefone}`) permanecem literais — atendente revisa antes de enviar
- [ ] CA-07: Substituição também ocorre em mensagens enviadas via "Assumir" (não, esse texto é fixo no backend)

**Estado atual:** IMPLEMENTADO
**Arquivos relevantes:** `api/admin.py:1337-1353`, `api/admin.py:929-931`

---

### US-185: Preview no popover mostra placeholders substituídos
**Como** atendente
**Quero** ver na lista de canneds como o texto ficará após substituição
**Para** confirmar que vai enviar a coisa certa

**Critérios de Aceite:**
- [ ] CA-01: `previewCanned(texto)` substitui placeholders no frontend usando `state.usuarioAtual` e `state.eu`
- [ ] CA-02: Cada item do popover exibe `preview` truncado abaixo do atalho
- [ ] CA-03: Mesma substituição quando o atendente clica para inserir (texto inserido já tem placeholders trocados visualmente)
- [ ] CA-04: Se `state.usuarioAtual` é null (nenhuma conversa aberta), preview mostra texto bruto (sem substituir)

**Estado atual:** IMPLEMENTADO
**Arquivos relevantes:** `static/admin/js/app.js:43-54`, `static/admin/js/app.js:1435`

---

### US-186: Validação backend rejeita atalho sem barra inicial
**Como** sistema
**Quero** garantir que atalhos sempre comecem com `/`
**Para** consistência com o padrão de invocação no compositor

**Critérios de Aceite:**
- [ ] CA-01: `CannedIn.atalho` valida pattern `^/[a-z0-9_-]+$` no Pydantic
- [ ] CA-02: Atalho `saudacao` (sem `/`) → 422 Unprocessable Entity
- [ ] CA-03: Atalho `/Saudacao` (maiúsculas) → 422
- [ ] CA-04: Caracteres especiais (`@`, `!`, espaço) → 422
- [ ] CA-05: Tamanho 2-30 chars

**Estado atual:** IMPLEMENTADO
**Arquivos relevantes:** `api/admin.py:113`, `static/admin/settings.html:261`

---

### US-187: Mudança de escopo pessoal ↔ global na edição
**Como** atendente
**Quero** poder converter uma canned pessoal em global (e vice-versa)
**Para** compartilhar uma resposta que ficou útil para a equipe

**Critérios de Aceite:**
- [ ] CA-01: PATCH com `escopo: "global"` em canned pessoal: backend muda `atendente_id` para NULL
- [ ] CA-02: PATCH com `escopo: "pessoal"` em canned global: backend muda `atendente_id` para `me.id` (passa a ser do editor)
- [ ] CA-03: Se já era global e atendente A muda para pessoal: vira pessoal DE A (outros perdem acesso)
- [ ] CA-04: Decisão consciente: não há confirmação especial; histórico não rastreia mudança de escopo

**Estado atual:** IMPLEMENTADO
**Arquivos relevantes:** `api/admin.py:1435-1437`

---

### US-188: Edge case — autocomplete `/` aciona em todo `/` digitado
**Como** atendente
**Quero** que o autocomplete só apareça quando estou começando um atalho
**Para** não interferir em respostas que tenham `/` no meio (ex.: URL)

**Critérios de Aceite:**
- [ ] CA-01: Regex `(^|\s)(\/[a-z0-9_-]*)$` exige que o `/` seja precedido por início de texto ou espaço
- [ ] CA-02: Digitar `https://exemplo.com` NÃO abre popover
- [ ] CA-03: Digitar texto e depois `/foo` no fim abre popover (com espaço antes)
- [ ] CA-04: Popover fecha quando o cursor sai do contexto do atalho (mais texto após)

**Estado atual:** IMPLEMENTADO
**Arquivos relevantes:** `static/admin/js/app.js:1711`

---

## 35. Atribuição entre Atendentes (Fase 2)

### US-189: Botão Transferir visível apenas para o dono atual
**Como** atendente (dono)
**Quero** ver o botão "Transferir" no header da minha conversa
**Para** poder passar o atendimento para outro operador

**Critérios de Aceite:**
- [ ] CA-01: `syncComposerState()` mostra `#btn-transferir` apenas quando `meuAtendimento === true`
- [ ] CA-02: Em outros estados (aguardando, bot ativo, outro atendente): `#btn-transferir` permanece `hidden`
- [ ] CA-03: Clique abre `#transferir-popover` com lista de outros atendentes ativos
- [ ] CA-04: Ícone do botão é seta de troca, label "Transferir"

**Estado atual:** IMPLEMENTADO
**Arquivos relevantes:** `static/admin/js/app.js:536-542`, `static/admin/index.html:346-353`, `static/admin/js/app.js:1794-1803`

---

### US-190: Listar atendentes disponíveis (exceto eu) no dropdown
**Como** atendente
**Quero** ver a lista de outros atendentes ativos para escolher destino
**Para** transferir para a pessoa certa

**Critérios de Aceite:**
- [ ] CA-01: `carregarAtendentesParaTransfer()` chama GET `/admin/atendentes` e filtra `a.ativo`
- [ ] CA-02: `abrirPopoverTransferir()` filtra `a.id !== state.eu.id` (sem self)
- [ ] CA-03: Cada item exibe avatar (inicial em background accent), nome, status de presença (dot colorido + label)
- [ ] CA-04: Se não há outros ativos: "Nenhum outro atendente ativo" em itálico
- [ ] CA-05: Cache em `state.allAtendentes` evita refetch a cada abertura

**Estado atual:** IMPLEMENTADO
**Arquivos relevantes:** `static/admin/js/app.js:903-945`

---

### US-191: Confirmar e transferir
**Como** atendente
**Quero** confirmar antes de transferir
**Para** evitar transferência acidental

**Critérios de Aceite:**
- [ ] CA-01: `confirm('Transferir conversa para {nome}?')` antes do POST
- [ ] CA-02: Cancelar não chama o endpoint
- [ ] CA-03: POST `/admin/conversa/{telefone}/atribuir` body `{atendente_id}` retorna `{ok, atendente_id, atendente_nome}`
- [ ] CA-04: Toast verde "Conversa transferida para {nome}"
- [ ] CA-05: `carregarConversas()` é chamado — a conversa some da minha lista (filtro "Meus")

**Estado atual:** IMPLEMENTADO
**Arquivos relevantes:** `static/admin/js/app.js:947-961`, `api/admin.py:857-912`

---

### US-192: UPDATE condicional impede transferência se não sou dono
**Como** sistema
**Quero** que só o dono atual consiga transferir
**Para** evitar que terceiros mudem propriedade arbitrariamente

**Critérios de Aceite:**
- [ ] CA-01: Backend verifica `user.atendente_id != me.id` → 403 "Você precisa ser o dono atual para transferir"
- [ ] CA-02: UPDATE com `atendente_id == me.id` como filtro WHERE — se afetou 0 linhas: 409 "Conversa não pertence mais a você"
- [ ] CA-03: Race condition: dois cliques simultâneos resultam em apenas uma transferência
- [ ] CA-04: Frontend exibe erro genérico via toast vermelho

**Estado atual:** IMPLEMENTADO
**Arquivos relevantes:** `api/admin.py:870-890`

---

### US-193: Destino inválido (inexistente ou inativo)
**Como** sistema
**Quero** rejeitar transferência para atendente que não existe ou está inativo
**Para** evitar conversas em limbo

**Critérios de Aceite:**
- [ ] CA-01: Backend busca destino com `Atendente.id == payload.atendente_id, Atendente.ativo == True`
- [ ] CA-02: Não encontrado: 404 "Atendente destino não encontrado ou inativo"
- [ ] CA-03: Destino == eu: 400 "Você já é o dono desta conversa"
- [ ] CA-04: Frontend filtra inativos antes de exibir no popover (defesa em profundidade)

**Estado atual:** IMPLEMENTADO
**Arquivos relevantes:** `api/admin.py:874-881`

---

### US-194: Histórico registra evento de transferência
**Como** sistema
**Quero** gravar a transferência como evento no histórico
**Para** auditoria e contexto futuro

**Critérios de Aceite:**
- [ ] CA-01: Após UPDATE bem-sucedido, INSERT em `HistoricoConversa`: `resposta_bot = "[Sistema] Conversa transferida de {nome} para {nome}"`, `origem = "humano"`, `intencao = "transferencia"`, `atendente_id = destino.id`, `entregue = None`
- [ ] CA-02: Mensagem NÃO é enviada ao cliente via WhatsApp (apenas registro interno)
- [ ] CA-03: Aparece no histórico da thread como bolha de atendente (futuro: poderia ser separador de evento)
- [ ] CA-04: `entregue = None` evita ícone de delivery na bolha

**Estado atual:** IMPLEMENTADO
**Arquivos relevantes:** `api/admin.py:893-902`

---

### US-195: SSE `conversa_atribuida` notifica origem, destino e demais
**Como** atendente
**Quero** que todos os atendentes vejam a mudança de dono em tempo real
**Para** manter sidebar sincronizada

**Critérios de Aceite:**
- [ ] CA-01: Backend publica `{tipo: "conversa_atribuida", telefone, de_atendente_id, para_atendente_id, para_atendente_nome}`
- [ ] CA-02: Todos os atendentes recebem e chamam `carregarConversas()`
- [ ] CA-03: Se conversa estava aberta: recarrega via `api.getConversa()` para atualizar header e compositor
- [ ] CA-04: Destinatário recebe toast `Conversa transferida para você` + som de notificação
- [ ] CA-05: Origem perde o botão "Transferir" e ganha read-only via `syncComposerState`

**Estado atual:** IMPLEMENTADO
**Arquivos relevantes:** `api/admin.py:904-910`, `static/admin/js/app.js:1538-1556`

---

### US-196: Dot de presença dos atendentes no dropdown
**Como** atendente
**Quero** ver quais destinos estão online antes de transferir
**Para** evitar transferir para alguém ausente

**Critérios de Aceite:**
- [ ] CA-01: Cada item do popover de transferir renderiza dot pequeno (`w-2 h-2 absolute bottom-0 right-0`) com cor de presença
- [ ] CA-02: Cores: online=#10b981, away=#f59e0b, offline=#6b7280
- [ ] CA-03: Label de status ao lado do nome: "Online", "Ausente", "Offline"
- [ ] CA-04: Dot tem `border-color: var(--bg-card)` para separação visual do avatar
- [ ] CA-05: Atualização live via SSE `presence_changed` — popover re-renderiza se já aberto

**Estado atual:** IMPLEMENTADO
**Arquivos relevantes:** `static/admin/js/app.js:921-933`, `static/admin/js/app.js:1522-1528`

---

### US-197: Transferência funciona quando origem está offline (dono original)
**Como** sistema
**Quero** considerar offline do dono como caso normal
**Para** transferências feitas por supervisores funcionarem (no contexto de bulk; ver US-205)

**Critérios de Aceite:**
- [ ] CA-01: Endpoint individual `POST /atribuir` exige `me.id == user.atendente_id` (apenas o dono pode)
- [ ] CA-02: Para reatribuir de offline → outro: usar `POST /admin/conversas/bulk` com ação `atribuir` (admin-level, sem ownership check)
- [ ] CA-03: GAP documentado: não há endpoint individual de "force transfer" para supervisor sem ser dono atual
- [ ] CA-04: Possível impacto: conversas ficam órfãs se atendente desativado e supervisor não usar bulk

**Estado atual:** IMPLEMENTADO (com gap de UX)
**Arquivos relevantes:** `api/admin.py:870-890`, `api/admin.py:800-808`

---

## 36. @mentions em Notas Internas (Fase 2)

### US-198: Autocomplete @ na textarea de notas
**Como** atendente
**Quero** digitar `@` para ver lista de atendentes para mencionar
**Para** notificar colegas de forma estruturada

**Critérios de Aceite:**
- [ ] CA-01: `input` em `#note-input` detecta regex `(^|\s)(@[a-z0-9_]*)$` no final do texto
- [ ] CA-02: Match abre `#mention-autocomplete` posicionado acima da textarea (`posicionarAutocomplete`)
- [ ] CA-03: Filtra `state.allAtendentes` por `a.id !== state.eu.id && a.usuario_login.includes(q)`
- [ ] CA-04: Sem matches: popover fecha
- [ ] CA-05: Sem `state.allAtendentes` em cache: chama `carregarAtendentesParaTransfer()` antes
- [ ] CA-06: Esc fecha popover

**Estado atual:** IMPLEMENTADO
**Arquivos relevantes:** `static/admin/js/app.js:1297-1334`, `static/admin/js/app.js:1903-1925`

---

### US-199: Inserir mention via clique no autocomplete
**Como** atendente
**Quero** clicar no nome do colega para inserir `@login`
**Para** mencionar sem ter que digitar o login completo

**Critérios de Aceite:**
- [ ] CA-01: Clique no `.mention-opt` substitui `@xxx` parcial pelo `@login ` completo (com espaço final)
- [ ] CA-02: Cursor mantém posição correta após inserção
- [ ] CA-03: Popover fecha após inserção
- [ ] CA-04: Foco retorna à textarea

**Estado atual:** IMPLEMENTADO
**Arquivos relevantes:** `static/admin/js/app.js:1317-1333`

---

### US-200: Parser regex extrai @logins ao salvar nota
**Como** sistema
**Quero** detectar todos os `@user_login` no texto da nota
**Para** criar notificações apropriadas

**Critérios de Aceite:**
- [ ] CA-01: Regex `_REGEX_MENTION = re.compile(r'@([a-z0-9_]{3,50})')` no backend
- [ ] CA-02: `findall(nota.texto.lower())` extrai todos os logins (case-insensitive)
- [ ] CA-03: Set deduplica menções múltiplas do mesmo login
- [ ] CA-04: Pattern exige 3+ chars (consistente com pattern de criação de atendente)
- [ ] CA-05: Padrões inválidos (ex.: `@ab`, `@ABC`) são ignorados silenciosamente

**Estado atual:** IMPLEMENTADO
**Arquivos relevantes:** `api/admin.py:1607-1618`

---

### US-201: Valida atendente existe e está ativo antes de notificar
**Como** sistema
**Quero** criar notificações apenas para logins válidos e atendentes ativos
**Para** não gerar mentions órfãs

**Critérios de Aceite:**
- [ ] CA-01: Query: `Atendente.usuario_login.in_(logins), Atendente.ativo == True, Atendente.id != autor.id`
- [ ] CA-02: Self-mention é ignorada (não cria notificação para o próprio autor)
- [ ] CA-03: Login que não existe é silenciosamente ignorado (sem erro 4xx)
- [ ] CA-04: Atendente desativado não recebe mention
- [ ] CA-05: Se nenhum atendente válido → retorna lista vazia (sem inserts)

**Estado atual:** IMPLEMENTADO
**Arquivos relevantes:** `api/admin.py:1619-1630`

---

### US-202: Persistir notificação em mention_notificacoes
**Como** sistema
**Quero** gravar uma linha por menção em tabela dedicada
**Para** manter inbox auditável e marcável como lida

**Critérios de Aceite:**
- [ ] CA-01: Para cada atendente válido, INSERT em `MentionNotificacao`: `{atendente_id, nota_id, telefone_usuario, mencionado_por, lida=false}`
- [ ] CA-02: Índice composto `idx_mn_atendente_lida` otimiza filtros do inbox
- [ ] CA-03: ON DELETE CASCADE de `Atendente` e `NotaInterna` remove notificações órfãs
- [ ] CA-04: `mencionado_por` usa ON DELETE SET NULL (preserva notificação se autor for deletado)
- [ ] CA-05: `criado_em` é UTC timestamp

**Estado atual:** IMPLEMENTADO
**Arquivos relevantes:** `db/models.py:207-223`, `api/admin.py:1632-1641`

---

### US-203: SSE `nova_mention` dispara toast e som
**Como** atendente
**Quero** ser notificado imediatamente quando alguém me menciona
**Para** ter awareness em tempo real

**Critérios de Aceite:**
- [ ] CA-01: Backend publica `{tipo: "nova_mention", atendente_id, telefone, mencionado_por, mencionado_por_nome, nota_id, preview}` para cada destinatário
- [ ] CA-02: Frontend filtra: apenas reage se `ev.atendente_id === state.eu.id`
- [ ] CA-03: Toast vermelho (`transbordo`) "{nome} mencionou você"
- [ ] CA-04: Som de notificação tocado (`tocarNotificacao`)
- [ ] CA-05: `carregarMentions()` é chamado para atualizar badge contador

**Estado atual:** IMPLEMENTADO
**Arquivos relevantes:** `api/admin.py:1644-1652`, `static/admin/js/app.js:1530-1536`

---

### US-204: Badge contador de mentions no sidebar
**Como** atendente
**Quero** ver quantas menções não-lidas tenho
**Para** priorizar leitura quando volto à aba

**Critérios de Aceite:**
- [ ] CA-01: Badge `#mentions-badge` ao lado do botão sino no icon sidebar
- [ ] CA-02: Cor de fundo `var(--danger)` (vermelho); texto branco; tamanho mínimo 18px
- [ ] CA-03: Mostra contagem; se > 99 exibe "99+"
- [ ] CA-04: Hidden quando contagem = 0
- [ ] CA-05: Atualiza após cada SSE `nova_mention` e a cada 60s via `setInterval(carregarMentions, 60000)` (backup)

**Estado atual:** IMPLEMENTADO
**Arquivos relevantes:** `static/admin/index.html:202`, `static/admin/js/app.js:979-989`, `static/admin/js/app.js:1938`

---

### US-205: Popover inbox lista mentions com preview
**Como** atendente
**Quero** abrir um popover para ver minhas menções recentes
**Para** revisar e navegar para as conversas

**Critérios de Aceite:**
- [ ] CA-01: Clique no botão sino abre `#mentions-popover` (fixed, w-80, max-h-96, custom-scrollbar)
- [ ] CA-02: GET `/admin/mentions/inbox` retorna até 100 items: `{id, lida, criado_em, lida_em, telefone, nome_cliente, mencionado_por_nome, nota_texto, nota_id}`
- [ ] CA-03: Default `apenas_nao_lidas=true` filtra; query param pode forçar todas
- [ ] CA-04: Cada item: dot azul (não-lida) ou opacidade 0.5 (lida), nome mencionador → nome cliente, preview da nota, tempo relativo
- [ ] CA-05: Estado vazio: "Nenhuma menção"

**Estado atual:** IMPLEMENTADO
**Arquivos relevantes:** `api/admin.py:1674-1705`, `static/admin/index.html:205-209`, `static/admin/js/app.js:991-1035`

---

### US-206: Clique numa mention abre conversa e marca como lida
**Como** atendente
**Quero** navegar para a conversa direto da mention
**Para** ler o contexto rapidamente

**Critérios de Aceite:**
- [ ] CA-01: Clique no item dispara `api.marcarMentionLida(id)` → PATCH `/admin/mentions/{id}/marcar-lida`
- [ ] CA-02: Backend valida ownership (`mn.atendente_id != me.id` → 403)
- [ ] CA-03: Marca `lida=true` e `lida_em=now()`; se já lida: retorna `{ok: true, ja_lida: true}` (idempotente)
- [ ] CA-04: Frontend atualiza `state.mentions` localmente e recalcula `unread`
- [ ] CA-05: Popover fecha e `abrirConversa(telefone)` é chamado

**Estado atual:** IMPLEMENTADO
**Arquivos relevantes:** `api/admin.py:1708-1725`, `static/admin/js/app.js:1016-1034`

---

### US-207: Mention em atendente offline persiste para próximo login
**Como** atendente
**Quero** ver mentions feitas enquanto estava offline ao voltar
**Para** não perder solicitações de colegas

**Critérios de Aceite:**
- [ ] CA-01: Notificações são persistidas no DB (não só em memória) — sobrevivem a restart e logout
- [ ] CA-02: `lida=false` por padrão até ser explicitamente marcada
- [ ] CA-03: GET `/admin/mentions/inbox?apenas_nao_lidas=true` retorna tudo pendente
- [ ] CA-04: SSE `nova_mention` é perdido se atendente offline — mas persistência cobre
- [ ] CA-05: Badge é atualizado no bootstrap via `carregarMentions()`

**Estado atual:** IMPLEMENTADO
**Arquivos relevantes:** `db/models.py:207-223`, `static/admin/js/app.js:1930` (bootstrap chama carregarMentions)

---

### US-208: Mention para login inexistente — silencioso
**Como** atendente
**Quero** que erros de digitação no `@` não bloqueiem o salvamento da nota
**Para** não perder o texto se eu errar o login do colega

**Critérios de Aceite:**
- [ ] CA-01: Nota é salva mesmo se `@xpto_invalido` não corresponde a nenhum atendente
- [ ] CA-02: `_processar_mentions` retorna lista vazia silenciosamente
- [ ] CA-03: Resposta de criar nota: `{ok, id, mencionados: []}` — atendente vê que nenhum foi notificado
- [ ] CA-04: Não há erro visual no frontend; nota aparece normalmente
- [ ] CA-05: Atendente pode editar a nota depois para corrigir (US edge: editar nota não re-processa mentions — GAP)

**Estado atual:** PARCIAL — salvamento silencioso funciona; editar nota NÃO re-processa mentions (gap).
**Arquivos relevantes:** `api/admin.py:1656-1667`, `api/admin.py:1744-1791`

---

### US-209: Permissão — só o dono pode marcar como lida
**Como** sistema
**Quero** impedir que outros atendentes marquem mentions alheias como lidas
**Para** preservar integridade do inbox de cada um

**Critérios de Aceite:**
- [ ] CA-01: PATCH `/admin/mentions/{id}/marcar-lida` verifica `mn.atendente_id != me.id` → 403 "Notificação não pertence a você"
- [ ] CA-02: GET `/admin/mentions/inbox` retorna apenas mentions do `me.id`
- [ ] CA-03: Frontend não tem UI para ver mentions alheias (defesa em profundidade)

**Estado atual:** IMPLEMENTADO
**Arquivos relevantes:** `api/admin.py:1715-1725`

---

## 37. Bulk Actions (Fase 2)

### US-210: Selecionar múltiplas conversas via checkbox
**Como** atendente
**Quero** marcar várias conversas para ação em lote
**Para** processar fila de forma eficiente

**Critérios de Aceite:**
- [ ] CA-01: Cada card da sidebar renderiza `<input type="checkbox" class="bulk-check">` com `data-tel`
- [ ] CA-02: Checkbox visível apenas quando há pelo menos uma seleção (`bulkActive = state.bulkSelecionadas.size > 0`)
- [ ] CA-03: Click no avatar do card também faz toggle (`toggleBulkSelecao`) — atalho UX
- [ ] CA-04: Cards selecionados ganham classe `bulk-selected` para destaque visual
- [ ] CA-05: `event.stopPropagation()` no checkbox impede abrir a conversa ao marcar

**Estado atual:** IMPLEMENTADO
**Arquivos relevantes:** `static/admin/js/app.js:1050-1077`, `static/admin/js/app.js:246-248`, `static/admin/js/app.js:1858-1867`

---

### US-211: Top bar com contagem e ações em lote
**Como** atendente
**Quero** ver uma barra superior mostrando quantas selecionei e quais ações posso fazer
**Para** ter feedback do estado e gatilho rápido

**Critérios de Aceite:**
- [ ] CA-01: `#bulk-bar` aparece quando `state.bulkSelecionadas.size > 0`
- [ ] CA-02: Texto: "N selecionada(s)" (plural condicional)
- [ ] CA-03: Botões: "✓ Resolver", "⏰ Adiar", "✕ Cancelar"
- [ ] CA-04: Fundo `var(--accent)`, texto branco, posicionado abaixo do filter row
- [ ] CA-05: Cancelar limpa `state.bulkSelecionadas`, esconde a barra e re-renderiza lista

**Estado atual:** IMPLEMENTADO
**Arquivos relevantes:** `static/admin/index.html:289-296`, `static/admin/js/app.js:1060-1077`, `static/admin/js/app.js:1870-1872`

---

### US-212: Bulk resolver
**Como** atendente
**Quero** marcar várias conversas como resolvidas de uma vez
**Para** limpar a lista rapidamente após resolver vários atendimentos

**Critérios de Aceite:**
- [ ] CA-01: Clique em "Resolver" exibe `confirm('Marcar N conversa(s) como resolvidas?')`
- [ ] CA-02: POST `/admin/conversas/bulk` body `{telefones: [...], acao: "resolver", parametros: {}}`
- [ ] CA-03: Backend itera cada telefone: set `status_conversa="resolved"`, `resolved_em=now()`, `resolved_por=me.id`
- [ ] CA-04: Toast: "N conversa(s) resolvida(s) (X falharam)"
- [ ] CA-05: `limparBulkSelecao()` e `carregarConversas()` após sucesso

**Estado atual:** IMPLEMENTADO
**Arquivos relevantes:** `static/admin/js/app.js:1079-1092`, `api/admin.py:780-784`

---

### US-213: Bulk snooze
**Como** atendente
**Quero** adiar várias conversas pelo mesmo prazo
**Para** despriorizar grupo de atendimentos não-urgentes

**Critérios de Aceite:**
- [ ] CA-01: Clique em "Adiar" exibe `prompt('Adiar N conversa(s) por quantas horas?', '24')`
- [ ] CA-02: Validação igual ao snooze individual: 1 <= h <= 720
- [ ] CA-03: POST com `{acao: "snooze", parametros: {snoozed_until: ISO}}`
- [ ] CA-04: Backend valida cada item (mesmo critério); falha individual não para o batch
- [ ] CA-05: Toast: "N conversa(s) adiada(s) por Xh"

**Estado atual:** IMPLEMENTADO
**Arquivos relevantes:** `static/admin/js/app.js:1276-1295`, `api/admin.py:785-799`

---

### US-214: Bulk atribuir (admin-level, ignora ownership)
**Como** supervisor
**Quero** atribuir várias conversas para um atendente específico de uma vez
**Para** distribuir carga ou redirecionar fila

**Critérios de Aceite:**
- [ ] CA-01: Endpoint aceita `{acao: "atribuir", parametros: {atendente_id}}`
- [ ] CA-02: Ao contrário do `/atribuir` individual: NÃO verifica ownership — qualquer atendente autenticado pode reatribuir
- [ ] CA-03: Conversas afetadas têm: `atendente_id = dest_id`, `bot_ativo = false`, `aguardando_humano = false`
- [ ] CA-04: Falta de `atendente_id` em `parametros` → erro item-level "atendente_id obrigatório"
- [ ] CA-05: Frontend NÃO tem UI exposta para essa ação (GAP — endpoint pronto, mas botão "Atribuir" não aparece na bulk bar)

**Estado atual:** PARCIAL — backend completo; UI não expõe a ação `atribuir` na bulk bar.
**Arquivos relevantes:** `api/admin.py:800-808`, `static/admin/index.html:289-296` (apenas resolver/snooze/cancelar)

---

### US-215: Bulk label_add e label_remove
**Como** atendente
**Quero** adicionar ou remover uma etiqueta em várias conversas
**Para** classificar grupo inteiro de uma vez

**Critérios de Aceite:**
- [ ] CA-01: `{acao: "label_add", parametros: {label_id}}` — backend INSERT idempotente em `usuario_labels`
- [ ] CA-02: Idempotência via guard SELECT — se associação já existe, no-op (não erro)
- [ ] CA-03: `{acao: "label_remove", parametros: {label_id}}` — backend DELETE
- [ ] CA-04: `label_id` ausente em parametros → erro item-level "label_id obrigatório"
- [ ] CA-05: Frontend NÃO expõe UI para essas ações (GAP — endpoint pronto, sem botões na bulk bar)

**Estado atual:** PARCIAL — backend completo; UI não expõe.
**Arquivos relevantes:** `api/admin.py:810-838`

---

### US-216: Resposta granular {sucesso, falha} não para em erro parcial
**Como** atendente
**Quero** que falhas em alguns itens não interrompam o processamento do resto
**Para** maximizar throughput em batches grandes

**Critérios de Aceite:**
- [ ] CA-01: Backend retorna `{sucesso: [tel1, tel2, ...], falha: [{telefone, erro}, ...]}`
- [ ] CA-02: Cada telefone é processado em try/except — exceção individual loga `log.exception` e continua
- [ ] CA-03: Telefones de clientes inexistentes vão para `falha` com erro "não encontrado"
- [ ] CA-04: Commit único no final agrupa todos os successes
- [ ] CA-05: Toast no frontend mostra "N sucesso (M falharam)" — apenas se M > 0

**Estado atual:** IMPLEMENTADO
**Arquivos relevantes:** `api/admin.py:770-854`

---

### US-217: Limite 1-200 telefones por requisição bulk
**Como** sistema
**Quero** rejeitar batches absurdamente grandes
**Para** evitar travamento de DB e abuso

**Critérios de Aceite:**
- [ ] CA-01: `BulkIn.telefones = Field(..., min_length=1, max_length=200)` no Pydantic
- [ ] CA-02: Lista vazia → 422 Unprocessable Entity
- [ ] CA-03: Lista com 201+ → 422
- [ ] CA-04: Frontend não impõe limite explícito (atendente improvável de selecionar 200+ via UI)
- [ ] CA-05: Erro 422 cai no catch genérico do `_req` e exibe toast "Erro ao processar bulk"

**Estado atual:** IMPLEMENTADO
**Arquivos relevantes:** `api/admin.py:133`

---

### US-218: SSE `bulk_aplicado` informa total afetado
**Como** atendente
**Quero** ver feedback no dashboard quando outro atendente faz uma ação bulk
**Para** entender mudanças massivas que ocorrem

**Critérios de Aceite:**
- [ ] CA-01: Backend publica `{tipo: "bulk_aplicado", acao, afetadas: len(sucesso), por_atendente_id}`
- [ ] CA-02: Evento atual NÃO é tratado especificamente no frontend (não há handler `sse:bulk_aplicado`) — GAP UX
- [ ] CA-03: Refresh periódico de `carregarConversas()` eventualmente sincroniza a sidebar
- [ ] CA-04: Recomendação futura: toast informativo "{nome} resolveu N conversas em bulk"

**Estado atual:** PARCIAL — backend publica, frontend não consome.
**Arquivos relevantes:** `api/admin.py:847-852`, `static/admin/js/app.js:1478-1589` (sem listener `sse:bulk_aplicado`)

---

### US-219: Limpar seleção ao trocar de aba/filtro
**Como** atendente
**Quero** que minha seleção não persista entre filtros diferentes
**Para** evitar agir em conversas que sumiram da vista

**Critérios de Aceite:**
- [ ] CA-01: Mudar filtro (`#filter-tabs`) NÃO limpa `state.bulkSelecionadas` atualmente (potencial bug)
- [ ] CA-02: Botão "✕" da bulk bar é o único reset explícito
- [ ] CA-03: Refresh de conversas mantém seleção (telefones existem mesmo fora da view atual)
- [ ] CA-04: GAP: deveria limpar ao trocar de filtro para evitar agir em conversas não visíveis

**Estado atual:** PARCIAL — seleção persiste indefinidamente; falta limpeza ao mudar filtro.
**Arquivos relevantes:** `static/admin/js/app.js:1603-1610` (não chama limparBulkSelecao)

---

### US-220: Bulk atribuir em conversas com aguardando_humano
**Como** sistema
**Quero** que bulk atribuir limpe `aguardando_humano` automaticamente
**Para** retirar conversas da fila vermelha ao serem distribuídas

**Critérios de Aceite:**
- [ ] CA-01: Backend seta `aguardando_humano = false` e `bot_ativo = false` ao atribuir em bulk
- [ ] CA-02: Métricas `aguardando` na sidebar atualizam após bulk
- [ ] CA-03: Cliente NÃO recebe mensagem de boas-vindas em bulk (diferente de `/assumir`)
- [ ] CA-04: Comportamento documentado: bulk atribuir é "silent" — atendente destino deve enviar saudação manual

**Estado atual:** IMPLEMENTADO (sem mensagem de boas-vindas)
**Arquivos relevantes:** `api/admin.py:806-808`

---

## 38. Presence (Online/Away/Offline) (Fase 2)

### US-221: Heartbeat de presença a cada 30s
**Como** atendente
**Quero** sinalizar que estou ativo continuamente
**Para** colegas verem minha presença correta

**Critérios de Aceite:**
- [ ] CA-01: `iniciarPresenceTracking()` chamado no bootstrap envia `enviarPresence('online')` imediatamente
- [ ] CA-02: `setInterval` envia heartbeat a cada 30s
- [ ] CA-03: Status enviado depende de `document.hidden` — `away` se hidden, senão `online`
- [ ] CA-04: POST `/admin/presence` body `{status}` atualiza dict in-memory `_presence_store`
- [ ] CA-05: Refresh do mapa via `setInterval(carregarPresence, 60000)` como backup do SSE

**Estado atual:** IMPLEMENTADO
**Arquivos relevantes:** `static/admin/js/app.js:1248-1273`, `static/admin/js/app.js:1935-1940`, `api/admin.py:681-740`

---

### US-222: Page Visibility API alterna online ↔ away
**Como** sistema
**Quero** detectar quando o atendente troca de aba e mudar status para `away`
**Para** sinalizar indisponibilidade imediata sem timeout

**Critérios de Aceite:**
- [ ] CA-01: Listener `visibilitychange` no document dispara `enviarPresence(document.hidden ? 'away' : 'online')` imediatamente
- [ ] CA-02: Mudança propagada via SSE `presence_changed` para outros atendentes
- [ ] CA-03: Trocar de janela do browser inteiro também dispara (mesmo evento)
- [ ] CA-04: Voltar à aba (`document.hidden=false`) restaura `online`

**Estado atual:** IMPLEMENTADO
**Arquivos relevantes:** `static/admin/js/app.js:1258-1260`

---

### US-223: sendBeacon em beforeunload marca offline
**Como** sistema
**Quero** detectar fechamento da aba e marcar offline
**Para** outros atendentes não enviarem transferências para ausente

**Critérios de Aceite:**
- [ ] CA-01: Listener `beforeunload` chama `navigator.sendBeacon('/admin/presence?token={t}', body)`
- [ ] CA-02: Body é JSON `{status: "offline"}` em Blob (sendBeacon não aceita string direta consistentemente)
- [ ] CA-03: sendBeacon não bloqueia o unload (assíncrono, ignora resposta)
- [ ] CA-04: Token passado via query param porque sendBeacon não suporta headers customizados

**Estado atual:** IMPLEMENTADO
**Arquivos relevantes:** `static/admin/js/app.js:1264-1273`

---

### US-224: Endpoint /presence aceita auth via header OU query param
**Como** sistema
**Quero** que `POST /presence` aceite token via header (default) ou query (fallback)
**Para** compatibilidade com sendBeacon

**Critérios de Aceite:**
- [ ] CA-01: Tenta header `Authorization: Bearer {t}` primeiro
- [ ] CA-02: Se ausente, busca `?token={t}` query param
- [ ] CA-03: Sem token em nenhum lugar: 401 "Token ausente"
- [ ] CA-04: Token inválido: HTTPException via `_decodificar`
- [ ] CA-05: `sub` ausente ou não-int: 401 com mensagem específica

**Estado atual:** IMPLEMENTADO
**Arquivos relevantes:** `api/admin.py:681-720`

---

### US-225: Validação de atendente ainda ativo no /presence
**Como** sistema
**Quero** rejeitar heartbeat de atendente desativado mesmo com JWT válido
**Para** não mostrar "online" para alguém demitido (até JWT expirar)

**Critérios de Aceite:**
- [ ] CA-01: Backend faz query: `Atendente.id == aid, Atendente.ativo == True`
- [ ] CA-02: Não encontrado → 401 "Atendente inativo ou inexistente"
- [ ] CA-03: Mesma paridade que `atendente_atual` (dependency padrão)
- [ ] CA-04: Frontend desse atendente vai cair no fluxo de 401 → redirect login

**Estado atual:** IMPLEMENTADO
**Arquivos relevantes:** `api/admin.py:723-728`

---

### US-226: Auto-marca offline após 90s sem heartbeat
**Como** sistema
**Quero** considerar offline atendentes sem heartbeat recente
**Para** UI exibir status correto mesmo se cliente desconecta sem beacon

**Critérios de Aceite:**
- [ ] CA-01: `_limpar_presence_stale()` é chamado no GET `/admin/presence`
- [ ] CA-02: Itera `_presence_store`: se `(now - last_seen).seconds > 90` e status != offline → muda para offline
- [ ] CA-03: Mudança publica SSE `presence_changed` para todos
- [ ] CA-04: `_PRESENCE_TIMEOUT_SECS = 90` é constante (3x heartbeat de 30s)
- [ ] CA-05: Trade-off: 30-90s de janela entre desconexão real e UI atualizar

**Estado atual:** IMPLEMENTADO
**Arquivos relevantes:** `api/admin.py:664-678`, `api/admin.py:743-753`

---

### US-227: GET /presence retorna mapa completo
**Como** atendente
**Quero** obter status atual de todos os atendentes
**Para** decidir transferências e ver disponibilidade

**Critérios de Aceite:**
- [ ] CA-01: GET `/admin/presence` retorna `{atendente_id_string: {status, last_seen}}`
- [ ] CA-02: Chaves são strings (não int) para compatibilidade JSON
- [ ] CA-03: Inclui apenas atendentes que sinalizaram presença pelo menos uma vez (in-memory)
- [ ] CA-04: Atendentes que nunca abriram o dashboard NÃO aparecem (default offline implícito no frontend)
- [ ] CA-05: Reset em restart do servidor (dict in-memory) — aceito como trade-off

**Estado atual:** IMPLEMENTADO
**Arquivos relevantes:** `api/admin.py:743-753`

---

### US-228: SSE presence_changed atualiza dropdown live
**Como** atendente
**Quero** ver dots de presença mudando em tempo real no dropdown de transferir
**Para** decisão informada sem refresh

**Critérios de Aceite:**
- [ ] CA-01: Backend publica evento sempre que status muda (não a cada heartbeat — apenas em transições)
- [ ] CA-02: Frontend atualiza `state.presence[id]` imediatamente
- [ ] CA-03: Se dropdown de transferir está aberto: `abrirPopoverTransferir()` re-renderiza
- [ ] CA-04: Dot de presença em outros lugares (futuro: sidebar) também atualizaria

**Estado atual:** IMPLEMENTADO
**Arquivos relevantes:** `api/admin.py:734-739`, `static/admin/js/app.js:1522-1528`

---

### US-229: JWT_SECRET ausente bloqueia presence
**Como** sistema
**Quero** rejeitar presence sem JWT_SECRET configurado
**Para** consistência com login (não aceitar tokens forjáveis)

**Critérios de Aceite:**
- [ ] CA-01: `POST /admin/presence` retorna 503 "JWT_SECRET não configurado" se `JWT_SECRET` é falsy
- [ ] CA-02: Mesma proteção que `/login` (defesa em profundidade)
- [ ] CA-03: Frontend logs warning silencioso (`console.warn('presence:', e)`) sem toast invasivo
- [ ] CA-04: Heartbeats falham silenciosamente — UI continua usável

**Estado atual:** IMPLEMENTADO
**Arquivos relevantes:** `api/admin.py:694-695`

---

### US-230: Mention em atendente away/offline persiste (sem som live)
**Como** sistema
**Quero** que menções a atendentes ausentes sejam persistidas mesmo sem entrega imediata via SSE
**Para** garantir delivery eventual quando voltarem

**Critérios de Aceite:**
- [ ] CA-01: Mention é gravada em `MentionNotificacao` independente de status de presença do destinatário
- [ ] CA-02: SSE `nova_mention` é publicado, mas se destinatário não está conectado, evento é perdido
- [ ] CA-03: Ao voltar online, `carregarMentions()` no bootstrap recupera todas as não-lidas
- [ ] CA-04: Badge mostra contagem retroativa
- [ ] CA-05: Comportamento aceito: mention de atendente offline NÃO dispara toast/som em outras abas até relogin

**Estado atual:** IMPLEMENTADO (delivery eventual via persistência)
**Arquivos relevantes:** `api/admin.py:1610-1652`, `static/admin/js/app.js:1930` (bootstrap mentions)

---

## 39. Saved Views (Fase 3)

### US-231: Listar views salvas do atendente
**Como** atendente
**Quero** ver minhas views salvas como chips na sidebar
**Para** aplicar filtros pré-configurados rapidamente

**Critérios de Aceite:**
- [ ] CA-01: GET `/admin/views` retorna views do `me.id` ordenadas por `ordem, criado_em`
- [ ] CA-02: `state.views` cacheado; `renderViews()` injeta chips em `#views-list`
- [ ] CA-03: `#views-row` fica `display: none` se não há views (esconde a row inteira)
- [ ] CA-04: Visível abaixo do filter row, com scroll horizontal se muitos
- [ ] CA-05: Cada chip exibe `nome` da view e botão `×` de exclusão

**Estado atual:** IMPLEMENTADO
**Arquivos relevantes:** `api/admin.py:504-525`, `static/admin/index.html:272-277`, `static/admin/js/app.js:1119-1145`

---

### US-232: Salvar filtros atuais como view nova
**Como** atendente
**Quero** clicar em "+ Salvar" para salvar a combinação de filtros atual
**Para** revisitar essa visão sem reconfigurar

**Critérios de Aceite:**
- [ ] CA-01: Botão `#btn-save-view` exibe `prompt('Nome da view (ex.: "VIPs ativos"):')`
- [ ] CA-02: POST `/admin/views` body `{nome, criterios: {filtro, statusFiltro}, ordem}`
- [ ] CA-03: `criterios` é JSON com `filtro` (todas/aguardando/meus/bot) e `statusFiltro` (open/pending/resolved/snoozed/todas)
- [ ] CA-04: Toast verde "View '{nome}' salva"
- [ ] CA-05: Re-renderiza row de views imediatamente

**Estado atual:** IMPLEMENTADO
**Arquivos relevantes:** `api/admin.py:528-550`, `static/admin/js/app.js:1171-1184`

---

### US-233: Aplicar view via clique no chip
**Como** atendente
**Quero** clicar num chip para aplicar a view e ver as conversas filtradas
**Para** alternar entre visões rapidamente

**Critérios de Aceite:**
- [ ] CA-01: Clique chama `aplicarView(viewId)` que atualiza `state.filtro` e `state.statusFiltro`
- [ ] CA-02: UI sincronizada: filter-tab ativo + status-filter destacado
- [ ] CA-03: `carregarConversas()` é disparado
- [ ] CA-04: Toast info: "View '{nome}' aplicada"
- [ ] CA-05: Sem feedback visual de qual view está "ativa" no momento (GAP UX)

**Estado atual:** IMPLEMENTADO (sem highlight de view ativa)
**Arquivos relevantes:** `static/admin/js/app.js:1147-1169`

---

### US-234: Excluir view via X
**Como** atendente
**Quero** clicar no X do chip para excluir uma view
**Para** limpar views obsoletas

**Critérios de Aceite:**
- [ ] CA-01: Botão `×` interno tem `onclick="event.stopPropagation(); deletarView(id)"` para evitar disparar aplicar
- [ ] CA-02: `confirm('Excluir view "{nome}"?')` antes do delete
- [ ] CA-03: DELETE `/admin/views/{id}` retorna 204
- [ ] CA-04: Frontend remove de `state.views` e re-renderiza
- [ ] CA-05: Toast verde "View excluída"

**Estado atual:** IMPLEMENTADO
**Arquivos relevantes:** `api/admin.py:584-598`, `static/admin/js/app.js:1186-1199`

---

### US-235: Nome único de view por atendente
**Como** sistema
**Quero** impedir duas views com mesmo nome para o mesmo atendente
**Para** evitar confusão na listagem

**Critérios de Aceite:**
- [ ] CA-01: POST verifica `FiltroSalvo.atendente_id == me.id, FiltroSalvo.nome == payload.nome`
- [ ] CA-02: Duplicidade → 409 "Já existe view com nome '{nome}'"
- [ ] CA-03: Frontend exibe toast "Nome já existe" no catch
- [ ] CA-04: PATCH também valida ao mudar nome (excluindo a própria view)

**Estado atual:** IMPLEMENTADO
**Arquivos relevantes:** `api/admin.py:535-540`, `api/admin.py:567-574`

---

### US-236: Edição de view (PATCH /admin/views/{id})
**Como** atendente
**Quero** poder editar nome, critérios ou ordem de uma view
**Para** ajustar sem ter que excluir e recriar

**Critérios de Aceite:**
- [ ] CA-01: PATCH aceita `{nome?, criterios?, ordem?}` (todos opcionais)
- [ ] CA-02: Backend só atualiza campos enviados (PATCH semântico)
- [ ] CA-03: Ownership: 404 se view não pertence ao `me.id`
- [ ] CA-04: Frontend NÃO expõe UI de edição (GAP — endpoint pronto, falta modal)
- [ ] CA-05: api.js tem `editarView` exposto mas sem uso no app.js

**Estado atual:** PARCIAL — backend e api wrapper prontos; UI não expõe.
**Arquivos relevantes:** `api/admin.py:553-581`, `static/admin/js/api.js:189-190`

---

### US-237: Views isoladas por atendente
**Como** sistema
**Quero** garantir que cada atendente vê apenas suas próprias views
**Para** privacidade de configurações pessoais

**Critérios de Aceite:**
- [ ] CA-01: Todas as queries filtram por `FiltroSalvo.atendente_id == me.id`
- [ ] CA-02: ON DELETE CASCADE de `Atendente` remove views órfãs ao desativar
- [ ] CA-03: Não há views globais ou compartilhadas (decisão consciente)
- [ ] CA-04: GAP futuro: views compartilháveis ao time

**Estado atual:** IMPLEMENTADO (sem sharing)
**Arquivos relevantes:** `db/models.py:192-204`, `api/admin.py:510-515`

---

### US-238: Critérios JSON serializados em Text
**Como** sistema
**Quero** persistir critérios como JSON texto (não JSON nativo)
**Para** compatibilidade com MySQL antigo

**Critérios de Aceite:**
- [ ] CA-01: Coluna `FiltroSalvo.criterios = Column(Text)` (não JSON type)
- [ ] CA-02: Backend serializa com `_json_lib.dumps(payload.criterios)` ao inserir
- [ ] CA-03: Deserializa com `_json_lib.loads(v.criterios)` ao ler
- [ ] CA-04: Critérios podem ser dict arbitrário (esquema livre — extensível para filtros futuros como labels, datas, etc.)

**Estado atual:** IMPLEMENTADO
**Arquivos relevantes:** `db/models.py:199-200`, `api/admin.py:544`, `api/admin.py:520`

---

## 40. Search Global de Mensagens (Fase 3)

### US-239: Toggle modo busca (contato vs mensagem)
**Como** atendente
**Quero** alternar entre busca por nome/telefone e busca por texto de mensagem
**Para** localizar conversas ou conteúdo específico

**Critérios de Aceite:**
- [ ] CA-01: Botão `#btn-search-mode` no input de busca alterna entre `@` (contato) e `🔍 msg`
- [ ] CA-02: Prefixo `?` no input ativa modo mensagem automaticamente
- [ ] CA-03: Clique no botão adiciona/remove o `?` do início do input e dispara `input` event
- [ ] CA-04: `state.searchMode = 'contato' | 'mensagem'`
- [ ] CA-05: Placeholder do input dica: "Buscar conversa… (?texto p/ mensagens)"

**Estado atual:** IMPLEMENTADO
**Arquivos relevantes:** `static/admin/index.html:253-254`, `static/admin/js/app.js:1614-1642`, `static/admin/js/app.js:1204`

---

### US-240: Debounce 300ms na busca de mensagens
**Como** sistema
**Quero** debounce o fetch para não bombardear o servidor a cada tecla
**Para** performance e UX fluida

**Critérios de Aceite:**
- [ ] CA-01: `_searchTimer` cancelado a cada novo `input` event
- [ ] CA-02: `setTimeout(executarSearchMensagem, 300)` agendado
- [ ] CA-03: Modo contato (sem `?`) NÃO faz debounce (filtra local imediato)
- [ ] CA-04: Query menor que 2 chars não dispara request (`q.length < 2` retorna vazio)

**Estado atual:** IMPLEMENTADO
**Arquivos relevantes:** `static/admin/js/app.js:1613-1629`, `static/admin/js/app.js:1207-1212`

---

### US-241: Backend LIKE em mensagem_cliente + resposta_bot
**Como** sistema
**Quero** buscar em ambos os campos de mensagem para cobrir todo o conteúdo
**Para** atendente encontrar tanto o que cliente disse quanto o que bot/atendente respondeu

**Critérios de Aceite:**
- [ ] CA-01: GET `/admin/search?q=texto&limit=50`
- [ ] CA-02: Backend faz `or_(HistoricoConversa.mensagem_cliente.like(termo), HistoricoConversa.resposta_bot.like(termo))`
- [ ] CA-03: `termo = f"%{q}%"` — busca parcial case-sensitive (MySQL default depende do collate, geralmente CI)
- [ ] CA-04: Ordenação por `criado_em DESC` (mais recentes primeiro)
- [ ] CA-05: Validação `q: min_length=2, max_length=100`

**Estado atual:** IMPLEMENTADO
**Arquivos relevantes:** `api/admin.py:605-629`

---

### US-242: Snippet centrado no match
**Como** atendente
**Quero** ver o trecho da mensagem em torno da palavra buscada
**Para** ter contexto sem abrir cada conversa

**Critérios de Aceite:**
- [ ] CA-01: Backend calcula `idx = texto.lower().find(q.lower())`
- [ ] CA-02: Janela de 40 chars antes e 40 depois do match
- [ ] CA-03: Reticências `…` no início se `inicio > 0`; no final se `fim < len(texto)`
- [ ] CA-04: Fallback: se match não encontrado (raro), retorna primeiros 100 chars
- [ ] CA-05: Frontend exibe snippet em `text-secondary` no card de resultado

**Estado atual:** IMPLEMENTADO
**Arquivos relevantes:** `api/admin.py:636-644`, `static/admin/js/app.js:1240`

---

### US-243: Agrupamento por telefone (1 resultado por conversa)
**Como** atendente
**Quero** ver no máximo 1 resultado por cliente
**Para** lista não ficar poluída com várias linhas do mesmo telefone

**Critérios de Aceite:**
- [ ] CA-01: Backend itera ordenado por `criado_em DESC` e mantém apenas a primeira ocorrência por telefone
- [ ] CA-02: `if m.telefone_usuario in resultados: continue` — skip duplicatas
- [ ] CA-03: Snippet renderizado é o do match mais recente daquela conversa
- [ ] CA-04: Resultado: até `limit` clientes distintos (pode ser menos se mesmo telefone aparecer várias vezes)

**Estado atual:** IMPLEMENTADO
**Arquivos relevantes:** `api/admin.py:631-654`

---

### US-244: Click em resultado abre conversa
**Como** atendente
**Quero** clicar num resultado da busca para abrir a conversa
**Para** ler o contexto completo

**Critérios de Aceite:**
- [ ] CA-01: Cada card de resultado tem `onclick="abrirConversa('{telefone}')"`
- [ ] CA-02: Abre normalmente (mesmo fluxo de clique em card normal)
- [ ] CA-03: Posicionamento NÃO scrolla até a mensagem encontrada (GAP — só abre conversa)
- [ ] CA-04: Atendente precisa rolar manualmente ou usar US-106 (busca dentro da thread, não implementada ainda)

**Estado atual:** PARCIAL — abre conversa mas não scrolla até match.
**Arquivos relevantes:** `static/admin/js/app.js:1234`

---

### US-245: Busca retorna conversas resolved/snoozed
**Como** atendente
**Quero** que a busca encontre mensagens em conversas resolvidas ou adiadas
**Para** recuperar contexto de atendimentos antigos

**Critérios de Aceite:**
- [ ] CA-01: Endpoint NÃO filtra por `status_conversa` — busca em todo o histórico
- [ ] CA-02: Resultados incluem conversas resolved que sumiram do dashboard padrão
- [ ] CA-03: Abrir resultado mostra a conversa mesmo que status seja resolved (header mostra status atual)
- [ ] CA-04: Comportamento documentado como feature (não bug)

**Estado atual:** IMPLEMENTADO
**Arquivos relevantes:** `api/admin.py:617-625` (sem filtro por status)

---

### US-246: Performance — MVP LIKE pode ficar lento em 50k+ mensagens
**Como** sistema
**Quero** monitorar performance da busca para migrar para FULLTEXT se necessário
**Para** manter UX rápida em produção

**Critérios de Aceite:**
- [ ] CA-01: Implementação atual usa LIKE simples (sem índice eficaz para `%texto%`)
- [ ] CA-02: Comment no código: "Se ficar lento (>5s em 50k+ mensagens), migrar para FULLTEXT"
- [ ] CA-03: Limite `limit=50` (max 200) protege contra payloads enormes
- [ ] CA-04: GAP futuro: migration adicionar `FULLTEXT INDEX(mensagem_cliente, resposta_bot)` e usar `MATCH AGAINST`

**Estado atual:** IMPLEMENTADO (MVP)
**Arquivos relevantes:** `api/admin.py:614-616`

---

### US-247: Resultados vazios — mensagem clara
**Como** atendente
**Quero** ver mensagem "Nenhum resultado" quando a busca não encontra nada
**Para** confirmar que a busca foi executada

**Critérios de Aceite:**
- [ ] CA-01: `state.searchResults.length === 0` exibe `<div class="px-4 py-8 text-xs italic text-center">Nenhum resultado</div>`
- [ ] CA-02: Texto em `var(--text-muted)` (cinza esmaecido)
- [ ] CA-03: Visível na mesma área de `#conv-list` (substitui a lista normal enquanto há query)
- [ ] CA-04: Limpar input volta a renderizar conversas normais

**Estado atual:** IMPLEMENTADO
**Arquivos relevantes:** `static/admin/js/app.js:1226-1228`

---

### US-248: Toggle de modo via tecla
**Como** atendente
**Quero** poder usar `?` no início para entrar no modo mensagem
**Para** atalho de teclado fluido

**Critérios de Aceite:**
- [ ] CA-01: Digitar `?` como primeiro char do input ativa modo mensagem automaticamente
- [ ] CA-02: Apagar o `?` volta ao modo contato
- [ ] CA-03: Botão `#btn-search-mode` mostra estado atual ("@" ou "🔍 msg")
- [ ] CA-04: Não há atalho global de teclado para alternar (mas `/` foca o input — US-261)

**Estado atual:** IMPLEMENTADO
**Arquivos relevantes:** `static/admin/js/app.js:1617-1629`

---

## 41. Atalhos de Teclado (Fase 3)

### US-249: j / k navegam conversas
**Como** atendente
**Quero** usar j (próxima) e k (anterior) para navegar a lista
**Para** workflow estilo Gmail/Vim

**Critérios de Aceite:**
- [ ] CA-01: Listener `keydown` no document captura `j` e `k`
- [ ] CA-02: `j`: encontra índice da conversa atual nos `.conv-card` e abre `cards[idx+1]` (clamp em max)
- [ ] CA-03: `k`: abre `cards[idx-1]` (clamp em 0)
- [ ] CA-04: Sem conversa selecionada: `j` abre a primeira; `k` não faz nada (ou abre a primeira também — verificar)
- [ ] CA-05: Navega apenas entre conversas visíveis na lista atual (respeitando filtros)

**Estado atual:** IMPLEMENTADO
**Arquivos relevantes:** `static/admin/js/app.js:1964-1982`

---

### US-250: Enter abre conversa (em foco de card)
**Como** atendente
**Quero** apertar Enter para abrir a conversa em foco
**Para** navegação completa por teclado

**Critérios de Aceite:**
- [ ] CA-01: Atualmente NÃO implementado — j/k apenas abre direto, sem foco intermediário
- [ ] CA-02: GAP: deveria haver navegação com foco visual antes de abrir
- [ ] CA-03: Como mitigação, j/k abre imediatamente (UX comparável)

**Estado atual:** NÃO IMPLEMENTADO (como atalho separado)
**Arquivos relevantes:** N/A — comportamento ausente

---

### US-251: c foca composer
**Como** atendente
**Quero** apertar c para focar o campo de mensagem
**Para** começar a digitar sem clicar

**Critérios de Aceite:**
- [ ] CA-01: Tecla `c` chama `document.getElementById('msg-input')?.focus()`
- [ ] CA-02: `preventDefault()` evita inserir "c" em algum input ativo
- [ ] CA-03: Funciona apenas se não está em input/textarea já (proteção via `dentroInput`)
- [ ] CA-04: Composer pode estar desabilitado (estado não-dono) — foco ainda é tentado mas pode ser silenciosamente ignorado

**Estado atual:** IMPLEMENTADO
**Arquivos relevantes:** `static/admin/js/app.js:1983-1987`

---

### US-252: e resolve conversa atual
**Como** atendente
**Quero** apertar e para marcar conversa como resolved
**Para** atalho de finalização rápida

**Critérios de Aceite:**
- [ ] CA-01: Tecla `e` chama `alterarStatus('resolved')` se `state.conversaAtual` definido
- [ ] CA-02: Confirmação via `confirm()` ainda é exibida (US-166)
- [ ] CA-03: Sem conversa aberta: tecla é ignorada silenciosamente
- [ ] CA-04: `preventDefault()` evita inserir "e" em campos
- [ ] CA-05: Bloqueado se foco em input/textarea

**Estado atual:** IMPLEMENTADO
**Arquivos relevantes:** `static/admin/js/app.js:1988-1993`

---

### US-253: s adia conversa atual
**Como** atendente
**Quero** apertar s para adiar (snooze) com prompt de horas
**Para** atalho de despriorização rápida

**Critérios de Aceite:**
- [ ] CA-01: Tecla `s` chama `alterarStatus('snoozed')` se `state.conversaAtual` definido
- [ ] CA-02: Prompt de horas é exibido normalmente
- [ ] CA-03: Sem conversa aberta: ignorado
- [ ] CA-04: Bloqueado se foco em input/textarea

**Estado atual:** IMPLEMENTADO
**Arquivos relevantes:** `static/admin/js/app.js:1994-1999`

---

### US-254: n abre nova nota interna
**Como** atendente
**Quero** apertar n para focar na textarea de nota
**Para** registrar observação rápida sem clicar

**Critérios de Aceite:**
- [ ] CA-01: Tecla `n` abre info panel (`abrirInfoPanel()`) se estava fechado
- [ ] CA-02: Após 100ms (delay para evitar conflito com animação), foca `#note-input`
- [ ] CA-03: Sem conversa aberta: ignorado
- [ ] CA-04: Bloqueado se foco em input/textarea

**Estado atual:** IMPLEMENTADO
**Arquivos relevantes:** `static/admin/js/app.js:2005-2011`

---

### US-255: i alterna info panel
**Como** atendente
**Quero** apertar i para abrir/fechar o painel de informações
**Para** alternância rápida sem mouse

**Critérios de Aceite:**
- [ ] CA-01: Tecla `i` chama `abrirInfoPanel()` ou `fecharInfoPanel()` baseado em `state.infoAberto`
- [ ] CA-02: Funciona mesmo sem conversa aberta (mas painel ficará vazio)
- [ ] CA-03: `preventDefault()` evita inserir "i" em campos
- [ ] CA-04: Bloqueado se foco em input/textarea

**Estado atual:** IMPLEMENTADO
**Arquivos relevantes:** `static/admin/js/app.js:2012-2017`

---

### US-256: / foca busca
**Como** atendente
**Quero** apertar `/` para focar imediatamente o input de busca
**Para** ir direto pesquisar como no Slack/GitHub

**Critérios de Aceite:**
- [ ] CA-01: Tecla `/` chama `document.getElementById('search-input')?.focus()`
- [ ] CA-02: `preventDefault()` evita inserir "/" no foco anterior
- [ ] CA-03: Bloqueado se já está em input/textarea
- [ ] CA-04: Foco no search-input não é bloqueio (atende ao propósito)

**Estado atual:** IMPLEMENTADO
**Arquivos relevantes:** `static/admin/js/app.js:2000-2004`

---

### US-257: ? abre modal de atalhos
**Como** atendente
**Quero** ver lista de atalhos disponíveis
**Para** aprender e relembrar shortcuts

**Critérios de Aceite:**
- [ ] CA-01: Tecla `?` (shift+/) abre modal `#modal-shortcuts`
- [ ] CA-02: Modal lista todos os atalhos com `<kbd>` styled visualmente
- [ ] CA-03: Esc ou clique fora fecha
- [ ] CA-04: Botão X no header também fecha
- [ ] CA-05: Atalhos exibidos: j/k, c, e, s, /, n, i, Esc

**Estado atual:** IMPLEMENTADO
**Arquivos relevantes:** `static/admin/index.html:218-237`, `static/admin/js/app.js:2018-2022`, `static/admin/js/app.js:2027-2034`

---

### US-258: Esc fecha popovers e modais
**Como** atendente
**Quero** apertar Esc para fechar qualquer popover/modal aberto
**Para** sair de contextos rápido sem usar mouse

**Critérios de Aceite:**
- [ ] CA-01: Esc fecha: modal-shortcuts, canned-popover, label-picker, status-popover, transferir-popover, mentions-popover, mention-autocomplete
- [ ] CA-02: Funciona mesmo dentro de inputs/textareas (não bloqueado por `dentroInput`)
- [ ] CA-03: `return` após Esc impede que processe outros atalhos
- [ ] CA-04: Não fecha info panel (decisão consciente — info é estado mais permanente)

**Estado atual:** IMPLEMENTADO
**Arquivos relevantes:** `static/admin/js/app.js:1950-1960`

---

### US-259: Detecção de foco em input/textarea evita conflito
**Como** sistema
**Quero** não disparar atalhos quando atendente está digitando
**Para** evitar comportamento errático (ex.: `e` apertado dentro de mensagem disparar resolved)

**Critérios de Aceite:**
- [ ] CA-01: `tag = e.target.tagName.toLowerCase()` capturado
- [ ] CA-02: `dentroInput = tag === 'input' || tag === 'textarea' || e.target.isContentEditable`
- [ ] CA-03: Se `dentroInput && key !== 'Escape'`: `return` (ignora atalho)
- [ ] CA-04: Esc é exceção — sempre processa
- [ ] CA-05: Funciona corretamente em textarea de mensagem, busca, notas e modais

**Estado atual:** IMPLEMENTADO
**Arquivos relevantes:** `static/admin/js/app.js:1947-1961`

---

### US-260: Atalhos modal de ajuda persistente
**Como** atendente novato
**Quero** acessar modal de atalhos a qualquer momento
**Para** aprender progressivamente

**Critérios de Aceite:**
- [ ] CA-01: Modal sempre disponível via `?`
- [ ] CA-02: Estilo: backdrop preto 70%, card central com lista
- [ ] CA-03: Atalho `?` documentado dentro do próprio modal (autorreferência)
- [ ] CA-04: GAP: não há botão visível para abrir o modal (apenas via teclado) — usuários sem teclado físico podem não descobrir

**Estado atual:** IMPLEMENTADO (sem botão visual)
**Arquivos relevantes:** `static/admin/index.html:218-237`

---

### US-261: Foco no search input com / não dispara modo mensagem
**Como** sistema
**Quero** que `/` foque o input mas não digite `?` automaticamente
**Para** comportamento previsível

**Critérios de Aceite:**
- [ ] CA-01: Tecla `/` apenas chama `.focus()` — não insere caractere
- [ ] CA-02: Atendente precisa digitar `?` explicitamente para entrar no modo mensagem
- [ ] CA-03: Após foco, atendente pode digitar normalmente (modo contato por default)
- [ ] CA-04: Combinação típica: `/` + `?` + termo abre modo mensagem com busca

**Estado atual:** IMPLEMENTADO
**Arquivos relevantes:** `static/admin/js/app.js:2000-2004`

---

## 42. Tema Claro/Escuro (Fase 3)

### US-262: Aba "Aparência" em settings com toggle
**Como** atendente
**Quero** ter uma área dedicada para alternar tema
**Para** ajustar preferência visual conforme ambiente

**Critérios de Aceite:**
- [ ] CA-01: Tab "Aparência" em `settings.html`
- [ ] CA-02: Dois botões grandes: "🌙 Escuro" e "☀️ Claro"
- [ ] CA-03: Botão ativo recebe `border-color: var(--accent)` e `box-shadow` accent
- [ ] CA-04: Clique chama `trocarTema('dark'|'light')`
- [ ] CA-05: Texto explicativo: "Escolha entre tema escuro (padrão) e claro. A preferência é salva localmente neste navegador."

**Estado atual:** IMPLEMENTADO
**Arquivos relevantes:** `static/admin/settings.html:163-176`, `static/admin/settings.html:435-448`

---

### US-263: CSS custom properties para tokens de tema
**Como** sistema
**Quero** usar `var(--bg-base)`, `var(--text-primary)` etc. em vez de cores hardcoded
**Para** tema funcionar sem reescrever componentes

**Critérios de Aceite:**
- [ ] CA-01: `:root, :root[data-theme="dark"]` define 16+ tokens (bg-base, bg-surface, bg-card, accent, success, warning, danger, text-primary, text-secondary, text-muted, border, bg-bubble-*)
- [ ] CA-02: `:root[data-theme="light"]` redefine os mesmos tokens com valores claros
- [ ] CA-03: Toda CSS no `index.html` e `settings.html` usa `var(--token)` em vez de hex direto
- [ ] CA-04: Estilos inline também usam `style="background: var(--bg-card)"` (não hex)
- [ ] CA-05: Mudança de `data-theme` no `<html>` propaga para todos os elementos via cascata

**Estado atual:** IMPLEMENTADO
**Arquivos relevantes:** `static/admin/index.html:17-57`, `static/admin/settings.html:10-37`

---

### US-264: Persistência em localStorage
**Como** atendente
**Quero** que minha escolha de tema persista entre sessões
**Para** não ter que reconfigurar a cada login

**Critérios de Aceite:**
- [ ] CA-01: `trocarTema(t)` chama `localStorage.setItem('theme', t)`
- [ ] CA-02: Aplica `document.documentElement.setAttribute('data-theme', t)`
- [ ] CA-03: Re-renderiza estado ativo dos botões em `aplicarThemeSelecionado()`
- [ ] CA-04: Persistência sobrevive a logout/login (não é apagado em `localStorage.clear()` do logout — mas verificar)
- [ ] CA-05: GAP: `localStorage.clear()` no logout (api.js _logout) APAGA preferência de tema — atendente perde configuração

**Estado atual:** PARCIAL — persiste entre refreshes, mas é apagado em logout (`localStorage.clear()`).
**Arquivos relevantes:** `static/admin/settings.html:444-448`, `static/admin/js/api.js:10`

---

### US-265: Aplicação antes do render (sem flash)
**Como** atendente
**Quero** que o tema correto apareça imediatamente ao carregar a página
**Para** não ver flash de tema errado (FOUC)

**Critérios de Aceite:**
- [ ] CA-01: `<script>` inline no `<head>` (antes do `<body>`) lê `localStorage.theme` e aplica
- [ ] CA-02: Default: `prefers-color-scheme: light` query (respeita preferência do OS)
- [ ] CA-03: Fallback: `dark` (default da aplicação)
- [ ] CA-04: Mesmo script em `index.html` e `settings.html` para consistência
- [ ] CA-05: Variáveis CSS já definidas no `<head>` antes do `<body>` aparecer

**Estado atual:** IMPLEMENTADO
**Arquivos relevantes:** `static/admin/index.html:9-15`, `static/admin/settings.html:40-46`

---

### US-266: login.html sem tema (cores hardcoded — limitação aceita)
**Como** sistema
**Quero** que a tela de login mantenha visual constante
**Para** branding consistente independente de configuração do usuário

**Critérios de Aceite:**
- [ ] CA-01: `login.html` usa cores hex hardcoded (`#0f1117`, `#1a1d27`, `#6366f1` etc.) — sem custom properties
- [ ] CA-02: Sem script de aplicação de tema
- [ ] CA-03: Decisão consciente: usuário ainda não logado não tem preferência conhecida (e o flash seria mais perceptível na tela de login)
- [ ] CA-04: Trade-off documentado — pode ser revisado se demanda surgir

**Estado atual:** IMPLEMENTADO (limitação aceita)
**Arquivos relevantes:** `static/admin/login.html:11-47`

---

### US-267: Detecção inicial via prefers-color-scheme
**Como** atendente
**Quero** que tema inicial respeite minha configuração do sistema operacional
**Para** UX coerente sem precisar configurar manualmente

**Critérios de Aceite:**
- [ ] CA-01: Primeira visita (sem `localStorage.theme`): `window.matchMedia('(prefers-color-scheme: light)').matches ? 'light' : 'dark'`
- [ ] CA-02: Aplica como default mas não persiste em localStorage (atendente precisa escolher explicitamente)
- [ ] CA-03: Próxima visita usa o salvo (independente do OS)
- [ ] CA-04: GAP: não há listener para mudanças dinâmicas do OS (atendente que muda tema do OS não vê mudança em tempo real)

**Estado atual:** IMPLEMENTADO (sem listener dinâmico)
**Arquivos relevantes:** `static/admin/index.html:12`, `static/admin/settings.html:43`

---

### US-268: Bolhas WhatsApp-style adaptadas em tema claro
**Como** atendente
**Quero** que as cores das bolhas (cliente/bot/atendente) mudem em tema claro
**Para** legibilidade não sofrer

**Critérios de Aceite:**
- [ ] CA-01: Tema claro define `--bg-bubble-client: #e2e8f0`, `--bg-bubble-bot: #d1fae5`, `--bg-bubble-human: #dbeafe`
- [ ] CA-02: Texto das bolhas usa `var(--text-primary)` (que vira `#0f172a` em claro)
- [ ] CA-03: Contraste mantido legível em ambos os temas
- [ ] CA-04: Bolha-falha mantém vermelho semitransparente fixo (alerta deve ser visível em ambos)

**Estado atual:** IMPLEMENTADO
**Arquivos relevantes:** `static/admin/index.html:45-47`, `static/admin/index.html:88-117`

---

### US-269: Toast colors visíveis em ambos os temas
**Como** atendente
**Quero** ver toasts com cores adequadas independente do tema
**Para** não ter notificações ilegíveis

**Critérios de Aceite:**
- [ ] CA-01: Toasts usam cores fixas (`#2481cc`, `#10b981`, etc.) — não custom properties
- [ ] CA-02: Texto branco em todos os tipos garante contraste
- [ ] CA-03: Funciona em ambos os temas (branco sobre cor sempre legível)
- [ ] CA-04: GAP: em tema claro, toasts azuis/verdes podem destoar do estilo geral mais sutil — refinamento futuro

**Estado atual:** IMPLEMENTADO (com refinamento pendente)
**Arquivos relevantes:** `static/admin/js/app.js:127-133`

---

### US-270: Scrollbar customizado adaptativo
**Como** atendente
**Quero** que scrollbars mantenham estilo discreto em ambos os temas
**Para** UI coerente

**Critérios de Aceite:**
- [ ] CA-01: `.custom-scrollbar::-webkit-scrollbar-thumb { background: var(--border); }` — adapta com tema
- [ ] CA-02: Hover `background: #3a4050` é fixo (gap menor de visibilidade em tema claro)
- [ ] CA-03: Track transparente em ambos os temas
- [ ] CA-04: Width fixa em 5px

**Estado atual:** IMPLEMENTADO
**Arquivos relevantes:** `static/admin/index.html:62-65`

---

## 43. Integrações com Features Pré-existentes

### US-271: Devolver ao bot deveria setar status para open?
**Como** sistema
**Quero** decidir comportamento explícito quando atendente devolve uma conversa resolved
**Para** consistência entre status e ciclo de vida do bot

**Critérios de Aceite:**
- [ ] CA-01: Atual: POST `/admin/devolver` NÃO altera `status_conversa` — preserva o que estava (open/pending/resolved/snoozed)
- [ ] CA-02: Caso 1: conversa estava `resolved` e devolvida → continua `resolved` (some do dashboard padrão, mas bot pode responder)
- [ ] CA-03: Caso 2: conversa estava `pending` (esperando supervisor) e devolvida → continua `pending`
- [ ] CA-04: Decisão recomendada: devolver deveria forçar status `open` para retornar à fila normal
- [ ] CA-05: GAP UX: atendente que devolve conversa resolved fica confuso pois ela "some"

**Estado atual:** PARCIAL — comportamento atual preserva status, gerando confusão UX
**Arquivos relevantes:** `api/admin.py:956-1046` (devolver não toca status_conversa)

---

### US-272: Bulk atribuir em conversas aguardando_humano
**Como** sistema
**Quero** que bulk atribuir limpe `aguardando_humano` corretamente
**Para** retirar da fila vermelha

**Critérios de Aceite:**
- [ ] CA-01: Backend bulk atribuir já faz `user.aguardando_humano = false` e `user.bot_ativo = false`
- [ ] CA-02: Conversa muda de estado visual: ponto vermelho pulsante → ponto azul/cinza
- [ ] CA-03: Métrica de "aguardando" decrementa
- [ ] CA-04: Bot fica desativado (atendente destino precisa enviar mensagem)
- [ ] CA-05: Diferença vs `/assumir`: bulk não envia mensagem de boas-vindas automática

**Estado atual:** IMPLEMENTADO (comportamento documentado)
**Arquivos relevantes:** `api/admin.py:805-808`

---

### US-273: Mention em atendente offline persiste para depois
**Como** sistema
**Quero** garantir delivery eventual de mentions a atendentes ausentes
**Para** colaboração funcionar mesmo com diferentes horários

**Critérios de Aceite:**
- [ ] CA-01: Tabela `mention_notificacoes` persiste sem dependência de presença
- [ ] CA-02: SSE `nova_mention` é "fire and forget" — perdido se destino offline
- [ ] CA-03: GET `/admin/mentions/inbox` retorna acumulado ao logar
- [ ] CA-04: Badge contador atualiza no bootstrap (`carregarMentions()` em `DOMContentLoaded`)
- [ ] CA-05: Funcionalidade completa documentada em US-207 e US-230

**Estado atual:** IMPLEMENTADO
**Arquivos relevantes:** `static/admin/js/app.js:1930-1938`

---

### US-274: Search retorna conversas resolved/snoozed
**Como** atendente
**Quero** que busca encontre conteúdo em conversas que sumiram do dashboard
**Para** recuperar contexto antigo

**Critérios de Aceite:**
- [ ] CA-01: GET `/admin/search` não aplica filtro de `status_conversa`
- [ ] CA-02: Resultados podem incluir conversas que estão `resolved` ou `snoozed`
- [ ] CA-03: Ao abrir resultado, header mostra status atual (badge "Resolvida"/"Adiada")
- [ ] CA-04: Atendente pode reabrir mudando status para `open`
- [ ] CA-05: Comportamento documentado em US-245

**Estado atual:** IMPLEMENTADO
**Arquivos relevantes:** `api/admin.py:605-655` (sem filtro de status)

---

### US-275: Tema claro afeta bolhas WhatsApp-style
**Como** atendente
**Quero** que bolhas em tema claro não pareçam "fora de lugar"
**Para** experiência visual coerente

**Critérios de Aceite:**
- [ ] CA-01: `--bg-bubble-client` em tema claro: `#e2e8f0` (cinza claro WhatsApp-like)
- [ ] CA-02: `--bg-bubble-bot` em tema claro: `#d1fae5` (verde claro pastel)
- [ ] CA-03: `--bg-bubble-human` em tema claro: `#dbeafe` (azul claro pastel)
- [ ] CA-04: Texto `var(--text-primary)` adapta automaticamente
- [ ] CA-05: Bolha-falha mantém fundo vermelho semitransparente em ambos (alerta consistente)
- [ ] CA-06: Documentado em US-268

**Estado atual:** IMPLEMENTADO
**Arquivos relevantes:** `static/admin/index.html:39-57`

---

### US-276: Labels visíveis em tema claro com contraste correto
**Como** atendente
**Quero** que chips coloridos de labels mantenham legibilidade em ambos os temas
**Para** identificação visual não sofrer

**Critérios de Aceite:**
- [ ] CA-01: Chips usam `background: {cor}20` (12.5% alpha) — fundo translúcido sobre o tema
- [ ] CA-02: Texto usa a cor original da label (`color: {cor}`)
- [ ] CA-03: Em tema claro: fundo translúcido fica muito claro, texto saturado garante leitura
- [ ] CA-04: Em tema escuro: fundo translúcido escurece, texto vibrante mantém visibilidade
- [ ] CA-05: GAP: cores muito claras (ex.: amarelo `#f59e0b`) podem ter contraste fraco em tema claro

**Estado atual:** IMPLEMENTADO (com possíveis ajustes de contraste futuros)
**Arquivos relevantes:** `static/admin/js/app.js:179-186`

---

### US-277: Saved view com filtro de label (extensibilidade)
**Como** atendente
**Quero** salvar uma view que filtre por uma label específica
**Para** monitorar grupo de conversas (ex.: todas marcadas como VIP)

**Critérios de Aceite:**
- [ ] CA-01: `criterios` é dict arbitrário (esquema livre — extensível)
- [ ] CA-02: Frontend atual só salva `{filtro, statusFiltro}` — não há UI para incluir labels
- [ ] CA-03: Backend não filtra por labels no GET `/admin/conversas` — feature pendente
- [ ] CA-04: GAP: precisa extensão tanto frontend (UI de filtro por label) quanto backend (suporte no endpoint de listagem)

**Estado atual:** NÃO IMPLEMENTADO
**Arquivos relevantes:** N/A

---

### US-278: Atalho de teclado dentro de modal de canned response
**Como** atendente
**Quero** que Tab/Enter funcione em modal de criar canned response
**Para** fluxo de teclado completo em settings

**Critérios de Aceite:**
- [ ] CA-01: Modal `#modal-canned` aceita Tab para navegar entre campos
- [ ] CA-02: Enter no último campo submete o form
- [ ] CA-03: Esc fecha o modal (via listener global de Esc — mas em settings.html não há esse listener)
- [ ] CA-04: GAP: settings.html não tem atalho Esc global — apenas botão X fecha

**Estado atual:** PARCIAL — Tab/Enter funcionam (browser default); Esc não implementado em settings
**Arquivos relevantes:** `static/admin/settings.html:249-283`, `static/admin/settings.html:628-633`

---

### US-279: Status pending não usado pelo bot automaticamente
**Como** sistema
**Quero** documentar que `pending` é um status manual (não setado por nenhum fluxo automático)
**Para** atendentes saberem o significado

**Critérios de Aceite:**
- [ ] CA-01: Bot NÃO seta `status_conversa = "pending"` em nenhum momento (verificado em webhook.py)
- [ ] CA-02: `pending` é puramente manual: atendente usa via dropdown do header
- [ ] CA-03: Semântica sugerida: "aguardando ação de terceiro" (ex.: confirmação do gerente)
- [ ] CA-04: GAP UX: não há tooltip explicativo de cada status no dropdown
- [ ] CA-05: Documentação inline ou guia recomendada

**Estado atual:** IMPLEMENTADO (sem documentação inline)
**Arquivos relevantes:** `api/admin.py:1273-1330`

---

### US-280: Tema claro em mobile drawer
**Como** atendente (mobile)
**Quero** que info panel em drawer mobile mantenha tema correto
**Para** consistência visual em mobile

**Critérios de Aceite:**
- [ ] CA-01: `#info-panel` usa custom properties — adapta automaticamente
- [ ] CA-02: Backdrop preto 70% funciona em ambos os temas (overlay genérico)
- [ ] CA-03: Drawer slide-in animation independente do tema
- [ ] CA-04: GAP: não há media queries específicas para mobile que forcem tema (uniformidade ok)

**Estado atual:** IMPLEMENTADO
**Arquivos relevantes:** N/A — propagação automática via CSS vars

---

## Gaps Identificados (Fase 1-3)

**GAP-09: Seed inicial de labels ausente (US-161)**
Modelo `Label` e endpoints completos, mas não há SQL/script de seed para `resolvido, follow_up, vip, reclamacao, fidelidade`. Instalação nova começa com catálogo vazio — UX ruim para onboarding.

**GAP-10: Backfill de `status_conversa` para usuários antigos (US-175)**
Coluna tem `default="open"` mas usuários pré-existentes têm `NULL`. Filtro SQL `Usuario.status_conversa == "open"` NÃO captura `NULL`. Migration recomendada: `UPDATE usuarios SET status_conversa='open' WHERE status_conversa IS NULL`.

**GAP-11: Bulk actions UI incompleta (US-214, US-215, US-218)**
Backend suporta `atribuir`, `label_add`, `label_remove` em bulk, mas a bulk bar do frontend só expõe `Resolver` e `Adiar`. Frontend tampouco consome o evento SSE `bulk_aplicado` — outros atendentes só veem mudança no próximo refresh periódico (60s).

**GAP-12: Edição de view sem UI (US-236)**
PATCH `/admin/views/{id}` e `api.editarView` existem, mas não há modal/UI para editar nome/critérios. Atendente precisa excluir + recriar.

**GAP-13: Devolver ao bot não normaliza status_conversa (US-271)**
Devolver uma conversa `resolved` mantém `status_conversa = "resolved"`. Atendente devolve e a conversa "some" do dashboard. Recomendação: forçar `status_conversa = "open"` em devolver.

**GAP-14: localStorage.clear() no logout apaga preferência de tema (US-264)**
`_logout()` em api.js faz `localStorage.clear()`, removendo `theme`, `atendente_mute`, `notif_history` (futuro), etc. Próximo login volta ao default. Recomendação: salvar preferências em chaves específicas e preservar no logout.

**GAP-15: Edição de nota não re-processa @mentions (US-208)**
Editar nota via PATCH não chama `_processar_mentions(db, nota, autor)`. Adicionar `@colega` em edição NÃO gera notificação. Corrigir em `editar_nota` ou aceitar como limitação documentada.

**GAP-16: Search não scrolla até a mensagem encontrada (US-244)**
Click em resultado de busca abre conversa mas não navega até a mensagem específica (sem destaque visual). Ideal: adicionar `?msg_id={id}` em `getConversa` e scroll + highlight.

**GAP-17: Sem busca de texto dentro da conversa ativa (US-106 da v1.1)**
US-106 já documentava como gap futuro. Persiste — apenas search global no servidor existe, sem find local na thread.

**GAP-18: Saved views não suportam filtro por label (US-277)**
`criterios` é dict livre mas frontend só salva `{filtro, statusFiltro}` e backend não tem suporte a filtrar por label_id em `/admin/conversas`.

**GAP-19: Sem tooltip explicativo dos status (US-279)**
Atendente não sabe quando usar `pending` vs `open`. Hover/tooltip ou onboarding inline recomendado.

**GAP-20: Atalho de teclado em settings.html ausente**
`Esc` para fechar modais funciona em `index.html` mas não em `settings.html`. Apenas botão X fecha.

**GAP-21: Bulk não limpa seleção ao trocar filtro (US-219)**
Selecionar 5 em "Todas" e trocar para "Aguardando" mantém seleção, mesmo que cards não estejam visíveis. Pode agir em conversas ocultas.

**GAP-22: Sem highlight visual da view ativa (US-233)**
Aplicar uma view não destaca qual chip está em uso. Atendente perde rastreio.

**GAP-23: prefers-color-scheme sem listener dinâmico (US-267)**
Mudar tema do OS não reflete no painel em tempo real. Apenas no primeiro carregamento sem `localStorage.theme`.

---

*Expansão Fase 1-3 gerada em 2026-05-21. Novas stories US-150 a US-280 (131 stories adicionais) cobrindo 12 features Chatwoot-style implementadas em `redesign/admin-interface`: Labels múltiplas (14 stories), Status de conversa (12), Canned responses dinâmicas (13), Atribuição entre atendentes (9), @mentions (12), Bulk actions (11), Presence (10), Saved Views (8), Search global (10), Atalhos de teclado (13), Tema claro/escuro (9) e Integrações com features pré-existentes (10).*

*Total de user stories no documento (após anexar): 280.*
