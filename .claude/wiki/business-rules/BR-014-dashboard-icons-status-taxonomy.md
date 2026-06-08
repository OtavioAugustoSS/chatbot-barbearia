# BR-014: Dashboard — Taxonomia de Ícones, Status e Tags

**Domínio:** Dashboard de atendimento (modo híbrido)
**Decisor:** Product Owner
**Data:** 2026-06-07
**Status:** ATIVO

---

## Contexto

O dashboard usa dois padrões problemáticos identificados como "cara de IA" pelo proprietário:

- (A) Emojis 💈 e 💆‍♀️ como ícone estrutural em tags de categoria de serviço.
- (B) Badges de status minúsculos (~8px) sobre o avatar da conversa, onde a cor é o único indicador de estado.

Ambos violam regras do projeto:
- `PRODUCT.md` anti-reference explícita: "Emoji como ícone estrutural (usar Lucide/Heroicons SVG)"
- Princípio 4 de PRODUCT.md: "Cor nunca é único indicador de status. Sempre + ícone ou + texto."
- WCAG 2.1 AA: cor sozinha não basta para comunicar informação.
- Skill ui-ux-pro-max regra `no-emoji-icons` e `color-not-only`.

---

## Decisão 1 — Emojis de categoria devem ser aposentados

Os emojis 💈 e 💆‍♀️ **ficam APENAS no bot** (system prompt, respostas canônicas, mensagens WhatsApp ao cliente). No **dashboard operacional** eles são proibidos como ícone estrutural.

### Substituição: ícone SVG + rótulo texto

Cada categoria de serviço recebe um ícone SVG Heroicons (outline, stroke 1.6, tamanho 10–11px inline com o texto da tag) mais o rótulo em texto.

| Categoria | Ícone SVG Heroicons | Rótulo | Cor de acento |
|---|---|---|---|
| Barbearia (corte, barba, combo) | `scissors` (tesouras) — `heroicons/outline/scissors` | "corte" / "barba" / "combo" | var(--green-text) + var(--green-line) (atual) |
| Estética (qualquer serviço Isabella) | `sparkles` — `heroicons/outline/sparkles` | "estética" / "noiva" / "progressiva" etc. | var(--pink) + pink-line (atual) |

**Rationale da escolha de ícone:**
- Tesouras cruzadas é o próprio símbolo da marca Bolshoi ("tesouras cruzadas + serif"). Usá-las como ícone de categoria reforça identidade de marca premium, não enfraquece.
- `sparkles` para estética é um ícone estrutural reconhecido em dashboards de beleza/bem-estar — sem conotação de emoji, sem dependência de font rendering.
- Ambos são outline (stroke 1.6), alinhados ao vocabulário de ícones do restante do dashboard (Heroicons outline).

---

## Decisão 2 — Badges de status: ícone + texto sempre, cor nunca sozinha

### Taxonomia de 5 estados

| Estado | O que significa | Ícone SVG (Heroicons outline) | Cor de preenchimento do badge | Texto aria-label / tooltip |
|---|---|---|---|---|
| **Bot ativo** | Bot IA responde normalmente | `cpu-chip` (circuito) | var(--green) | "Bot ativo" |
| **Aguardando humano** | handoff disparado, nenhum operador assumiu ainda | `clock` (relógio) | var(--amber) | "Aguardando atendimento" |
| **Em atendimento humano** | operador assumiu, `atendente_id IS NOT NULL` | `headphones` (fone de ouvido) | var(--acc) / var(--acc-deep) | "Em atendimento — [nome]" |
| **Atendido por outro operador** | `bot_ativo=False`, outro atendente assumiu (não o logado) | `lock-closed` (cadeado) | var(--t3) cinza | "Atendido por [outro]" |
| **Encerrada / Resolvida** | conversa marcada como resolvida | `check` (checkmark) | var(--t4) cinza escuro | "Encerrada" |

### Regras de renderização WCAG-compliant

1. O badge sobre o avatar mantém a forma circular com ícone SVG interno (como hoje) — mas o ícone deve ser legível (mínimo 8px, preferencialmente 9px com stroke 1.8).
2. Em qualquer lugar que exiba status além do avatar-badge (thread header `st-dot`, tab filter), adicionar **texto junto** — ex: "● Bot ativo", "● Aguardando", "● Com você".
3. O `st-dot` no thead não pode ser o único indicador; o texto ao lado (já existe: "Com você", etc.) é obrigatório e suficiente.
4. Tooltip/aria-label no badge é obrigatório (campo `title` + `aria-label`).

### O que operador precisa ler em <200ms

- **Aguardando (amber + relógio):** urgente, ninguém atendeu. Leitura imediata por cor (amber) + forma (círculo relógio) + pill "aguardando · N min" já presente na conv-meta.
- **Bot ativo (verde + chip):** sem ação necessária do operador.
- **Em atendimento humano (azul + fone):** alguém já assumiu.
- **Outro operador (cinza + cadeado):** não tocar.
- **Encerrada (cinza escuro + check):** histórico.

---

## Decisão 3 — Taxonomia de tags: categoria vs. tag interna

### Dois tipos de tag, dois vocabulários visuais distintos

**Tipo A — Tags de categoria de serviço** (o que o cliente quer):
- Ícone SVG (tesouras ou sparkles) + texto
- Verde para barbearia, pink para estética
- Origem: injetado automaticamente pelo bot com base na última intenção detectada

**Tipo B — Tags internas operacionais** (metadados do operador):
- SEM ícone decorativo — apenas texto, fonte mono, estilo neutro (cor --t2, border --line-mut)
- Ex: "Fred", "resolvida", "vip", "noiva"
- Nota: "noiva" pode ser tanto categoria de serviço (serviço Isabella) quanto tag interna. Quando vier do bot como serviço, usar Tipo A (sparkles + pink). Quando adicionada manualmente pelo operador, usar Tipo B (neutro).

**"vip"** é tag interna operacional (Tipo B), não categoria de serviço. Usar amber-text + amber-line para distinção visual (já implementado parcialmente), mas SEM ícone — o texto "vip" já é suficientemente curto e distinguível pela cor amber.

### Separação no visual

Tags Tipo A (categoria) e Tipo B (interna) não precisam de separador visual além do estilo diferente — a presença ou ausência do ícone SVG já sinaliza a natureza da tag.

---

## Adendo 2026-06-07 — Revisão pós-QA

Após validação do QA, duas decisões adicionais:

**Badge size: 15px → 18px**
Badge de status sobre o avatar sobe de 15px para 18px. Ícone interno: 11–12px. Borda: 2.5px mantida. Offset: bottom/right -3px. Motivo: 15px com borda 2.5px deixa ~10px de área útil — insuficiente para leitura em <200ms (KPI do PRODUCT.md).

**Stroke como tokens CSS obrigatórios**
Declarar em `:root`:
```css
--icon-stroke: 1.6;       /* ícones no corpo geral */
--icon-stroke-badge: 1.8; /* ícones dentro de badges pequenos */
```
Aplicar via `stroke-width` nos SVGs inline. Valores ad-hoc são bloqueantes pelo QA (`icon-style-consistent`).

---

## Gap de implementação — Tags Tipo A não existem na API atual

Tags de categoria de serviço (Tipo A — corte, barba, estética, noiva) **não existem como dado estruturado na API atual**. No concept são dados hardcoded de exemplo.

Na API real, as conversas retornam:
- `labels` — array `{id, nome, cor}` — sempre Tipo B (labels criadas por operadores via `/admin/labels`)
- `tag` — string legacy (`"resolvido"`, `"follow_up"`, null) — sempre Tipo B

Para implementar Tipo A na produção, será necessário um campo `intencao_servico` (ou similar) detectado pelo bot e persistido no modelo `Usuario`. Isso é trabalho de backend futuro — não está no escopo deste ciclo de revisão do concept.

**No concept (mockup):** usar `data-type="servico"` manual nas tags de exemplo Tipo A. O contrato HTML fica estabelecido para quando o backend implementar.

---

## Referências

- [[PRODUCT.md]] — anti-references: "Emoji como ícone estrutural"
- [[BR-009]] — categorias barbearia vs estética na injeção de IA
- [[BR-004]] — handoff triggers: chamar_recepcao e transbordo_falha
- Skill ui-ux-pro-max: `no-emoji-icons`, `color-not-only`, `icon-style-consistent`
- WCAG 2.1 AA Critério 1.4.1: uso de cor
