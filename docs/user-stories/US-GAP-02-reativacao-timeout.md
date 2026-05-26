---
id: US-GAP-02
area: Fluxo de Handoff
origem: BR-011 (decisao PO sobre GAP-08, 2026-05-22)
data_formalizacao: 2026-05-22
status_backend: PENDENTE
status_frontend: N/A (logica de backend/webhook)
---

# US-GAP-02: Mensagem de Contexto apos Reativacao por Timeout

## User Story

**Como** cliente que pediu atendimento humano e nao foi atendido dentro do periodo de espera,
**Quero** receber uma mensagem de contexto na primeira interacao apos o bot reativar automaticamente,
**Para** entender que o atendimento humano nao foi possivel e que o bot esta disponivel novamente.

---

## Contexto

Quando um cliente solicita falar com a recepcao (`chamar_recepcao`), o bot entra em modo de espera (`bot_ativo=False`, `aguardando_humano=True`). Se nenhum atendente assumir dentro de `BOT_REATIVAR_APOS_HORAS` horas (default: 24h), o bot e reativado automaticamente na proxima mensagem do cliente.

Atualmente, essa reativacao e silenciosa: o bot responde como se nada tivesse acontecido, sem contexto sobre o periodo de espera. Isso gera confusao para o cliente que nao entende por que o humano nao atendeu.

Esta story cobre APENAS a reativacao por timeout — nao a reativacao via `POST /admin/devolver` (que ja tem mensagem de despedida enviada pelo atendente via BR-004).

---

## Criterios de Aceite

- [ ] CA-01: O sistema distingue reativacao por timeout (`BOT_REATIVAR_APOS_HORAS` expirou) de reativacao por `devolver` (atendente devolveu)
- [ ] CA-02: Na primeira mensagem apos reativacao por timeout, a resposta do bot e prefixada com frase de contexto: "Lamentamos nao ter conseguido conectar voce com nossa recepcao anteriormente. Estou aqui para te ajudar!"
- [ ] CA-03: A frase de contexto aparece apenas UMA vez — somente na primeira interacao apos a reativacao por timeout
- [ ] CA-04: Nas interacoes seguintes, o bot responde normalmente sem a frase de contexto
- [ ] CA-05: Reativacao via `POST /admin/devolver` NAO exibe a frase de contexto (atendente ja enviou despedida)
- [ ] CA-06: Reativacao via `!reiniciar` (comando de staff) NAO exibe a frase de contexto
- [ ] CA-07: A frase de contexto e prefixada ANTES da resposta normal do bot (nao substitui a resposta)

---

## Implementacao tecnica necessaria

### Opcao A — Campo booleano em Usuario (recomendada)

Adicionar campo `reativado_por_timeout` (Boolean, default False) na tabela `usuarios`.

Fluxo:
1. Quando auto-reativacao por timeout ocorre em `api/webhook.py`: setar `reativado_por_timeout=True`
2. Na proxima chamada da IA: detectar `reativado_por_timeout=True`, prefixar resposta, setar `reativado_por_timeout=False`
3. `POST /admin/devolver`: nao toca `reativado_por_timeout`
4. `!reiniciar`: nao toca `reativado_por_timeout`

### Opcao B — Verificacao via timestamps (sem migration)

Verificar se `(bot_desativado_em != None) AND (aguardando_humano era True antes de reativar) AND (atendente_id e NULL)`. Se sim, inferir que foi timeout e nao `devolver`.

**Migration necessaria (Opcao A):**
```sql
-- scripts/migrations/US-GAP-02-reativacao-timeout.sql
ALTER TABLE usuarios ADD COLUMN reativado_por_timeout BOOLEAN NOT NULL DEFAULT FALSE;
```

---

## Arquivos a modificar

- `db/models.py`: adicionar campo `reativado_por_timeout` a classe `Usuario` (Opcao A)
- `api/webhook.py`: logica de auto-reativacao — setar flag + prefixo na resposta
- `scripts/migrations/US-GAP-02-reativacao-timeout.sql`: migration do campo

---

## Relacionamentos

- Depende de: BR-004 (handoff triggers), BR-011 (decisao GAP-08)
- Relacionado a: US-GAP-01 (reativar atendente)
- Nao conflita com: `POST /admin/devolver` (logica separada)

---

## Notas de produto

- A frase "Lamentamos nao ter conseguido conectar voce com nossa recepcao anteriormente" e tom de empatia — adequado para barbearia premium
- Nao usar "desculpe" ou "foi um erro" — pode implicar falha tecnica quando na verdade foi ausencia de atendente
- A frase deve usar `<br><br>` para separar do conteudo da resposta: `"Lamentamos nao ter conseguido conectar voce com nossa recepcao anteriormente. Estou aqui para te ajudar!<br><br>" + resposta_normal`
