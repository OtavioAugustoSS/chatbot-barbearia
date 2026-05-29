# Product

## Register

product

## Users

Operadores humanos da Barbearia Bolshoi (Unaí/MG) usam o dashboard de atendimento em turnos de várias horas pra assumir conversas WhatsApp quando o bot IA precisa de handoff humano. Contexto típico: balcão da barbearia ou backoffice, monitor desktop, segunda-domingo horário comercial. Job-to-be-done: ler status do bot/conversas em <200ms, responder cliente, gerenciar tags/notas internas, devolver pro bot quando resolvido. Secundariamente o Fred (proprietário) usa pra revisar estatísticas e cadastrar atendentes/respostas canônicas/etiquetas via `/settings`.

## Product Purpose

Dashboard de atendimento operacional pra Barbearia Bolshoi — interface híbrida onde operadores assumem conversas WhatsApp do bot IA quando ele aciona handoff (`intencao=chamar_recepcao`) ou falha (`transbordo_falha`). Sucesso = operador identifica conversa pendente em segundos, responde sem fricção, devolve pro bot, mantém tom profissional do tom da casa, NUNCA agenda (BR-001 — agendamento exclusivo via AppBarber).

## Brand Personality

Profissional · Calmo · Confiável. Voz operacional sem hype: o painel não vende, ele serve. Densidade de informação alta mas respiratória. Inspiração visual: Paperlayer/Drift inbox style (multi-canal operacional, dark cool-toned, micro-interactions com causa-efeito). Logo Bolshoi (tesouras cruzadas + serif Western "BOLSHOI BARBEARIA") fixa identidade clássica de barbearia premium em ambiente operacional moderno.

## Anti-references

- ❌ SaaS genérico indigo→violet gradient (Linear-clone, Notion-clone vibes)
- ❌ Estética landing-page no app operacional (este é ferramenta, não marketing)
- ❌ WhatsApp Web copycat (verde nos ticks, bolhas iguais) — somos Bolshoi, não Meta
- ❌ Glassmorphism em conteúdo de leitura prolongada (mensagens, conv list)
- ❌ Ícones flat coloridos estilo Material 2014
- ❌ Cards retangulares sem hierarquia, nested cards
- ❌ Emoji como ícone estrutural (usar Lucide/Heroicons SVG)

## Design Principles

1. **Confiança operacional > hype visual.** Status do bot (ativo / aguardando / humano) precisa ser lido em 200ms. Densidade respiratória, não vazio.
2. **Movimento expressa causa-efeito.** Bolha cliente entra da esquerda. Bolha operador entra da direita. Painel slide do lado chamado. Sem ornamento.
3. **Mono para dados técnicos.** Geist Mono em timestamps/telefones/badges/IDs. Plus Jakarta Sans em prosa. Tabular-nums sempre que números podem variar.
4. **Cor nunca é único indicador de status.** Sempre + ícone ou + texto. Acessibilidade WCAG AA mínimo.
5. **Bonito sob pressão operacional.** Operador olha 4 horas seguidas — paleta cool-toned charcoal #15161A não cansa, accent #3B6BDF com contraste 5.02:1 cumpre WCAG, motion polish + prefers-reduced-motion completo.

## Accessibility & Inclusion

- **WCAG 2.1 AA mínimo** em todos pares texto/fundo (4.5:1 normal, 3:1 large)
- **prefers-reduced-motion** respeitado: animações decorativas desligadas; transições funcionais ≤100ms
- **Keyboard nav** completo: tab order = visual order, focus-visible outline accent 2px com transition outline-offset
- **Color não é único indicador**: status badges sempre acompanhados de ícone + texto
- **Tabular-nums** em timestamps previne layout shift
- **Touch targets ≥44px** em botões mobile (operador pode usar tablet em balcão)
- Sem dependência de hover-only (acessibilidade touch)
