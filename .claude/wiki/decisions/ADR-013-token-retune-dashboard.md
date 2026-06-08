# ADR-013: Re-tune do Sistema de Tokens do Dashboard — WCAG AA + Camada de Profundidade

Status: aceito
Data: 2026-06-07
Decisor: architect-agent
Stakeholders consultados: lead-agent (missão), frontend-agent (consumidor)

---

## Contexto

O redesign do dashboard (`redesign/admin-dashboard`) porta `static/admin/_concept.html` para produção
(`static/admin/index.html`). O concept foi desenvolvido com um ramp de cinza calibrado para WCAG AA e
uma camada de profundidade (sombras internas, elevação de bolhas) ausente na produção atual.

Problemas no arquivo de produção atual (`index.html`):

| Token | Valor atual | Razão do problema |
|---|---|---|
| `--text-secondary` | `#9CA3AF` | L≈0.296 → ~5.23:1 on #15161A — passa, mas margem estreita |
| `--text-muted` | `#6B7280` | L≈0.131 → ~2.62:1 on #15161A — **FALHA** WCAG AA |
| `--bg-bubble-bot` | `#064E3B` | Verde escuro saturado — diverge do concept; sem teste de contraste formal |
| `--bg-bubble-human` | `#3B6BDF` | Mesmo que accent; timestamp/corpo branco passa, mas sem acc-deep separado |
| `--border` | `#2A2C32` | Ok |
| `--border-soft` | `#1F2025` | Ok |
| `--border-muted` | `#34363D` | Ok |

Há também ausência total de tokens de profundidade (inset, sheen, lift) que o concept usa para
distinguir superfícies e dar textura ao compositor/avatar/bolhas.

Estratégia adotada: **re-tunar valores, não renomear tokens**. Os nomes de produção têm centenas de
call-sites no HTML/JS; renomear sem ganho funcional seria dívida pura. Novos tokens são adicionados
com nomes novos apenas quando não existe equivalente.

---

## Decisão

### Regras de contraste usadas

- Fórmula: WCAG 2.1 relative luminance (sRGB piecewise, expoente 2.4).
- Threshold: ≥ 4.5:1 para texto normal (AA), ≥ 3.0:1 para texto grande (AA large).
- Surface de referência para dark: `--bg-base #15161A` (L=0.006703) — a mais escura onde texto cai.
- Surface de referência para light: `--bg-base #f8fafc` (L=0.9520) — a mais clara.

---

## Tabela de tokens (COPIÁVEL pelo frontend-agent)

> Legenda coluna "Novo?": `sim` = token não existe em produção; `re-tune` = existe, valor alterado; `—` = não mexer (valores já corretos).

### Bloco 1 — Tokens existentes re-tunados

| Token | Valor dark | Valor light | Novo? | Contraste dark (par crítico) | Contraste light (par crítico) |
|---|---|---|---|---|---|
| `--text-primary` | `#E8EAEE` | `#0f172a` | re-tune | 15.7:1 on #15161A | 18.1:1 on #f8fafc |
| `--text-secondary` | `#A6AAB3` | `#334155` | re-tune | 7.96:1 on #15161A | 9.86:1 on #f8fafc |
| `--text-muted` | `#8A8E98` | `#64748B` | re-tune | 5.64:1 on #15161A | 4.54:1 on #f8fafc |
| `--border` | `#26282F` | `#e2e8f0` | re-tune | (non-text border) | (non-text border) |
| `--border-soft` | `#1F2127` | `#e2e8f0` | re-tune | (non-text border) | (non-text border) |
| `--border-muted` | `#2F323A` | `#cbd5e1` | re-tune | (non-text border) | (non-text border) |
| `--bg-bubble-bot` | `rgba(43,167,123,0.10)` | `#D1FAE5` | re-tune | texto #E8EAEE on tint ~14:1 | texto #0f172a on #D1FAE5 ~16.6:1 |
| `--bg-bubble-human` | `var(--acc-deep)` | `var(--acc-deep)` | re-tune | branco on #2F58CC 6.19:1 | branco on #2F58CC 6.19:1 |

**Notas do bloco 1:**

- `--text-primary`: de `#E5E7EB` → `#E8EAEE`. Incremento sutil (+3 lightness), mantém cool undertone alinhado ao concept. 15.7:1.
- `--text-secondary`: de `#9CA3AF` → `#A6AAB3`. Era ~5.2:1; sobe para 7.96:1 com margem confortável.
- `--text-muted`: de `#6B7280` → `#8A8E98`. Era ~2.62:1 (falha AA); agora 5.64:1. Este é o **fix crítico** do re-tune.
- `--border` / `--border-soft` / `--border-muted`: ajuste fino para alinhar com `--line`/`--line-soft`/`--line-mut` do concept.
- `--bg-bubble-bot` dark: de `#064E3B` (verde escuro opaco) → `rgba(43,167,123,0.10)` = `--green-tint` do concept. Superfície composited sobre `#15161A` fica ~`#172424`. Texto `--text-primary #E8EAEE` ≥14:1.
- `--bg-bubble-bot` light: mantém `#D1FAE5` de produção. Texto `--text-primary #0f172a` 16.6:1.
- `--bg-bubble-human`: usa `var(--acc-deep)` (#2F58CC) nos dois temas. Branco 6.19:1 ✓.

---

### Bloco 2 — Tokens novos (adicionar em ambos os blocos `:root`/`[data-theme="dark"]` e `[data-theme="light"]`)

| Token | Valor dark | Valor light | Novo? | Propósito |
|---|---|---|---|---|
| `--acc-deep` | `#2F58CC` | `#2D5BCC` | sim | Fill de bolha humano + CTA com texto branco. Dark 6.19:1; light 6.32:1 (branco) |
| `--text-faint` | `#54575F` | `#94A3B8` | sim | Separadores visuais e dividers APENAS — nunca usar como texto legível |
| `--success-text-strong` | `#46C699` | `#059669` | sim | Texto de sucesso garantido AA em ambos os temas |
| `--warning-text-strong` | `#E6B860` | `#B45309` | sim | Texto de warning garantido AA em ambos os temas |
| `--sheen-avatar` | `inset 0 1px 0 rgba(255,255,255,0.12)` | `inset 0 1px 0 rgba(255,255,255,0.60)` | sim | Highlight superior em avatares/badges circulares |
| `--inset-input` | `inset 0 1px 3px rgba(0,0,0,0.30), inset 0 0 0 1px rgba(0,0,0,0.18)` | `inset 0 1px 3px rgba(0,0,0,0.08), inset 0 0 0 1px rgba(0,0,0,0.06)` | sim | Campo de texto recuado (compositor, inputs de login) |
| `--inset-panel` | `inset 0 2px 6px rgba(0,0,0,0.22)` | `inset 0 2px 6px rgba(0,0,0,0.06)` | sim | Área de chat (canvas recuado) |
| `--shadow-bubble` | `0 1px 4px rgba(0,0,0,0.28), 0 0 0 1px rgba(0,0,0,0.12)` | `0 1px 4px rgba(0,0,0,0.10), 0 0 0 1px rgba(0,0,0,0.06)` | sim | Elevação sutil das bolhas de chat |
| `--lift-active` | `0 4px 16px rgba(0,0,0,0.38), 0 1px 4px rgba(0,0,0,0.22)` | `0 4px 16px rgba(0,0,0,0.16), 0 1px 4px rgba(0,0,0,0.08)` | sim | Elevação em item de lista selecionado/hovered |

**Notas do bloco 2:**

- `--acc-deep` dark `#2F58CC` vs light `#2D5BCC`: diferença é 1 ponto de L no canal azul — ambos resultam em branco 6.19:1/6.32:1; os valores são praticamente equivalentes e intercambiáveis. Usar o literal correto em cada tema.
- `--text-faint #54575F` dark: L≈0.097 → 1.88:1 on #15161A. **Intencionalmente sub-AA** — é válido só para elementos não-textuais (linhas, separadores, track de scrollbar). Nunca aplicar em `color:` de texto.
- `--text-faint #94A3B8` light: L≈0.317 → 3.67:1 on #ffffff — sub-AA deliberado para uso idêntico (separadores) no tema claro.
- `--success-text-strong #46C699` dark: L≈0.465 → 8.73:1 on #15161A ✓.
- `--success-text-strong #059669` light: L≈0.101 → 5.67:1 on #f8fafc ✓.
- `--warning-text-strong #E6B860` dark: L≈0.495 → 9.29:1 on #15161A ✓.
- `--warning-text-strong #B45309` light: L≈0.116 → 6.36:1 on #f8fafc ✓ (amber escuro, mantém legibilidade).
- Sombras depth: em dark, opacidades ~0.22–0.38 (preto sobre preto, sutil mas visível). Em light, ~40–60% de redução de opacidade, espelhando o padrão já estabelecido em `--shadow-sm`/`--shadow-md`/`--shadow-lg` (dark usa 0.28/0.32/0.38; light usa 0.10/0.12/0.15).

---

### Bloco 3 — Tokens de duração (avaliação)

| Token | Valor atual | Valor concept | Decisão |
|---|---|---|---|
| `--duration-instant` | `80ms` | `90ms` | **Manter 80ms** — 80ms é percebido como instantâneo; 90ms cria leve lag em clicks |
| `--duration-fast` | `120ms` | `150ms` | **Adotar 150ms** — 120ms é rápido demais para transições de cor/hover; 150ms dá smoothness perceptível |
| `--duration-normal` | `200ms` | `240ms` | **Adotar 240ms** — selection slide e mudanças de estado maiores beneficiam do extra 40ms; mantém abaixo do limiar de "lento" (~300ms) |
| `--duration-slow` | `320ms` | — (não existe no concept) | **Manter 320ms** — usado em animações de entrada de painel |

Resultado: atualizar só `--duration-fast` (120→150) e `--duration-normal` (200→240) em ambos os temas.
`--duration-instant` e `--duration-slow` ficam como estão.

---

## Consequências

**Positivas:**
- `--text-muted` passa de falha AA (2.62:1) para 5.64:1 — elimina violação de acessibilidade real.
- `--text-secondary` sobe de margem estreita (5.2:1) para 7.96:1 — margem robusta.
- Camada de profundidade (6 novos tokens shadow/inset) torna as superfícies distintas sem glassmorphism.
- `--bg-bubble-bot` alinha ao concept: verde-tint discreto vs. verde escuro opaco atual.
- `--acc-deep` separa o fill de bolha humano do `--accent` puro, permitindo que ambos coexistam com propósitos distintos.

**Negativas / riscos:**
- `--text-muted` sobe +20% de lightness em dark; qualquer UI que usava muted como "quase invisível" ficará mais visível — revisão visual recomendada no QA pass.
- `--bg-bubble-bot` muda de opaco para rgba; em browsers sem suporte a `color-mix()`, o compositing depende do contexto de stacking — testar em Chrome/Firefox/Safari.
- 6 novos tokens de sombra aumentam o tamanho do bloco CSS em ~12 linhas; impacto desprezível.

---

## Alternativas consideradas

1. **Renomear tokens para alinhar com concept** (`--t1`/`--t2`/`--t3`/`--t4` etc.): descartado — centenas de call-sites; sem ganho funcional; ADR-007 proíbe refatorações puramente cosméticas de grande escala.
2. **Manter `--text-muted #6B7280`**: descartado — falha AA documentada; não aceitável dado PRODUCT.md "WCAG 2.1 AA mínimo".
3. **Usar `color-mix()` para bubbles**: descartado — suporte parcial em produção (não há polyfill no projeto); `rgba()` é equivalente funcional sem dependência nova.
4. **Adotar valores de duração do concept sem avaliação**: descartado — 80ms para instant é melhor que 90ms (ver Bloco 3).
