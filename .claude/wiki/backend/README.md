# backend/ — Diretório do Backend Developer

## Convenções
- **Owner:** `backend-agent`
- Relatórios técnicos, notas de implementação, checklists de migração
- Naming: `{slug}.md` ou `{feature}-{aspecto}.md`
- Registrar no `../index.md` ao criar nota relevante
- Código vai em `api/`, `services/`, `db/`, `core/`, `scripts/` (NÃO neste diretório)

## Áreas de responsabilidade
- `api/webhook.py` — entrypoint Meta WhatsApp
- `api/admin.py` — endpoints do dashboard híbrido
- `services/ai_service.py` — chamada NVIDIA NIM
- `services/whatsapp.py` — Meta Cloud API v19.0
- `services/notificador.py` — SSE/eventos
- `db/models.py` + `db/database.py` — schema e sessão SQLAlchemy
- `core/prompts.py` — system prompt da IA
- `core/respostas_canonicas.py` — FAQ pré-IA
- `core/config.py` — env vars
- `scripts/migrations/*.sql` — migrations manuais
