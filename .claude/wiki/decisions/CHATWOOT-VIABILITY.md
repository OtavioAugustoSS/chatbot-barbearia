# CHATWOOT-VIABILITY: Análise de Viabilidade Técnica
Data: 2026-05-21
Autor: architect-agent
Contexto: Avaliação das 4 funcionalidades inspiradas no Chatwoot para o stack atual

## Stack de referência
FastAPI + SQLAlchemy + MySQL via pymysql + vanilla JS (sem framework) + SSE em memória

---

## 1. RBAC Supervisor/Agent

**Descrição**: Distinguir dois papéis — `supervisor` (pode ver tudo, reatribuir, ver analytics, gerenciar atendentes) e `agent` (só pode ver/responder conversas atribuídas a si ou na fila).

### Análise técnica

**O que precisa mudar no backend:**

1. Adicionar coluna `role ENUM('supervisor', 'agent') NOT NULL DEFAULT 'agent'` em `atendentes`
2. Migration: `scripts/migrations/0009_add_role_atendente.sql`
3. Atualizar `Atendente` model em `db/models.py`
4. Criar decorator/dependency `supervisor_required` em `api/auth.py`:
   ```python
   def supervisor_atual(me: Atendente = Depends(atendente_atual)) -> Atendente:
       if me.role != 'supervisor':
           raise HTTPException(403, "Acesso restrito a supervisores")
       return me
   ```
5. Aplicar guard nos endpoints:
   - `POST /admin/atendentes` — supervisor only
   - `PATCH /admin/atendentes/{id}/desativar` — supervisor only
   - `GET /admin/analytics` (futuro) — supervisor only
   - `POST /admin/conversas/bulk` — supervisor only (atribuição em massa)
   - Labels CRUD global — supervisor only
6. `GET /admin/conversas` — agents veem apenas status `open`/`meus`; supervisors veem tudo
7. `criar_token()` deve incluir `role` no payload JWT para o frontend poder esconder UI

**O que precisa mudar no frontend:**

8. `login.html` → após login, salvar `role` do JWT decoded no `localStorage`
9. `index.html` / `settings.html` → esconder elementos de UI para `agent` (ex: botão "Novo Atendente", filtro "Todas")
10. `api.js` → incluir `role` nas requisições que precisam (já está no JWT, não precisa enviar separado)

**Viabilidade**: Alta — é uma extensão direta do sistema de auth existente. O `atendente_atual` já valida atividade; adicionar validação de role é trivial.

**Esforço estimado**: 8-12 horas
- 2h: migration + model + token
- 3h: guards nos endpoints backend
- 3h: frontend (esconder UI por role)
- 2h: testes manuais de cada endpoint com os dois papéis
- 1h: documentação

**Dependências**: Nenhuma — pode ser feito isoladamente.

**Risco**: Baixo. O único risco é esquecer de guardar um endpoint novo — revisão de código resolve.

---

## 2. Analytics Dashboard

**Descrição**: Métricas agregadas visíveis para supervisors: volume de mensagens por dia, tempo médio de atendimento, conversas por atendente, taxa de handoff IA → humano.

### Análise técnica

**O que precisa mudar no backend:**

1. Novo endpoint `GET /admin/analytics` com parâmetros `from_date`, `to_date` (ISO8601)
2. Queries de agregação via SQLAlchemy:

```python
# Volume por dia
db.query(
    func.date(HistoricoConversa.criado_em).label("dia"),
    func.count(HistoricoConversa.id).label("total")
).filter(range).group_by("dia").all()

# Handoffs (IA → humano)
db.query(func.count(HistoricoConversa.id)).filter(
    HistoricoConversa.intencao.in_(["chamar_recepcao", "transbordo_falha"])
).scalar()

# Conversas por atendente
db.query(
    Atendente.nome,
    func.count(HistoricoConversa.id)
).join(HistoricoConversa, HistoricoConversa.atendente_id == Atendente.id
).filter(range).group_by(Atendente.id).all()

# Tempo médio de atendimento: requer colunas transbordo_em e "devolvido_em" (não existe ainda)
```

3. **Gap crítico**: não existe coluna `devolvido_em` em `usuarios` — calcular tempo médio de atendimento requer rastrear quando o atendente devolveu. Alternativa aproximada: diferença entre maior e menor `HistoricoConversa.criado_em` com `origem='humano'` por `telefone+atendente_id`.

**O que precisa mudar no frontend:**

4. Nova seção em `settings.html` ou nova página `analytics.html`
5. Gráficos: vanilla JS pode usar Chart.js via CDN (biblioteca sem bundler, aceita sem novo ADR) ou tabelas HTML simples. Recomendação: tabelas HTML no MVP, Chart.js quando houver demanda visual.

**Performance das queries:**

Com <5k usuários e <100k mensagens: queries em <1s com os índices existentes (`idx_historico_telefone_data`). Para range de 30 dias: estimado <500ms. Sem necessidade de materialized views ou cache.

**Viabilidade**: Alta para métricas básicas (volume, handoffs, por atendente). Média para tempo médio de atendimento (requer nova coluna ou cálculo aproximado).

**Esforço estimado**: 10-16 horas
- 2h: migration `devolvido_em` (se quiser tempo real de atendimento)
- 4h: endpoint analytics + queries
- 4h: frontend (tabelas + gráficos simples)
- 2h: guard de supervisor
- 2-4h: refinamento e testes

**Dependências**: RBAC (item 1) para o guard de supervisor. Pode ser feito antes sem guard e adicionar depois.

**Risco**: Médio. Queries de agregação sobre tabelas grandes sem índices adequados podem ser lentas. Os índices existentes cobrem o caso principal.

---

## 3. Automation Rules (Regras de Automação)

**Descrição**: Regras configuráveis do tipo "se X então Y" — ex: "se conversa ficou sem resposta por 30min, mudar status para pending" ou "se intencao=chamar_recepcao, atribuir a atendente específico".

### Análise técnica

**Abordagem A: Job periódico (polling)**

Implementação mais simples no stack atual:

```python
# services/automation.py
import threading, time

def _run_automation_loop():
    while True:
        time.sleep(60)  # verifica a cada 60s
        _aplicar_regras()

def _aplicar_regras():
    db = SessionLocal()
    try:
        # Ex: conversas open sem resposta por >30min → pending
        limite = datetime.now(timezone.utc) - timedelta(minutes=30)
        db.query(Usuario).filter(
            Usuario.status_conversa == 'open',
            Usuario.data_ultima_interacao < limite,
            Usuario.bot_ativo == True,
        ).update({"status_conversa": "pending"}, synchronize_session=False)
        db.commit()
    finally:
        db.close()

# Iniciado em main.py via threading.Thread(target=_run_automation_loop, daemon=True)
```

**Vantagens**: sem dependência externa, sem Celery, sem Redis.
**Desvantagens**: precisão de 60s (não tempo real), loop daemon morre em restart.

**Abordagem B: Trigger de banco de dados MySQL**

```sql
CREATE EVENT IF NOT EXISTS auto_pending_sem_resposta
ON SCHEDULE EVERY 5 MINUTE
DO
  UPDATE usuarios
  SET status_conversa = 'pending'
  WHERE status_conversa = 'open'
    AND data_ultima_interacao < NOW() - INTERVAL 30 MINUTE
    AND bot_ativo = TRUE;
```

**Vantagens**: independente do servidor Python, não afetado por restart.
**Desvantagens**: requer `event_scheduler=ON` no MySQL; lógica de negócio no banco dificulta manutenção; não publica SSE (frontend precisa fazer polling ou re-fetch).

**Abordagem recomendada**: A (loop periódico em thread daemon) para MVP. Regras configuráveis armazenadas em tabela `automation_rules` (JSON com condições e ações), avaliadas pelo loop.

**Schema proposto para configurabilidade:**
```sql
CREATE TABLE automation_rules (
    id INT AUTO_INCREMENT PRIMARY KEY,
    nome VARCHAR(100) NOT NULL,
    ativo BOOLEAN NOT NULL DEFAULT TRUE,
    condicao JSON NOT NULL,   -- {"campo": "data_ultima_interacao", "op": "older_than", "valor": 30}
    acao JSON NOT NULL,       -- {"tipo": "set_status", "valor": "pending"}
    criado_por INT NULL REFERENCES atendentes(id)
);
```

**Viabilidade**: Alta para regras simples (mudança de status, atribuição automática). Média para regras complexas com múltiplas condições.

**Esforço estimado**: 16-24 horas
- 4h: design do schema de regras + migration
- 6h: engine de avaliação de regras (parser de JSON de condição + ação)
- 4h: endpoints CRUD de regras (admin)
- 4h: frontend para configurar regras
- 2-4h: testes e debugging

**Risco**: Alto. O maior risco é a engine de regras ter bugs silenciosos que mudam status de conversas incorretamente em produção. Recomendação: implementar primeiro com regra hardcoded (sem configurabilidade) e só depois tornar configurável.

---

## 4. Audit Trail

**Descrição**: Log imutável de todas as ações realizadas por atendentes — quem assumiu, quem devolveu, quem mudou status, quem editou nota, quem adicionou label.

### Análise técnica

**Opção A: Tabela nova `audit_log`**

```sql
CREATE TABLE audit_log (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    atendente_id INT NULL REFERENCES atendentes(id) ON DELETE SET NULL,
    acao VARCHAR(50) NOT NULL,  -- "assumiu", "devolveu", "status_alterado", "nota_criada", etc.
    telefone_usuario VARCHAR(20) NULL,
    parametros JSON NULL,       -- dados adicionais (ex: {"de": "open", "para": "resolved"})
    criado_em DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_audit_atendente (atendente_id),
    INDEX idx_audit_telefone (telefone_usuario),
    INDEX idx_audit_acao (acao),
    INDEX idx_audit_criado_em (criado_em)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
```

**Vantagens**: tabela dedicada, não mistura com histórico de conversas, fácil de consultar por ação, por atendente ou por conversa.
**Desvantagens**: nova tabela, novo endpoint, esforço de instrumentar cada ponto de ação.

**Opção B: Append em `historico_conversas`**

Já existe um padrão emergente: transferência de conversa grava em `historico_conversas` com `intencao="transferencia"` e texto `"[Sistema] Conversa transferida de X para Y"`. Poderia expandir esse padrão para mais eventos.

**Vantagens**: sem nova tabela, sem novo endpoint (frontend já lê histórico).
**Desvantagens**: mistura mensagens reais com eventos de sistema; query para extrair apenas audit events requer filtro em `intencao`; coluna `intencao` é `VARCHAR(30)` — curta para alguns casos.

**Recomendação**: Opção A (`audit_log` dedicada). O padrão de historico_conversas para eventos de sistema já criou inconsistência (o frontend renderiza `[Sistema] Conversa transferida` como mensagem normal). Uma tabela dedicada é mais limpa e escalável.

**Pontos de instrumentação necessários** (em `api/admin.py`):
- `POST /admin/assumir/{telefone}`
- `POST /admin/devolver/{telefone}`
- `PATCH /admin/conversa/{telefone}/status`
- `POST /admin/conversa/{telefone}/atribuir`
- `POST /admin/notas/{telefone}` / `PATCH /admin/notas/{nota_id}` / `DELETE /admin/notas/{nota_id}`
- `POST /admin/conversas/bulk`
- `POST /admin/atendentes` / `PATCH /admin/atendentes/{id}/desativar|ativar`

**Helper proposto:**
```python
def _audit(db, atendente_id, acao, telefone=None, **kwargs):
    db.execute(text(
        "INSERT INTO audit_log (atendente_id, acao, telefone_usuario, parametros) "
        "VALUES (:aid, :acao, :tel, :params)"
    ), {"aid": atendente_id, "acao": acao, "tel": telefone, 
        "params": json.dumps(kwargs) if kwargs else None})
```

**Endpoint de consulta:**
- `GET /admin/audit?telefone=X&atendente_id=Y&from=ISO&to=ISO&limit=100` (supervisor only)

**Viabilidade**: Alta. Tabela simples com INSERTs em cada ação — sem lógica complexa.

**Esforço estimado**: 8-14 horas
- 2h: migration + model
- 4h: instrumentação dos endpoints (muitos pontos mas mecânico)
- 2h: endpoint de consulta
- 2h: frontend (tabela de auditoria em settings.html)
- 1-3h: testes

**Risco**: Baixo. O único risco é esquecer de instrumentar um endpoint — inspeção do código resolve.

---

## Tabela Resumo

| Funcionalidade | Viabilidade | Esforço | Risco | Bloqueadores |
|---|---|---|---|---|
| RBAC supervisor/agent | Alta | 8-12h | Baixo | Nenhum |
| Analytics dashboard | Alta (básico) / Média (tempo atendimento) | 10-16h | Médio (queries perf) | RBAC recomendado antes |
| Automation rules | Alta (simples) / Média (configurável) | 16-24h | Alto (bugs silenciosos) | Recomendado hardcoded primeiro |
| Audit trail | Alta | 8-14h | Baixo | RBAC para guard do endpoint |

## Ordem de implementação recomendada

1. **Audit trail** — baixo risco, alta utilidade imediata, não bloqueia nada
2. **RBAC** — desbloqueia os demais com guard de supervisor
3. **Analytics** — depende de RBAC; útil para PO validar eficácia do bot
4. **Automation rules** — maior esforço e risco; só implementar após estabilidade dos anteriores

## Nota sobre o stack

Todas as 4 funcionalidades são viáveis no stack FastAPI + SQLAlchemy + MySQL + vanilla JS sem necessidade de:
- Celery / Redis (Automation pode ser thread daemon)
- Framework JS (tabelas HTML são suficientes para analytics MVP)
- Novo serviço externo
- Mudança de arquitetura principal

O maior risco técnico é a Automation Rules, que pode evoluir para um "mini motor de regras" difícil de manter. Recomenda-se começar com 2-3 regras hardcoded antes de tornar configurável.
