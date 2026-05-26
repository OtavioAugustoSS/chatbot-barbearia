# Mockup Spec — fonte de verdade do redesign (extraído do bundle React)

**Origem:** `Bolshoi_Atendente_standalone_.html` (raiz). Bundle React decodificado pelo qa-agent (manifest base64+gzip → 7 componentes). CSS autoritativo completo: `.claude/wiki/qa/mockup-reference.css` (23KB, copiar valores de lá em caso de dúvida).
**Uso:** frontend-agent constrói contra isto (RD-1..RD-5); qa-agent re-audita contra isto (RD-6).
**Regra:** É vanilla JS no projeto real — NÃO portar React. Extrair só visual/estrutura. Reusar `state`, `api.js`, `sse.js` intactos.

---

## 1. Layout (RD-1) — `mockup-reference.css:42-50`
```css
.app { height:100%; display:grid; grid-template-columns: 360px 1fr; background: var(--bg-base); position:relative; overflow:hidden; }
```
- **2 colunas:** sidebar 360px + thread `1fr`. **SEM icon-rail.** A navegação (settings, menções, sair) vai pro header da sidebar / footer, não numa coluna separada.
- **Drawer de info = slide-over absoluto** (não é 3ª coluna). `.drawer` 380px, `position:absolute; right:0; transform:translateX(100%)`, abre com `.drawer-open` (translateX(0)). Backdrop `.drawer-backdrop` cobre `inset:0 0 0 360px`.
- Responsivo: `@media max 1100px` → sidebar 320px; `@media max 860px` → sidebar 80px (esconde me-info/metric-label/search/chips/conv-body/conn, conv-row vira só avatar centralizado).

## 2. Sidebar (RD-2) — `comp3.jsx`, CSS `:53-257`
Ordem vertical dentro de `.sidebar` (bg `--bg-sidebar #202c33`, flex-column):
1. **`.sidebar-header`** (`:61-79`): `.me` = avatar 40px circular gradiente `linear-gradient(135deg,#2481cc,#1a5a8f)` com iniciais + `.me-name` (15px/600) + `.me-role` (12px secondary, ex "Atendente · Bolshoi"). À direita `.me-actions` com `.icon-btn` (36px circular) de sair (icon `log-out`). → alimentar com `state.eu.nome`.
2. **`.metrics`** (`:92-117`): grid 3-col, gap 6px. Cada `.metric` = card bg `--bg-elev-2 #233138`, radius 10px, com barra colorida 3px à esquerda (`::before`, cor via `--metric-color`), `.metric-count` (22px/700) + `.metric-label` (10.5px uppercase). Os 3: **Aguardando** `#ef4858`, **Atendendo/Atendendo** `#00a884`, **Com bot** `#2481cc`. → alimentar com `data.totais_por_estado`.
3. **`.search-row`** (`:119-135`): `.search-input` (height 36, bg `--bg-base`, radius 8) com icon `search` + input. Botão `.icon-btn-sq` de filtro à direita.
4. **`.filter-chips`** (`:137-154`): chips **totalmente arredondados** `border-radius:16px`, bg `--bg-base`, texto secondary; ativo = `.chip-active` bg `color-mix(accent 18%)` cor accent. Chips: Todas / Aguardando / Meus / Com bot.
5. **`.conv-list`** (`:156-235`): scroll. Cada `.conv-row` (`:165-235`): avatar 48px circular (`.conv-avatar`, cor por contato) com `.status-dot` 12px no canto (waiting `#ef4858` com `pulse-red`, mine `#2481cc`, bot `#00a884`); `.conv-name` 15px/500 ellipsis + `.conv-time` 11.5px (urgent = waiting vermelho); `.conv-preview` 13.5px secondary com prefixo 🤖 (bot) ou ↩ (mine); `.conv-unread` badge verde `--ok`. Ativo: `.conv-row-active` bg `#2a3942` + barra accent 4px à esquerda (`::before`).
6. **`.sidebar-footer`** (`:242-257`): `.conn` com `.conn-dot` (7px verde glow) + icon `wifi` + "Conectado · WhatsApp Cloud API". Botão mute `.icon-btn` (bell/mute).

## 3. Thread / bolhas (RD-3) — `comp4.jsx`, CSS `:259-577`
- **`.thread-header`** (`:270-312`): `.thread-customer` (avatar 40px `.conv-avatar-md` + nome + sub com dot de status + telefone). `.thread-actions`: botão de ação por status (`waiting`→Assumir, `mine`→Devolver à IA, `bot`→Interromper bot) `.btn-primary` (bg accent) ou `.btn-ghost`, + icon-btns (tag/history/user-circle abre drawer).
- **`.thread-tags`** (`:314-333`): chips de etiqueta accent-tinted; ghost "+ adicionar".
- **`.thread-scroll`** (`:336-364`): bg `#0b141a` + `.thread-pattern` (dots radiais opacity 0.045, o "wallpaper").
- **`.bubble`** (`:405-414`): max-width 72%, padding `6px 10px 8px`, radius 8px, font 14.2px/1.42, shadow sutil.
  - `.bubble-client` bg `#202c33`, canto sup-esq reto (tail à esquerda).
  - `.bubble-bot` bg `--bubble-bot #04473b`, canto sup-dir reto.
  - `.bubble-human` bg `#2481cc`, canto sup-dir reto.
- **Caudas (tails)** (`:428-463`): `[data-tails="1"] .bubble::before` = triângulo 8x13 clip-path herdando bg. Cliente tail à esquerda (`left:-7px`), bot/humano à direita (`right:-7px`). **Agrupamento:** bolhas consecutivas do mesmo remetente (`.row-X + .row-X`) escondem o tail e restauram canto reto + apertam `margin-top: calc(2px - var(--bubble-gap))`.
- **`.bubble-author`** (RD-5, `:465-474`): 11.5px/600, **NÃO uppercase**, com ícone inline + gap. Cliente cor `#e9b884`, bot `#7fe3c4` (icon `bot`), humano `#d6e8fa` (icon `user`). Texto humano: "Atendente · {nome}". Bot: "Bolshoi Bot". **NÃO usar o chip "IA" atual.**
- **`.bubble-text`** (`:477-480`): `white-space:pre-wrap` (preserva `\n` do operador).
- **`.bubble-meta`** + `.bubble-time` (10.5px) + **ticks SVG** (`DeliveryTicks` comp4:4-13): icon `check` (1 tick = entregue) / `check-double` (2 ticks). Cor lido = `--tick-read #54a4d4`; na bolha humana (azul) forçar ticks brancos (`:500`). Backend hoje só tem "entregue" → use check simples; check-double só se houver flag de leitura.
- **`.date-divider`** (`:374-386`) bg `#1d282f` capsule; **`.system-row`** (`:388-399`) capsule translúcida com icon `arrow-undo` (ex "Diego assumiu", "Bot retomou").

## 4. Composer — CSS `:502-577` (já em boa forma no atual)
- `.composer` bg `#202c33`. `.composer-banner` contextual (bot ativo / cliente aguardando com `.pulse-red`).
- `.composer-row`: icon-btns 42px circular (bolt/quick-replies, smile, paperclip), `.composer-input` textarea (min-h 42, bg `--bg-elev #2a3942`, radius 12), e à direita: `.send-btn` 44px circular accent COM texto, ou `.composer-icon` mic quando vazio. **Send button já está circular no atual — OK.**
- `.qr-pop` (`:579-618`): popover de respostas rápidas acima do composer.

## 5. Drawer de info (RD-4) — `comp5.jsx`, CSS `:620-779`
Slide-over 380px. Seções (cada `.drawer-section` separada por `border-bottom: 8px solid var(--bg-base)`):
- **`.drawer-header`** 56px: botão x + "Perfil do cliente" + more-v.
- **`.drawer-hero`**: avatar 120px circular + nome 22px + telefone (icon phone) + `.drawer-quick` (3 botões: Mensagem/Favoritar/Etiquetar, `.drawer-quick-btn` 56px com icon+label).
- **Estatísticas**: `.drawer-stats` grid 2-col, cada `.drawer-stat` (label uppercase + value). Campos: Cliente desde, Última interação, Mensagens totais, Status atual.
- **Etiquetas**: `.drawer-tags` (accent-tinted) + botão `+`.
- **Notas internas**: `.drawer-note` (amarelo `#ffd54f` tint) + textarea `.drawer-note-input` + botão salvar.
- **Atendimentos recentes**: `.drawer-history` com `.dot` colorido (blue/green/red) + título + sub.

## 6. Ícones — `comp1.jsx`
SVG single-stroke, viewBox 0 0 24, `stroke-width:1.8`, `fill:none`, `stroke:currentColor`, linecap/linejoin round. Disponíveis: search, plus, new-chat, more-v, log-out, send, bolt, smile, tag, user, user-circle, x, mute, bell, check, check-double, paperclip, bot, arrow-undo, arrow-down, wifi, pin, filter, note, history, chat, star, mic, pause, phone, sparkles. (paths exatos em `%TEMP%\mockup_jsx\comp1.jsx` ou re-decodificar do bundle.)

## 7. Paleta (`:root` `:3-24`) — usar tokens, não hex inline
```
--bg-base #111b21 · --bg-sidebar #202c33 · --bg-elev #2a3942 · --bg-elev-2 #233138
--bubble-client #202c33 · --bubble-bot #04473b · --bubble-human/--accent #2481cc
--border #2a3942 · --border-soft #1a2329
--text #e9edef · --text-secondary #8696a0 · --text-muted #667781
--tick-read #54a4d4 · author cliente #e9b884 · author bot #7fe3c4 · author humano #d6e8fa
--waiting #ef4858 · --ok #00a884 · --info #2481cc
font default: Segoe UI, Helvetica Neue, Roboto, system-ui (Inter é opção, não default)
```
**Atenção:** trocar todo `rgba(99,102,241,...)` (indigo do tema antigo) por `var(--accent-subtle)`/accent. Ocorrências achadas: `index.html:1058`, `app.js:728` (RD-5).

## 8. Mapeamento mock → contrato real (NÃO inventar campos)
Mock data (`comp2.jsx`) é fictício. Os campos reais vêm do backend:
- `conv.status` mock = `'waiting'|'mine'|'bot'` → mapear do estado real (aguardando_humano / atendente_id==eu / bot_ativo). NÃO mudar o contrato `/admin/conversas`.
- `data.items` (lista) + `data.totais_por_estado` (métricas) — contrato atual de `getConversasFiltradas`, confirmado intacto.
- Mensagem: origem `cliente`/`humano`/`bot`, `criado_em`, `entregue`, `atendente_nome` — já usados em `app.js:bolha()`.
- Stats do drawer (Cliente desde / totalMessages) vêm de `/admin/cliente/{tel}/info` — confirmar campos disponíveis com backend-agent antes de exibir; o que não existir, omitir (não inventar).
