# TECH-DEBT-001: Débito Técnico Priorizado
Data: 2026-05-21
Autor: architect-agent
Fonte: Auditoria completa de codebase (FASE1-AUDIT)

## Metodologia de priorização

Escala: **Crítico** (risco de corrupção/segurança) → **Alto** (impacto em produção esperado) → **Médio** (degradação de qualidade) → **Baixo** (melhoria de processo)

---

## CRÍTICO

### TD-001: Datetime naive no banco de dados — timezone confusion
**Localização**: todos os modelos em `db/models.py`, `api/admin.py/_iso_utc()`
**Problema**: MySQL armazena `DATETIME` sem timezone. O código grava `datetime.now(timezone.utc)` mas o banco persiste como naive. O workaround atual em `_iso_utc()` assume que todo naive é UTC (`dt.replace(tzinfo=timezone.utc)`). Se o servidor mudar de fuso (VPS sem configuração de TZ), todos os timestamps históricos serão interpretados errado.
**Risco**: Cálculo incorreto de `BOT_REATIVAR_APOS_HORAS` (bot reativado horas antes ou depois do esperado), ordenação de conversas errada, confusão em logs.
**Solução recomendada**: Padronizar para `DATETIME` + garantir `TZ=UTC` no servidor via variável de ambiente (`export TZ=UTC` no systemd service) + documentar no CLAUDE.md. Alternativa: migrar para `TIMESTAMP` MySQL (que converte automaticamente) mas requer migration de todas as tabelas.
**Esforço**: 1-2h (config do servidor) + 4h (se migrar para TIMESTAMP).

---

### TD-002: Ausência completa de testes automatizados
**Localização**: todo o projeto
**Problema**: CLAUDE.md documenta explicitamente "No test suite exists — testing is done manually via WhatsApp". O pipeline de pre-AI layers (`webhook.py`) tem 8 camadas de lógica, o `ai_service.py` tem sanitização e validação, e `admin.py` tem lógica de concorrência (`assumir` com UPDATE condicional) — nenhuma com cobertura de teste.
**Risco**: Qualquer refatoração pode quebrar comportamento silenciosamente. Especificamente:
  - A lógica de handoff tem ao menos 4 ramificações (bot_only/hibrido × chamar_recepcao/transbordo_falha)
  - A sanitização de JSON da IA (ADR-006) tem edge cases não testados
  - Rate limit e dedupe são in-memory e difíceis de testar manualmente
**Solução recomendada**: Iniciar com testes unitários de `_e_saudacao_pura()`, `_e_pedido_de_menu()`, `_normalizar_texto_envio()`, e `_validar_resposta()` (funções puras). Depois testes de integração para o webhook com mock da Meta API.
**Esforço**: 8-16h para cobertura mínima útil (~60%).

---

## ALTO

### TD-003: Dois sistemas de nomenclatura de migrations coexistindo
**Localização**: `scripts/migrations/`
**Problema**: Existem dois padrões de prefixo:
  - Legacy: `TASK{NNN}_descricao.sql` (TASK001 até TASK017, não sequencial: faltam TASK006-TASK014, TASK016)
  - Novo: `{NNNN}_descricao.sql` (0001 a 0008)
  - Outlier: `TASK_FOTO_URL.sql` (sem número sequencial)
Não há tabela de controle de versão (sem Flyway/Alembic) — determinar quais migrations foram aplicadas em cada ambiente é impossível sem inspecionar o banco manualmente.
**Risco**: Ao configurar ambiente novo, não está claro qual ordem aplicar as migrations. Risco de pular migrations ou aplicar em ordem errada.
**Solução recomendada**: Criar `scripts/migrations/README.md` listando todas as migrations em ordem canônica de aplicação. Padronizar novos arquivos no formato `{NNNN}` sequencial a partir de `0009`. Não renomear os existentes (histórico de git).
**Esforço**: 2-3h.

### TD-004: `erro_ia_debug.txt` sem rotação ou limite de tamanho
**Localização**: `services/ai_service.py/_registrar_erro_debug()`
**Problema**: Arquivo de log de erros da IA cresce indefinidamente no filesystem. Em produção contínua, pode encher o disco.
**Risco**: DoS acidental por disco cheio em caso de instabilidade prolongada da NVIDIA NIM.
**Solução recomendada**: Substituir por `logging.handlers.RotatingFileHandler` com `maxBytes=5MB, backupCount=3`, ou simplesmente usar o `log.error()` existente e remover o arquivo de texto paralelo.
**Esforço**: 1h.

### TD-005: Cache de serviços/barbeiros não-thread-safe
**Localização**: `services/ai_service.py/_cache_db`
**Problema**: `AIService` é instanciada uma vez em `api/webhook.py` (singleton por módulo). O dict `_cache_db` é mutado sem lock:
```python
self._cache_db = {"data": dados, "expira_em": agora + self._cache_ttl_segundos}
```
Em cenário de múltiplas threads simultâneas (FastAPI com `workers>1` ou múltiplas requests simultâneas), pode ocorrer race condition na escrita/leitura do cache.
**Risco**: Em produção com Uvicorn multi-worker, cada worker tem seu próprio processo Python — sem problema. Em Uvicorn single-worker com ThreadPoolExecutor (background tasks usam threads), há risco baixo mas real.
**Solução recomendada**: Adicionar `threading.Lock` ao redor da seção crítica de escrita do cache, ou usar `functools.lru_cache` com TTL via decorator.
**Esforço**: 1-2h.

---

## MÉDIO

### TD-006: Presença de atendente armazenada apenas em memória
**Localização**: `api/admin.py/_presence_store`
**Problema**: `_presence_store: dict[int, tuple[str, datetime]]` perde estado em restart. Após deploy, todos os atendentes aparecem como offline até enviarem heartbeat (30s máximo de lag).
**Risco**: UX ruim imediatamente após deploy — dashboard mostra todos offline por até 30s.
**Solução recomendada**: Aceitável por ora (CLAUDE.md documenta isso). Se incomodar, adicionar coluna `status_presence` na tabela `atendentes` com TTL de 90s verificado por query.
**Esforço**: 2-4h.

### TD-007: Busca por LIKE sem índice FULLTEXT
**Localização**: `api/admin.py/search_mensagens()`
**Problema**: `GET /admin/search?q=...` usa `LIKE %termo%` em `mensagem_cliente` e `resposta_bot` (colunas `TEXT`). MySQL não usa índice para `LIKE` com wildcard no início. O endpoint tem comentário: "MVP: LIKE simples. Se ficar lento (>5s em 50k+ mensagens), migrar para FULLTEXT."
**Risco**: Query lenta quando `historico_conversas` crescer. Com 50k mensagens, tempo estimado >2s.
**Solução recomendada**: Adicionar `FULLTEXT INDEX` em `mensagem_cliente, resposta_bot` e usar `MATCH ... AGAINST` com modo booleano.
**Esforço**: 2-3h (migration + query).

### TD-008: `static/admin/js/app.js` sem tamanho documentado
**Localização**: `static/admin/js/app.js`
**Problema**: Arquivo principal do frontend sem limite de tamanho ou regra de extração de módulo. Baseado na extensão de funcionalidades (Chatwoot features Phase 1-3), provavelmente já é grande.
**Risco**: Manutenibilidade do frontend degrada com o tempo.
**Solução recomendada**: Monitorar tamanho; se passar de 1000 linhas, iniciar extração de responsabilidades por módulo (ex: `conversation.js`, `messages.js`, `filters.js`).
**Esforço**: 4-8h de refatoração quando necessário.

---

## BAIXO

### TD-009: `GEMINI_API_KEY` presente mas não utilizada
**Localização**: `.env`, `CLAUDE.md`
**Problema**: Variável de ambiente documentada mas código não a referencia. Cria confusão sobre se há funcionalidade usando Gemini.
**Solução**: Remover do `.env.example` (quando criado) e da documentação.
**Esforço**: 15min.

### TD-010: Coluna `tag` em `usuarios` é legacy mas ainda em uso pela API
**Localização**: `api/admin.py/atualizar_tag()`, `db/models.py`
**Problema**: O sistema de labels (`0002_labels.sql`) substituiu `tag`, mas o endpoint `/conversa/{telefone}/tag` ainda existe (marcado como "LEGACY"). A migration `0002` migrou os dados mas não removeu a coluna.
**Solução**: Após validação do sistema de labels em produção, deprecar e remover o endpoint legacy e a coluna.
**Esforço**: 2h (migration de remoção + remoção do endpoint).

---

## ALTO (adicionado 2026-05-22)

### TD-011: `_auto_unsnooze()` chamado em toda request GET /admin/conversas sem índice otimizado

**Localização**: `api/admin.py/_auto_unsnooze()`, chamada em `listar_conversas()` linha 235
**Problema**: A função executa um `UPDATE usuarios SET status_conversa='open', snoozed_until=NULL WHERE status_conversa='snoozed' AND snoozed_until <= NOW()` em **toda** chamada ao endpoint de listagem de conversas. O `status_conversa` é uma coluna `VARCHAR(20)` sem índice dedicado (índice composto `idx_historico_telefone_data` está em `historico_conversas`, não em `usuarios`). Se o dashboard fizer polling a cada 30s com múltiplos atendentes, isso significa dezenas de UPDATEs por minuto na tabela `usuarios`.
**Risco**: Em volumes maiores (>1000 usuários), contention de lock no MySQL por UPDATE frequente em tabela sem índice na coluna filtrada. Atualmente inócuo (volume baixo).
**Solução recomendada**: (a) Adicionar índice parcial em `status_conversa` — `CREATE INDEX idx_usuarios_status ON usuarios(status_conversa)`; (b) Mover `_auto_unsnooze()` para ser chamada apenas quando há snoozed conversations (verificar count antes do UPDATE) ou via job periódico (tarefa separada a cada 60s).
**Esforço**: 1h (migration + refatoração).

### TD-012: Trim de histórico usa `NOT IN` com subquery — problema de performance em MySQL

**Localização**: `api/webhook.py/_processar_mensagem()`, linhas 1055–1072
**Problema**: O código de poda de histórico (>50 mensagens) executa:
```python
ids_manter = [row.id for row in db.query(...).limit(50)]
db.query(HistoricoConversa).filter(~HistoricoConversa.id.in_(ids_manter)).delete()
```
O `NOT IN` com lista de IDs é conhecido por ter performance ruim no MySQL para listas grandes (o query planner não usa índice com `NOT IN` de forma eficiente). Com 50 IDs, ainda é aceitável, mas o padrão é frágil.
**Solução recomendada**: Substituir por DELETE com subquery de min id:
```sql
DELETE FROM historico_conversas WHERE telefone_usuario = ? AND id NOT IN (
    SELECT id FROM (SELECT id FROM historico_conversas WHERE telefone_usuario = ?
    ORDER BY criado_em DESC LIMIT 50) AS sub
)
```
Ou usar uma abordagem alternativa: buscar o ID mínimo dos 50 mais recentes e deletar todos os anteriores com `criado_em < min_criado_em`.
**Esforço**: 1-2h.

### TD-013: `_lock_do_telefone` — threading lock sem timeout no acquire (risco de starvation)

**Localização**: `api/webhook.py/tarefa_em_segundo_plano_ia()` e `_lock_do_telefone()`
**Problema**: O lock de per-telefone é adquirido com `with _lock_do_telefone(telefone):` sem timeout. Se um thread travado não liberar o lock (ex: NVIDIA NIM sem resposta por longo período), threads subsequentes do mesmo telefone ficam bloqueados indefinidamente.
**Solução recomendada**: Usar `lock.acquire(timeout=90)` com fallback de log e descarte da mensagem. Documentado em detalhe em ADR-010.
**Esforço**: 1-2h.

---

## MÉDIO (adicionado 2026-05-22)

### TD-014: `_ja_processada()` — TTL de limpeza de 20 minutos pode ser curto para retries da Meta

**Localização**: `api/webhook.py/_ja_processada()`, linha 778
**Problema**: A limpeza oportunista remove registros com `processada_em < NOW() - 1200s` (20 minutos). O comentário `_DEDUPE_TTL_SEGUNDOS = 600` (10 minutos) é o TTL de janela de retransmissão da Meta — o cleanup usa `_DEDUPE_TTL_SEGUNDOS * 2 = 1200s`. A Meta pode retentar mensagens por até 7 dias em caso de falha sistemática do servidor. Com TTL de 20 minutos, após restart do servidor + 20 minutos, a meta pode reenviar mensagens que seriam aceitas como novas (IDs expirados da tabela). O risco é baixo porque a Meta normalmente cobre retransmissão em janela de minutos para servidor disponível, mas em caso de indisponibilidade prolongada pode haver duplicatas.
**Solução recomendada**: Aumentar `_DEDUPE_TTL_SEGUNDOS` para 3600 (1h) e o cleanup para `_DEDUPE_TTL_SEGUNDOS * 24` (24h). O crescimento da tabela com 24h de retenção é aceitável (volume baixo).
**Esforço**: 15 minutos (mudança de constante + migration com índice).

### TD-015: `HistoricoConversa.intencao` com `String(30)` — margem estreita para valores atuais

**Localização**: `db/models.py`, `HistoricoConversa.intencao = Column(String(30), ...)`
**Problema**: Valores atuais gravados em `intencao`:
  - `"sub_servicos_barbearia"` = 20 chars ✓
  - `"devolucao_silenciosa"` = 20 chars ✓
  - `"sub_equipe_barbearia"` = 20 chars ✓
  - `"menu_resposta_direta"` = 20 chars ✓
  - `"menu_interativo"` = 15 chars ✓
  - Novos valores de intenção da IA podem exceder 30 chars se o prompt evoluir
**Risco**: `DataError` no MySQL se `intencao` tiver mais de 30 caracteres — truncado silenciosamente (MySQL modo não-strict) ou erro (modo strict). Modo strict é padrão desde MySQL 5.7.5.
**Solução recomendada**: Migrar coluna para `String(50)` — migration simples de ALTER TABLE.
**Esforço**: 30 min (migration SQL).

### TD-016: SSE `presence_changed` com status `"reativado"` não documentado no ADR-005

**Localização**: `api/admin.py/ativar_atendente()`, linhas 1597–1602
**Problema**: O endpoint `PATCH /admin/atendentes/{id}/ativar` publica um evento SSE:
```python
notificador.publicar({
    "tipo": "presence_changed",
    "atendente_id": a.id,
    "atendente_nome": a.nome,
    "status": "reativado",  # ← valor não listado no ADR-005
})
```
O ADR-005 define `presence_changed.status` como `"online | away | offline"`. O valor `"reativado"` é inválido segundo o contrato. O frontend pode não tratar esse valor e ignorar silenciosamente.
**Solução recomendada**: (a) Alterar para `"online"` no publicar, ou (b) criar evento de tipo distinto `atendente_reativado` com campo `atendente_nome`. Opção (a) é mais simples. Addendum registrado no ADR-005 abaixo.
**Esforço**: 5 minutos (1 linha de código).

---

## Resumo executivo

| ID | Prioridade | Impacto | Esforço |
|---|---|---|---|
| TD-001 | Crítico | Corrupção silenciosa de timestamps | 1-2h config |
| TD-002 | Crítico | Qualquer refatoração é arriscada | 8-16h |
| TD-003 | Alto | Impossível auditar estado do banco em produção | 2-3h |
| TD-004 | Alto | DoS por disco cheio | 1h |
| TD-005 | Alto | Race condition no cache de IA | 1-2h |
| TD-011 | Alto | Contention de lock por _auto_unsnooze() sem índice | 1h |
| TD-012 | Alto | Trim de histórico com NOT IN ineficiente | 1-2h |
| TD-013 | Alto | Threading lock sem timeout — starvation potencial | 1-2h |
| TD-006 | Médio | UX ruim após restart | 2-4h |
| TD-007 | Médio | Search lenta >50k msgs | 2-3h |
| TD-008 | Médio | Manutenibilidade frontend | 4-8h |
| TD-014 | Médio | Dedupe TTL curto — duplicatas em falha longa | 15min |
| TD-015 | Médio | intencao String(30) — margem estreita | 30min |
| TD-016 | Médio | SSE presence_changed com status "reativado" inválido | 5min |
| TD-009 | Baixo | Confusão na config | 15min |
| TD-010 | Baixo | API legacy acumulando | 2h |
