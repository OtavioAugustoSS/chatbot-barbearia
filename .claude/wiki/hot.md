# hot.md — Cache de Contexto Recente

## Convenções
- Atualizado pelo **lead-agent** ao fim de cada ciclo de trabalho
- Contém snapshot do estado atual do time: o que está em andamento, decisões recentes, próximos passos
- Limite: ~200 linhas. Ao exceder, mover entradas antigas para `log.md`
- Todos os teammates leem este arquivo **PRIMEIRO** ao iniciar trabalho

## Snapshot atual (2026-05-22) — Pós Loop Autônomo de Melhoria Contínua

Sprint Visual 1.0 CONCLUÍDA (14/14 PASS). Loop autônomo de 4 rodadas executado enquanto o usuário dormia.
Release report em `docs/release/visual_1_0.md`.

---

## Melhorias entregues no loop autônomo (2026-05-22)

### Backend (backend-loop-1 + backend-loop-2)

| Item | Arquivo | Impacto |
|---|---|---|
| Fix `dir()` → `locals()` em except JSONDecodeError | `services/ai_service.py` | Log de erro de IA mostrava sempre 'N/A' — agora mostra texto real |
| Cache de módulo `_cache_horarios` (5min TTL) | `services/ai_service.py` | Eliminava query SQL extra por chamada de IA |
| `threading.Lock` no cache de serviços e horários | `services/ai_service.py` | TD-005: race condition em multi-thread corrigida |
| `RotatingFileHandler` para `erro_ia_debug.txt` | `services/ai_service.py` | TD-004: sem mais risco de disco cheio |
| `!reiniciar` reseta todos campos de estado | `api/webhook.py` | Estado inconsistente pós-transbordo corrigido |
| Novo comando `!status` para admins | `api/webhook.py` | Diagnóstico em campo sem dashboard |
| Dedupe TTL 600→3600s | `api/webhook.py` | TD-014: protege reenvios Meta em janelas maiores |
| `lock.acquire(timeout=90)` no per-phone lock | `api/webhook.py` | TD-013: starvation se NIM travar corrigido |
| TD-016: SSE `"reativado"` → `"online"` | `api/admin.py` | ADR-005 compliance |
| Regex pagamento expandido (nubank, picpay, etc.) | `core/respostas_canonicas.py` | FAQ canônica sem IA para marcas específicas |
| Regex PCD/acessibilidade expandido | `core/respostas_canonicas.py` | "cadeirante/deficiente/PCD" casam corretamente |
| `RESPOSTA_DISPONIBILIDADE_FRED` + ordem de check | `core/respostas_canonicas.py` | "Fred tá lá?" não vaza telefone sem pedido |
| Regra 4 EQUIPE reformulada (sem gênero) | `core/prompts.py` | Fraseologia baseada em gênero removida |
| `ANCORA_ANTI_DRIFT` expandida (+4 regras) | `core/prompts.py` | Ativa 33% mais cedo + cobre pipe/ref, somar preços |
| Migration `0009-idx-usuarios-status-conversa.sql` | `scripts/migrations/` | TD-011: índice para `_auto_unsnooze()` |

### Frontend (frontend-loop-1 + frontend-loop-2)

| Item | Arquivo | Impacto |
|---|---|---|
| **BUG CRÍTICO**: `SyntaxError` em `trocarTab()` | `settings.html:467` | Tabs de configuração estavam 100% quebradas |
| `ev.count` → `ev.afetadas` (ADR-005) | `app.js` | Toast de bulk mostrava vazio |
| `abrirModalConfirmar()` Promise-based | `app.js` + `index.html` | 6 `confirm()` nativos eliminados |
| Click no overlay fecha modal confirm | `app.js` | UX padrão restaurado |
| Auto-update de timestamps (60s, sem re-render) | `app.js` | Timers relativos ficam atualizados sem custo |
| `aria-label` em 5 elementos | `index.html` | Acessibilidade básica |
| `role="dialog"` + `aria-modal` nos 4 modais | `index.html` | Acessibilidade screen readers |
| `#canned-btn` com tooltip "Respostas rápidas (/)" | `index.html` | UX: botão agora explicado |
| `note-input` maxlength=4096 | `index.html` | Limite de caracteres em notas |
| `#send-btn` 44px touch target (mobile) | `index.html` | Mobile: alvo de toque mínimo |
| Modais com `max-width: 95vw` em 375px | `index.html` | Modais cabem em qualquer tela |

### Documentação (architect-loop-2 + po-loop-2)

| Artefato | Conteúdo |
|---|---|
| ADR-009 | Bulk action atomicity — parcial intencional, documentado |
| ADR-010 | Background task exception handling — fix urgente identificado |
| ADR-011 | RBAC ausente — riscos aceitos, critérios para implementação |
| BR-006 a BR-013 | 8 novas business rules: escopo bot, anti-drift, serviços não oferecidos, injeção IA, horários, GAP-06/08 decisions, nome cliente, cobertura FAQ |
| US-GAP-02 | User story formal para reativação por timeout (BR-011/GAP-08) |

---

## ADRs vigentes
ADR-001 schema • ADR-002 HTTP errors • ADR-003 NVIDIA NIM retry • ADR-004 paginação • ADR-005 SSE contract • ADR-006 AI JSON • ADR-007 vanilla JS • ADR-008 promise modal • ADR-009 bulk atomicity • ADR-010 background exception • ADR-011 RBAC ausente

## BRs vigentes
BR-001 anti-agendamento • BR-002 contato Fred • BR-003 formatação • BR-004 handoff triggers • BR-005 bot_only vs híbrido • BR-006 escopo conteúdo • BR-007 anti-drift • BR-008 serviços não oferecidos • BR-009 injeção IA • BR-010 horários • BR-011 GAP-06/08 • BR-012 nome cliente • BR-013 FAQ cobertura

## Débito técnico ativo (prioritário)

| ID | Prioridade | Problema | Esforço |
|---|---|---|---|
| TD-001 | Crítico | `TZ=UTC` não configurado no servidor | Config 1 linha |
| TD-002 | Crítico | Zero testes automatizados | 8-16h |
| ADR-010 fix | Urgente | `tarefa_em_segundo_plano_ia` sem try/except raiz | 2 linhas |
| TD-012 | Alto | Trim histórico usa `NOT IN` — migrar para DELETE por min_id | 1-2h |
| TD-015 | Médio | `intencao String(30)` — migration para String(50) | 30min |
| TD-007 | Médio | Search usa LIKE sem índice FULLTEXT | 2-3h |

## Pendências de negócio
- **GAP-06 DECIDIDO**: sem auto-atribuição. Alerta visual de espera no dashboard (Sprint 0.3.0)
- **GAP-08 DECIDIDO**: reativação por timeout com frase de contexto na 1ª mensagem — US-GAP-02 criada
- **BR-013**: telefone comercial da barbearia — aguarda confirmação do Fred

## Próximos passos (Sprint 0.3.0)

1. **Configurar `TZ=UTC` no servidor** — TD-001, risco ativo, 1 linha
2. **ADR-010 fix** — 2 linhas em `webhook.py`, fix de blind spot de exceções
3. **US-GAP-02** — backend: campo `reativado_por_timeout` + lógica de frase de contexto
4. **TD-015** — migration `ALTER TABLE historico_conversas MODIFY intencao VARCHAR(50)`
5. **TD-012** — trim histórico com DELETE por min_id (mais eficiente)
6. **RBAC supervisor/agent** — desbloqueia força-transferência, métricas, proteção de endpoints
7. **Analytics dashboard** — volume, tempo médio, ranking atendentes
8. **Testes automatizados** — mínimo: funções puras de webhook + ai_service
