# BR-AUDIT-002: Avaliacao de Valor — Funcionalidades Chatwoot nao Implementadas
Data: 2026-05-21
Stakeholders: product-owner-agent (avaliacao autonoma, Fase 1 auditoria)

## Contexto
O redesign atual ja implementou features inspiradas no Chatwoot (labels multiplas, status de conversa, canned responses, atribuicao, @mentions, bulk actions, saved views, busca global, atalhos de teclado, temas). Esta nota avalia as 6 funcionalidades RESTANTES propostas pelo usuario para avaliacao de valor de negocio.

Criterios de pontuacao de valor:
- **Alto**: afeta diretamente qualidade do atendimento ao cliente ou receita
- **Medio**: melhora operacao interna sem impacto direto no cliente
- **Baixo**: conforto, analytics ou auditoria nao critica para o tamanho atual

---

## 1. Automation Rules
*Exemplo: conversa sem resposta por 30min automaticamente atribuida ao supervisor*

**Valor de negocio: MEDIO**

Justificativa:
- A barbearia opera com equipe pequena (2-4 atendentes conforme volume historico). Automacoes complexas tendem a ser subutilizadas.
- O caso de uso real e simples: conversa em `aguardando_humano` por muito tempo sem ser assumida. Isso ja e resolvido parcialmente pelo auto-refresh de 30s + visual de ponto pulsante vermelho.
- Automacao util seria: `se aguardando_humano > 15min E nenhum atendente online, enviar mensagem ao cliente ("em breve um atendente retorna")`. Mas essa logica borderline com o principio de nunca prometer retorno humano (regra do bot).
- Requer infraestrutura de scheduler (Celery/APScheduler) nao presente no projeto.

Recomendacao: **Backlog de medio prazo**. Implementar apenas se volume de transbordos aumentar a ponto de causar perdas de atendimento.

Pre-requisito critico: qualquer automation que envolva envio de mensagem automatica deve passar por revisao de PO para garantir nao quebrar regras (ex.: nao prometer agendamento, nao prometer retorno).

---

## 2. RBAC Supervisor vs Atendente
*Supervisor ve metricas, pode reatribuir qualquer conversa*

**Valor de negocio: ALTO**

Justificativa:
- Ja existe user story US-123 (modo supervisao) e US-087 (gestao de atendentes) — o conceito e reconhecido.
- Sem RBAC, qualquer atendente pode desativar labels, criar globais, acessar dados de todos os clientes.
- GAP critico atual: GAP-01 — atendentes desativados so podem ser reativados via SQL direto. Com RBAC, supervisor teria esse botao.
- Atribuicao forcada (supervisor move conversa de atendente offline para outro) e bloqueada hoje — exige ser o dono atual. Supervisor com role diferente resolveria GAP identificado em US-197.
- Implementacao minima viavel: adicionar coluna `papel` em `Atendente` (`atendente` | `supervisor`), check em endpoints criticos, badge visual no painel.

Recomendacao: **Prioridade alta para proximo ciclo**. Escopo minimo: coluna `papel`, protecao de endpoints de gestao de atendentes, botao reativar atendente para supervisor.

---

## 3. Analytics Dashboard
*Volume de conversas, tempo medio de resolucao, ranking de atendentes*

**Valor de negocio: MEDIO (baixo a curto prazo, medio a longo prazo)**

Justificativa:
- Com equipe pequena e volume de atendimento reduzido de uma barbearia, analytics detalhados tem pouco impacto imediato nas decisoes do dia a dia.
- O que o Fred (proprietario) realmente precisa: saber se o bot esta funcionando (quantos transbordos por semana) e se os atendentes estao respondendo rapido.
- As metricas mais uteis ja estao proximas de implementacao: cards de fila (aguardando/atendendo/bot) sao analytics em tempo real.
- Analytics historico (grafico de conversas por semana, tempo medio) exige persistencia de dados adicionais e infraestrutura de queries agregadas.
- Risco: complexidade de implementacao alta para valor percebido baixo no tamanho atual do negocio.

Recomendacao: **Backlog de longo prazo**. Implementar quando o volume justificar (estimativa: > 200 conversas/mes). Priorizar exportacao CSV como primeiro passo (mais simples, mesmo valor percebido para o proprietario).

---

## 4. Audit Trail por Conversa
*Log de cada acao: quem assumiu, quando, o que enviou*

**Valor de negocio: MEDIO**

Justificativa:
- US-194 ja implementa audit trail parcial para transferencias (INSERT em `HistoricoConversa` com `origem='humano'` e `intencao='transferencia'`).
- O que esta faltando: separadores de evento inline na thread (VIS-03, US-039 PARCIAL). O dado existe — o backend salva eventos de handoff — mas o frontend nao renderiza como separadores visuais.
- Para uma barbearia, o uso primario de audit trail e: entender porque o cliente ficou insatisfeito (quem respondeu o que). Isso ja e coberto parcialmente pelo historico de mensagens com `origem` diferenciado (bot/humano).
- Audit trail formal com log de acoes administrativas (quem criou/editou label, quem desativou atendente) seria util para RBAC (item 2).

Recomendacao: **Medio prazo, resolver VIS-03 primeiro**. O separador de evento inline (handoff) e o audit trail mais util e ja tem estrutura pronta. Custo de implementacao baixo, valor percebido alto para o atendente.

---

## 5. Contact Profile Enrichment
*Campos extras: preferencia de barbeiro, historico de servicos*

**Valor de negocio: ALTO (especifico para barbearia)**

Justificativa:
- Este e o item com maior diferencial competitivo especifico para a Barbearia Bolshoi. Nenhuma barbearia concorrente da regiao de Unai/MG tem esse nivel de CRM.
- Casos de uso imediatos:
  - Atendente ve que cliente sempre agenda com "Eduardo" → direciona no atendimento
  - Historico de servicos mostra que cliente nunca fez barba → sugere naturalmente
  - Preferencia de horario registrada → atendente ja menciona vagas naquele horario
- VIS-05 (botao "Favoritar cliente" sem funcionalidade) e VIS-06 ("Servicos frequentes" com dado errado) ja sinalizam que a UI foi projetada para isso mas sem backend.
- Implementacao possivel sem AI: campos livres + notas internas (ja implementadas) cobrem 70% do caso de uso. O restante e inferencia de historico de agendamento (exige integracao com AppBarber — fora de escopo atual).

Recomendacao: **Prioridade alta, implementacao incremental**. Fase 1: campos manuais no perfil do cliente (barbeiro preferido, observacoes, VIP flag). Fase 2: historico de servicos via inferencia das notas. Fase 3: integracao AppBarber (dependencia externa).

Restricao: informacoes de preferencia de barbeiro NAO devem ser usadas pelo bot automaticamente para sugerir barbeiros — isso configura "comprometimento de agenda" que viola a regra anti-agendamento. Bot deve continuar direcionando para AppBarber. Os dados sao para uso EXCLUSIVO do atendente humano no painel.

---

## 6. Canned Response Analytics
*Quantas vezes cada resposta rapida foi usada*

**Valor de negocio: BAIXO**

Justificativa:
- Com menos de 10 respostas rapidas globais e uma equipe pequena, analytics de uso de canned responses tem valor marginal.
- O caso de uso real seria: identificar quais canneds nunca sao usadas e limpar o catalogo. Com 10-20 items, isso e visivel a olho nu.
- Implementacao: contador `uso_count` em `CannedResponse` + incremento em cada uso. Simples, mas de pouca utilidade pratica no contexto atual.
- Poderia ser util se a barbearia escalar para franquia (multiplas unidades) — cenario nao mapeado ainda.

Recomendacao: **Nao implementar no curto/medio prazo**. Se o catalogo crescer muito (> 50 canneds), reconsiderar.

---

## Ranking de Prioridade (Top 3 para implementacao)

| Ranking | Funcionalidade | Valor | Justificativa resumida |
|---------|---------------|-------|------------------------|
| 1 | Contact Profile Enrichment | Alto | Diferencial competitivo direto para barbearia; VIP flag, barbeiro favorito, notas estruturadas |
| 2 | RBAC Supervisor vs Atendente | Alto | Resolve GAP-01 critico (reativar atendente); protege endpoints administrativos |
| 3 | Audit Trail (VIS-03 first) | Medio | Separador de evento inline e o item de menor custo com maior ganho perceptivel |

## Funcionalidades descartadas para o roadmap atual
- Automation Rules: aguardar crescimento de volume
- Analytics Dashboard: exportacao CSV como substituto imediato
- Canned Response Analytics: desnecessario no tamanho atual

## Excecoes e restricoes de produto
- Contact enrichment: dados de preferencia de barbeiro sao exclusivos do painel humano. Bot continua redirecionando para AppBarber sem usar esses dados.
- RBAC: qualquer endpoint que supervisor usa para enviar mensagem ao cliente ainda segue as mesmas restricoes do atendente (sem agendar, tom profissional).
- Audit trail: acoes do bot (intencao, resposta_sugerida) ja ficam em `HistoricoConversa`. Audit de acoes administrativas (CRUD de labels, atendentes) e o gap real.
