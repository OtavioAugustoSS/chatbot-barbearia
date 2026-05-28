# Análise da Referência Visual — Bolshoi Dashboard Redesign

**Referência:** `docs/ux/redesign/references/inbox-reference.png` (Paperlayer/Drift-style multi-channel inbox)
**Logo:** `docs/ux/redesign/references/logo-bolshoi.png` (tesouras cruzadas + Western serif "BOLSHOI" + "BARBEARIA" spaced)

---

## Layout observado (4 colunas, desktop ~1440px)

### Coluna 1 — Sidebar expandida (240px, NÃO mais 72px ícones)
- **Top:** Logo/brand "Paperlayer" + botão "+" (nova conversa)
- **Busca:** input full-width com ícone lupa
- **Seção "Conversations":** itens com ícone + label + count badge à direita
  - All Conversations · 11
  - Mentions · 3
  - Unattended · 2
- **Seção "Folders":** Priority Conversations, Leads Inbox
- **Seção "Teams":** Sales, Support L1 (avatares pequenos coloridos)
- **Seção "Channels":** canais com ícones de marca **coloridos** (Gmail vermelho, Drift Web, Facebook azul, Line verde)
- **Seção "Labels":** chips com dot colorido (ex: "device-setup" com dot vermelho)
- Item ativo: bg surface-container + barra accent à esquerda

### Coluna 2 — Lista de conversas (~300px)
- **Header sticky:** "Conversations" + ícones de filtro à direita
- **Sub-tabs:** Mine · Unassigned · All (todos com count)
- **Cards:**
  - Avatar circular 40px à esquerda
  - Nome (semibold 14px) + canal source linha 2 ("Drift Web", "Email", "Facebook")
  - Preview da última msg (1 linha truncada, secondary text)
  - Timestamp Geist Mono à direita (ex: "Jan 10")
  - **Tag chip vermelha pequena** topo direito quando aplicável ("device-setup")
- Card ativo: bg surface-container + border-left accent 3px

### Coluna 3 — Chat principal (flex 1, ~500px+)
- **Header:** avatar + "Klaus Crawley · Paperlayer Web · Close details" + badge "Resolve" à direita (pill button accent)
- **Sub-tabs:** Messages · Customer Dashboard
- **Área de mensagens:**
  - Bolha incoming: top-left squared, fundo cinza neutro (`surface-container-low`), nome em azul claro acima da msg, ts cinza claro
  - Bolha outgoing: top-right squared, accent solid azul não-saturado (`#4E7AE7`-ish), texto branco
  - **Bolha de sistema:** pill centralizada cinza médio ("Mathew M self-assigned this conversation", "set the priority to high", "added participant")
- **Composer:**
  - **Sub-tabs:** Reply · Private Note (MAJOR feature ausente atualmente)
  - Textarea com placeholder "Shift + enter for new line. Start with '/' to select a Canned Response."
  - **Toolbar bottom:**
    - LEFT: 6 ícones (attach, emoji, gif, link, etc.)
    - CENTER: pill "AI Assist" com ícone sparkle (NEW feature)
    - RIGHT: botão "Send ↵" accent solid

### Coluna 4 — Info panel (280px, abre sob demanda via "Close details")
- **Tabs:** Contact · Copilot
- **Header do contato:** avatar grande + nome + ícone edit + role abaixo ("Founder, Drift Burner")
- **Linhas de contato com ícone:**
  - Email: kcrawley@driftburner.com
  - Telefone: +14185552398
  - Empresa: Drift Burner
  - Localização: San Francisco, United States + 🇺🇸
- **Ícones sociais em linha** (LinkedIn, X, etc.)
- **Action icons row** (compose, attach, etc.)
- **Accordions colapsados:**
  - Conversation Actions
  - Conversation participants
  - Macros
  - Contact Attributes
  - Conversation Information
  - Previous Conversations

---

## Paleta de cores (extraída da referência)

| Token | Valor estimado | Uso |
|---|---|---|
| `--bg-base` | `#15161A` | Background app (deep cool charcoal, NÃO preto puro, sub-tom azul) |
| `--surface-1` | `#1C1D22` | Sidebar bg, conv-list bg |
| `--surface-2` | `#25272C` | Cards ativos, bolhas incoming |
| `--surface-3` | `#2D2F35` | Hover, popovers |
| `--border-subtle` | `#2A2C32` | Separadores entre colunas (~1px) |
| `--text-primary` | `#E5E7EB` | Headings, msgs |
| `--text-secondary` | `#9CA3AF` | Subtítulos, previews |
| `--text-muted` | `#6B7280` | Timestamps, counts, helper |
| `--accent` | `#4E7AE7` | Bolha operador, send btn, active item (menos saturado que o atual #2481CC) |
| `--accent-subtle` | `rgba(78,122,231,0.10)` | bg ativo, hover do CTA |
| `--accent-strong` | `#3B6BDF` | Hover de CTA primary |
| `--danger-tag` | `#EF4444` | Tag chips vermelhas, alertas |
| `--success` | `#10B981` | Online dots, success state |
| `--warning` | `#F59E0B` | Aguardando |

**Características da paleta:**
- Cool-toned (azul-acinzentado) — sofisticada, não competitiva com conteúdo
- Brand colors de canais preservados (Gmail/Facebook/etc. com suas cores oficiais)
- Accent NÃO é Bolshoi azul vibrante atual — é mais **balanceado**, menos saturado

---

## Tipografia (observada)

- **Body/UI:** Inter (geometric sans, peso 400-500, kerning aberto)
- **Headings:** Inter 600
- **Counts/timestamps/labels técnicos:** Inter tabular-nums (ou Geist Mono opcional)

**Decisão:** trocar Plus Jakarta Sans → **Inter** (mais aderente à referência). Manter Geist Mono apenas em telefones / IDs longos onde mono ainda agrega.

---

## Iconografia

- **Lucide-style SVG** monocromático throughout
- Stroke 1.5-2px
- 16-18px maioria, 20px em headers
- **EXCEÇÃO:** ícones de canais (Gmail, FB, etc.) coloridos oficiais
- Zero emoji estrutural

---

## Adaptações pro contexto Bolshoi

### Sidebar — adaptar seções

| Referência | Bolshoi adaptado |
|---|---|
| Conversations · All/Mentions/Unattended | Conversas · Todas/Aguardando/Resolvidas |
| Folders · Priority/Leads | Filas · Prioridade/Aguardando humano/Resolvidos hoje |
| Teams · Sales/Support L1 | Atendentes (lista de operadores online — útil pra transferência) |
| Channels · Email/Web/FB/Line | **REMOVER ou simplificar** — Bolshoi só tem WhatsApp. Mostrar "📱 WhatsApp · Bolshoi" como único canal |
| Labels · device-setup | Tags · VIP, Cabelo 💈, Estética 💆‍♀️, Recorrente |

### Brand — Logo
- Logo Bolshoi (tesouras + Western serif) substitui "Paperlayer" no topo
- Logo em 32-40px de altura
- Tagline pequena "Barbearia · Unaí, MG" abaixo (opcional)

### Composer — Reply / Private Note tabs
- **Reply (default):** envia pro WhatsApp (mesmo comportamento atual)
- **Private Note:** salva como nota interna na conversa (NÃO envia pro cliente)
  - Já existe feature "Notas internas" no info-panel — esta seria uma forma mais rápida de adicionar
  - Salvar em `HistoricoConversa.tipo='nota_interna'` ou nova tabela
  - Visível só pros operadores, com badge "🔒 Nota interna" inline na thread
- **AI Assist pill:** botão central — gera sugestão de resposta IA pro operador editar antes de enviar
  - Reusa serviço IA existente (`ai_service.py`) mas com prompt diferente: "Sugira resposta breve pra operador humano, em PT-BR, tom profissional"
  - Resposta sugerida vai pro textarea, operador edita ou envia direto

### Customer Dashboard tab (opcional, scope decisão)
- Read-only view do cliente:
  - Total de conversas, primeiro contato, último atendimento
  - Tags ativas
  - Stats: tempo médio resposta, msgs enviadas
  - Link "Ver no AppBarber" (NUNCA agendar pelo dashboard — BR-001)
- Reusa endpoint `/admin/cliente/{telefone}/stats` (criar se não existir)

### Copilot tab (opcional, scope decisão)
- View IA do operador:
  - "Resumo da conversa em 1 linha" (IA gera ao abrir)
  - "Tom do cliente" (frustrado / satisfeito / neutro)
  - "Sugestões de resposta" (3 opções)
- Reusa `ai_service.py` com prompt de análise

---

## Diferenças críticas vs implementação atual

| Aspecto | Atual | Referência |
|---|---|---|
| Sidebar | 72px só ícones | 240px expandida com labels e seções |
| Conv list filters | Filter chips horizontais scrolláveis | Sub-tabs Mine/Unassigned/All + sidebar seções |
| Card de conversa | Sem source/canal visível | Mostra canal (Bolshoi: só WhatsApp, então tag visual) |
| Composer | Só textarea + send | Tabs Reply/Private Note + AI Assist + toolbar 6 ícones |
| Info panel | Slide-in lateral | Toggle via "Close details" + tabs Contact/Copilot |
| Cor accent | #2481CC vibrante | #4E7AE7 balanceado |
| Bolha sistema | Não destacada | Pill centralizada cinza |
| Tags | Só "waiting-badge" | Sistema completo (labels com dots coloridos) |

---

## Recomendação de escopo

### Round 1 (visual puro — sem backend novo)
- Trocar Inter + paleta nova
- Layout 4 colunas expandido (sidebar 240px, info-panel 280px com tabs Contact/Copilot stubs)
- Pills sistema centralizadas (já existem msgs "Otávio assumiu" mas sem destaque)
- Sub-tabs Mine/Unassigned/All (mapear pros filtros atuais)
- Composer tabs Reply/Private Note (Private Note salva localmente, persist depois)
- Logo Bolshoi no topo da sidebar

### Round 2 (features novas — backend opcional)
- AI Assist (reusa ai_service.py)
- Private Note persistido em DB
- Customer Dashboard tab com stats reais
- Copilot tab com análise IA da conversa
- Sistema de tags/labels persistido

---

## Próximas decisões necessárias (humano)

1. **OK reescrever paleta de cor pra menos saturada?** (Atual #2481CC → ref #4E7AE7)
2. **OK trocar Plus Jakarta Sans → Inter?** (Fase 1 atual usa Plus Jakarta, ref usa Inter)
3. **Round 1 ou Round 1+2 nessa branch?** Round 2 requer migrations + endpoints novos.
4. **Logo Bolshoi: usar PNG cru ou pedir SVG?** PNG funciona; SVG escala melhor pra retina/mobile.
5. **AI Assist é uma feature aprovada pelo PO?** (Novo gasto NVIDIA por sugestão)
