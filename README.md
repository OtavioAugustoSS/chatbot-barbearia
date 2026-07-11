# 💈 Chatbot Inteligente — Barbearia Bolshoi

O Recepcionista Digital Oficial da Barbearia Bolshoi via WhatsApp, utilizando Inteligência Artificial (**NVIDIA NIM — Llama 3.1 70B**) e FastAPI.

## 📌 Visão Geral do Projeto

O bot atua como um concierge digital, construído em **Python (FastAPI)** com **MySQL** e conectado à **Meta Cloud API (WhatsApp)**.

1. **FAQ Inteligente:** responde perguntas sobre preços, horários e barbeiros lendo direto do banco de dados (evita alucinação). Perguntas frequentes têm resposta canônica por regex, sem custo de IA.
2. **Redirecionamento rígido:** o bot **nunca agenda** — sempre envia o link oficial do AppBarber.
3. **Triagem e transbordo humano:** ao detectar necessidade de atendimento, desativa o bot (`bot_ativo = False`) e, no modo híbrido, coloca o cliente na fila do dashboard de atendentes.

**Modos de operação** (`MODO_OPERACAO`):
- `bot_only` — IA responde tudo sozinha.
- `hibrido` — IA + dashboard de atendentes em `/static/admin/` (login JWT, SSE em tempo real, RBAC admin/atendente).

---

## ⚡ Rodar AGORA, sem configurar nada (modo dev)

Sem `.env`, o sistema sobe em **modo desenvolvimento** com tudo simulado:

```bash
pip install -r requirements.txt
python main.py
```

O boot mostra um banner com o estado de cada subsistema. Você ganha:

| Recurso | Em modo dev | URL |
|---|---|---|
| Banco | SQLite local `./dev.db` com dados demo | — |
| Simulador de WhatsApp | Chat no navegador com menus clicáveis, passando pelo pipeline real do bot | http://localhost:8000/dev/simulador |
| Dashboard do atendente | login `admin` / senha `admin123` | http://localhost:8000/static/admin/login.html |
| IA | Resposta de demonstração (sem chamada externa) | — |

Fluxo de teste sugerido: abra o simulador, mande `oi` (menu interativo), clique nas opções, pergunte algo livre (resposta demo da IA), toque em *Falar c/ Atendente* e atenda a conversa pelo dashboard — a resposta do atendente aparece no simulador.

Quando o `.env` real for preenchido, os subsistemas correspondentes ligam automaticamente e o simulador deixa de ser montado. Com `APP_ENV=production`, qualquer credencial faltante **aborta o boot** com erro claro.

---

## 🛠 Pré-requisitos para produção (WhatsApp real)

### 1. Conta Meta for Developers (WhatsApp)
- Anote o **Phone Number ID** (`WHATSAPP_PHONE_ID`).
- Gere um **token de acesso** (`WHATSAPP_TOKEN`) — o temporário dura 24h; em produção use token permanente de System User.
- Pegue o **App Secret** (`META_APP_SECRET`) para validação HMAC do webhook.

### 2. Chave NVIDIA NIM (IA)
- Gere em [build.nvidia.com](https://build.nvidia.com) e preencha `NVIDIA_API_KEY`.
- O modelo usado é `meta/llama-3.1-70b-instruct` via API compatível com OpenAI.

### 3. Banco de Dados MySQL
- MySQL com charset `utf8mb4`. Preencha `DB_USER/DB_PASS/DB_HOST/DB_NAME` (ou `DB_URL`).

---

## 🚀 Passo a passo (produção/integração)

### Passo 1: Configurar o `.env`
Copie `.env.example` para `.env` e preencha os valores (o arquivo é comentado).

### Passo 2: Instalar dependências
```bash
pip install -r requirements.txt
```

### Passo 3: Banco e migrations (Alembic)
Banco novo: o boot cria as tabelas via `create_all`; em seguida registre a baseline:
```bash
alembic stamp head
python -m scripts.seed_horarios   # popula horários de funcionamento
```
Banco existente (deploys seguintes):
```bash
alembic upgrade head
```
Qualquer mudança de schema é feita em `db/models.py` + `alembic revision --autogenerate` (ver `CLAUDE.md` e ADR-014).

### Passo 4: Túnel público (ngrok)
```bash
ngrok http 8000
```

### Passo 5: Subir o servidor
```bash
python main.py
```

### Passo 6: Registrar o webhook na Meta
Meta for Developers → WhatsApp → Configuration:
- **Callback URL:** `https://SEU-TUNEL/webhook`
- **Verify token:** o valor de `WEBHOOK_VERIFY_TOKEN` do seu `.env`
- Em "Webhook fields", inscreva-se em **messages**.

### Modo híbrido (dashboard)
```bash
# no .env: MODO_OPERACAO=hibrido e JWT_SECRET preenchido
python -m scripts.criar_atendente --admin   # primeiro operador (perfil admin)
```
Dashboard em `/static/admin/login.html`. Perfis: `admin` (gerencia atendentes, horários e exclusão LGPD) e `atendente` (atende conversas).

---

## 🧪 Testes

```bash
pip install -r requirements-dev.txt
pytest
```
A suíte roda 100% em SQLite in-memory, sem rede. Para smoke de integração contra MySQL real: `python -m scripts.smoke_integracao`.

## 📱 Regras de negócio testáveis no WhatsApp

1. **Dúvida livre:** "Quanto custa o corte?" → IA responde com preços do banco.
2. **Transbordo:** "Preciso falar com um humano" → `bot_ativo = False`; no híbrido, entra na fila do dashboard.
3. **Agendamento:** qualquer pedido de marcação devolve o link do AppBarber — o bot nunca agenda.

### 🤫 Comandos de staff (via WhatsApp)
Telefones em `ADMIN_PHONES` podem enviar:
- **`!reiniciar`** — reativa o bot e limpa o histórico da própria conversa (útil em testes).
- **`!status`** — mostra o estado atual da conversa (bot ativo, atendente, histórico).
