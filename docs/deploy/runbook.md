# Runbook de Deploy — Barbearia Bolshoi

Operação do bot WhatsApp + dashboard em produção. Cobre subir o serviço, o
**checklist de configuração de produção**, a **renovação do token WhatsApp** e
verificação de saúde. Complementa `docs/review/production-readiness-2026-06.md`.

---

## ✅ Checklist de configuração de PRODUÇÃO (antes do go-live)

No `.env` do servidor:

- [ ] **`META_APP_SECRET`** = App Secret real do app Meta (valida a assinatura HMAC do webhook).
- [ ] **Remover `ALLOW_UNSIGNED_WEBHOOK=1`** (ou setar `=0`). Com o secret presente, o boot exige assinatura válida. *(Se faltar o secret E o flag, o app NÃO sobe — guarda proposital em `main.py`.)*
- [ ] **`WHATSAPP_TOKEN`** = token **permanente** (System User), não o token temporário de sandbox (vence em 24h — ver abaixo).
- [ ] **`JWT_SECRET`** = 32+ bytes aleatórios (`python -c "import secrets; print(secrets.token_hex(32))"`).
- [ ] **`MODO_OPERACAO=hibrido`** se for usar o dashboard; senão `bot_only`.
- [ ] Servidor em **UTC** (o código já força `TZ=UTC`, mas confirme o relógio do host).
- [ ] MySQL com **`utf8mb4`** (nomes com emoji/acento) — ver P1-2 do relatório.
- [ ] **1 worker** apenas (estado em memória; ver P1-10). Não use `--workers 2+`.
- [ ] TLS/HTTPS no reverse-proxy (nginx/Caddy) na frente do app — a Meta exige `https` no webhook.

---

## Opção A — systemd (host Linux)

```bash
# 1. Código + venv
sudo mkdir -p /opt/barbearia && cd /opt/barbearia
git clone <REPO_URL> .
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt

# 2. Config
cp .env.example .env && nano .env   # preencher conforme o checklist acima

# 3. Banco: ver seção "Migrations (Alembic)" abaixo.
#    Banco do zero → bootstrap (create_all + `alembic stamp head` + seed_horarios).
#    Banco existente → `.venv/bin/alembic upgrade head`.

# 4. Serviço (auto-restart em crash)
sudo cp deploy/barbearia-bot.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now barbearia-bot
sudo systemctl status barbearia-bot
```

## Opção B — Docker

```bash
docker build -t barbearia-bot .
docker run -d --name barbearia-bot \
  --restart=always \
  --env-file .env \
  -p 8000:8000 \
  barbearia-bot
```

---

## Verificação de saúde

```bash
curl -s http://localhost:8000/health
# Esperado: {"status":"healthy","modo":"hibrido","timestamp":"..."}  (HTTP 200)
# Se o banco estiver fora: HTTP 503 {"detail":"database unavailable"}
```

- systemd: `journalctl -u barbearia-bot -f`
- Docker: `docker logs -f barbearia-bot` (e `docker inspect --format '{{.State.Health.Status}}' barbearia-bot`)

---

## Migrations (Alembic — ADR-014)

`db/models.py` é a fonte de verdade do schema. A baseline (`alembic/versions/ec0e2afe99be_*`)
é **vazia de propósito**: representa o schema que `create_all` constrói a partir dos models.

### Bootstrap de um banco MySQL do zero
Faça **uma vez** ao provisionar um banco novo:
```bash
# 1. Suba a app uma vez — o create_all do boot cria as tabelas a partir dos models
.venv/bin/python -c "import main"        # ou apenas inicie o serviço e pare em seguida
# 2. Carimbe a baseline (registra o ponto de partida, sem rodar SQL)
.venv/bin/alembic stamp head
# 3. Seed inicial
.venv/bin/python scripts/seed_horarios.py
```
> ⚠️ `alembic upgrade head` **sozinho NÃO cria as tabelas** (baseline vazia). O bootstrap é sempre
> `create_all` (no boot) **+** `alembic stamp head`. Depois disso, só deltas via `upgrade head`.

### Deploy normal (banco já com baseline carimbada)
Antes de subir/reiniciar a aplicação:
```bash
.venv/bin/alembic upgrade head   # idempotente; aplica migrations pendentes (nada se já no head)
```

### Mudar o schema (workflow de desenvolvimento)
```bash
# 1. Edite db/models.py
# 2. Gere a migration a partir do diff models↔banco:
alembic revision --autogenerate -m "descricao_da_mudanca"
# 3. REVISE o script em alembic/versions/ (autogenerate erra charset/ENUM/Numeric no MySQL)
# 4. Aplique:
alembic upgrade head
# 5. Commite db/models.py + o arquivo de versão juntos
```
SQL manual em `scripts/migrations/` foi descontinuado — está em `scripts/archive/migrations_legacy/`.

---

## 🔑 Renovação do token WhatsApp (P0-2)

**Sintoma de token vencido:** clientes mandam mensagem e o bot **não responde**.
Nos logs aparece o alerta distinto:

```
WHATSAPP_TOKEN EXPIRADO OU INVÁLIDO (401) ... renove o WHATSAPP_TOKEN no .env e reinicie.
```

> **Configure um alerta** (ex.: grep desse texto no journald / Sentry) para ser avisado
> automaticamente — sem isso, só se descobre quando um cliente reclama.

### Solução definitiva: token permanente (recomendado)
O token de **sandbox** vence a cada 24h. Para produção, gere um **System User token**
permanente em *Meta for Developers → Business Settings → System Users → Generate Token*
(escopos `whatsapp_business_messaging`, `whatsapp_business_management`). Cole em
`WHATSAPP_TOKEN` e reinicie. Esse token não expira em 24h.

### Renovação manual (enquanto não migrar)
```bash
# 1. Gere o novo token no painel Meta
# 2. Atualize o .env
nano /opt/barbearia/.env       # WHATSAPP_TOKEN=<novo_token>
# 3. Reinicie
sudo systemctl restart barbearia-bot     # (ou: docker restart barbearia-bot)
# 4. Valide
curl -s http://localhost:8000/health
```

---

## Notas

- **Horários / feriados:** edite via o dashboard/endpoint `PATCH /admin/horarios/{dia_semana}`
  (0=segunda … 6=domingo; campos `abertura`/`fechamento` "HH:MM" ou `fechado=true`).
  A canônica de horário e a IA passam a refletir a mudança na hora. Feriado em data móvel
  (Carnaval) ainda exige setar `fechado` no dia da semana correspondente (exceções por data = fast-follow).
- **LGPD:** o cliente pode pedir exclusão digitando "apagar meus dados"; a equipe cumpre via
  `DELETE /admin/cliente/{telefone}` (apaga histórico, labels, notas e menções).
- **`erro_ia_debug.txt`** fica em disco e contém logs (com PII já mascarada/truncada). Em deploy
  sem volume persistente, é perdido em redeploy — considere enviar logs pra um serviço externo (P1).

---

## Manutenção periódica (P2-3)

A limpeza oportunista (1% das mensagens) não é determinística. Rode `scripts/limpeza.py`
por cron/timer para garantir a limpeza:

```bash
# Só dedupe (mensagens_processadas > 2 dias) — seguro, garbage puro:
python scripts/limpeza.py

# Também minimizar dados pessoais: purga histórico > 180 dias (opt-in, LGPD):
python scripts/limpeza.py --historico-dias 180

# Ver o que seria removido sem deletar:
python scripts/limpeza.py --dry-run
```

Cron diário às 3h (systemd timer ou crontab):

```cron
0 3 * * *  cd /opt/barbearia-bot && ./venv/bin/python scripts/limpeza.py >> /var/log/barbearia-limpeza.log 2>&1
```
