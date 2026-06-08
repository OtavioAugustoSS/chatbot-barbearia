# BR-015: Dashboard — Labels de Ação e Métricas Operacionais

**Domínio:** Dashboard de atendimento (modo híbrido)
**Decisor:** Product Owner
**Data:** 2026-06-07
**Status:** ATIVO

---

## Contexto

Duas questões levantadas no punch list QA referente ao concept minimalista do dashboard:

- P2-02: label do botão amber "Interromper bot" é ambíguo (pausa temporária vs. encerramento?).
- P1-01: bloco de métricas hero-grid (template genérico SaaS) duplica informação já presente nos tabs.

---

## Decisão 1 — Label do botão de pausa do bot

**Label de produção:** "Pausar bot"

**Tooltip obrigatório:** "Silencia o bot nesta conversa. Você assume o atendimento. Use 'Devolver ao bot' quando terminar."

**Par canônico:** "Pausar bot" e "Devolver ao bot" são os dois verbos que formam o ciclo completo. Devem aparecer juntos no thead-actions e se espelhar semanticamente.

**Cor:** amber — estado de atenção, não destrutivo. Vermelho é reservado para ações irreversíveis no sistema.

**Rationale:**
- "Pausar" é reversível por definição — sem ambiguidade sobre permanência.
- "Assumir conversa" orienta para resultado mas não deixa claro que o bot está em background esperando.
- "Interromper" soa como encerramento permanente.

---

## Decisão 2 — Remoção do hero-grid de métricas

**Decisão:** remover o bloco `.metrics` (grid 3 colunas com números em 26px).

**Motivo:** os tabs "Aguardando", "Meus" e "Bot" já existem e já carregam os mesmos números via `cnt` badges. O hero-grid duplica a informação com tratamento visual de KPI de landing page — padrão banido pelo PRODUCT.md ("estética landing-page no app operacional").

**Migração dos dados:**

| Dado que sumia | Para onde vai |
|---|---|
| "3 aguardando" | cnt badge do tab "Aguardando" (já existe, cor amber) |
| "2 atendendo" | cnt badge do tab "Meus" (já existe) |
| "14 com bot" | cnt badge do tab "Bot" — **NOVO**: o tab "Bot" não tinha cnt badge; adicionar |

O tab "Bot" sem cnt badge é o único dado que efetivamente se perde — exige adição do badge. Os outros dois já estão nos tabs.

**Forma mínima aceita:** tabs com três `cnt` badges sempre visíveis. Nenhuma linha-resumo adicional é necessária.

---

## Decisão 3 — Tick de confirmação nas bolhas do operador

**Decisão:** um check simples (tick único), não tick duplo.

**Semântica:** "enviado ao WhatsApp" — confirma que o `POST /admin/enviar/{telefone}` foi aceito pela Cloud API. Isso é tudo que o backend expõe; não há mecanismo de leitura pelo cliente.

**Motivo para não usar tick duplo:** tick duplo tem significado cultural estabelecido no ecossistema WhatsApp: "lido pelo destinatário". Exibir duplo sem ter esse dado cria expectativa falsa no operador ("o cliente leu e está ignorando"). Check simples é honesto com o que o sistema oferece.

**Alternativa "sem tick":** também aceitável, mas o check simples tem valor operacional real — confirma que o envio não falhou silenciosamente.

---

## Referências

- [[PRODUCT.md]] — anti-reference: "estética landing-page no app operacional"
- [[BR-004]] — handoff triggers; semântica de "pausar bot" alinhada com `bot_ativo=False`
- [[BR-014]] — decisões de ícones/status do mesmo ciclo de revisão
