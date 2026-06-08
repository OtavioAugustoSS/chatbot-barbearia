# Confirmação de Prontidão — Bot WhatsApp + Dashboard · Barbearia Bolshoi

**Data:** 2026-06-08 · **Tipo:** verificação de prontidão funcional ("Confiança + Cobertura").
**Método:** smoke test ao vivo contra o **MySQL real** (sem chamar o NIM → custo zero) + checagem de drift de schema (Alembic) + triagem honesta dos gaps em 1ª mão + cobertura de testes dos fluxos core. **Deploy fora de escopo** (decisão do dono).

> Continuação da auditoria `production-readiness-2026-06.md`. Todos os P0/P1/P2 não-deploy já tinham sido fechados; esta rodada **confirma que funciona** e cobre o que faltava de teste.

---

## 1. Veredito

**🟢 GO para o modo dev/test — funciona de ponta a ponta.** O app sobe contra o MySQL real, todos os endpoints de leitura/auth respondem, e o pipeline do bot (boas-vindas, menu interativo, FAQ canônica, handoff) funciona **sem acionar a IA** nos caminhos determinísticos. A suíte subiu de 94 → **119 testes verdes**, cobrindo agora os fluxos core que estavam sem teste.

**Para produção:** falta apenas o que o dono deferiu (token permanente Meta, `META_APP_SECRET`, hospedagem+TLS) + uma **reconciliação de schema** (hand-review do Alembic, ver §4) — nenhum bug de runtime.

---

## 2. Smoke test ao vivo (TestClient sobre o MySQL real)

| Verificação | Resultado |
|---|---|
| Boot do app contra MySQL real (gates de env, `create_all`) | 🟢 sobe sem erro |
| `GET /health` (testa `SELECT 1` no DB) | 🟢 200 `{status:healthy}` |
| `GET /webhook` (handshake de verificação Meta) | 🟢 devolve o challenge |
| `POST /admin/login` (credencial inválida) | 🟢 401 |
| `GET /admin/conversas` sem token | 🟢 401 |
| `POST /admin/login` real → JWT → `GET /admin/conversas` autenticado | 🟢 200 |
| `GET /admin/horarios` (seed presente no banco) | 🟢 200, 7 dias |
| `POST /webhook` 1º contato → menu de boas-vindas (lista interativa) | 🟢 sem NIM |
| `POST /webhook` "qual o horário?" → FAQ canônica de horário | 🟢 sem NIM |

Todos os dados de teste criados foram removidos. **Nenhuma chamada ao NIM** (custo zero, blindado no teste).

---

## 3. Cobertura de testes (94 → 119)

Fluxos **core** que estavam sem teste agora cobertos:

| Área | Testes novos |
|---|---|
| Menu interativo + sub-fluxos (`test_menu_flows.py`) | 10 — 1º contato, MENU_HORARIO/PAGAMENTO/AGENDAMENTO, serviços do DB, voltar-ao-menu, pedido de menu, handoff via MENU_RECEPCAO, e canônica de horário lendo do banco |
| Endpoints admin (`test_admin_coverage.py`) | 12 — máquina de status (resolved/snooze/reabrir), transferência (+403), bulk atribuir/snooze/label, canned CRUD, label edit/delete, nota edit/delete |
| Auto-reativação do bot (`test_auto_reativacao.py`) | 3 — reativa após timeout; não reativa se recente; híbrido não reativa com atendente |

Cobertura de endpoints subiu de ~37% para os fluxos de maior risco. Restam sem teste endpoints secundários (search, views/CRUD, mentions inbox, atendentes lifecycle, media upload) — baixo risco, listados como follow-up.

---

## 4. Drift de schema (Alembic) — achado honesto, **não é bug**

`alembic check` contra o banco vivo acusa divergências entre os `db/models.py` (tipos genéricos do SQLAlchemy) e o banco (construído organicamente via SQL manual com **tipos nativos do MySQL**). **Nenhuma afeta o runtime** — o app usa os models, que mapeiam corretamente para as colunas/valores reais. Categorização:

| Categoria | Exemplos | Ação |
|---|---|---|
| **Representacional (benigno)** | `status_conversa` ENUM↔String(20), `data_ultima_interacao`/`criado_em` TIMESTAMP↔DateTime, `filtros_salvos.criterios` JSON↔Text | Aceitar — mesmos valores, comportamento idêntico |
| **Cosmético de naming** | índices `idx_*`→`ix_*` (naming_convention), `ix_*_id` redundante em PK (`index=True` no PK) | Aceitar — sem efeito funcional |
| **Falso-positivo PERIGOSO** | `historico_conversas` `ID`↔`id` (MySQL é case-insensitive → mesma coluna; autogenerate cru faria drop/recreate = **perda de dados**) | **NUNCA aplicar o autogenerate cru** |
| **Real mas benigno** | coluna morta `usuarios.estado_atual` (não referenciada em lugar nenhum), nullable mismatches (`servicos.tempo_estimado_minutos`, `usuario_labels.atribuido_em`) | Limpar numa migration revisada à mão |

**Recomendação pré-prod:** uma migration de **alinhamento revisada à mão** (converter os tipos nativos para bater com os models OU alinhar os models aos tipos nativos do banco; dropar `estado_atual`; ajustar nullables) — **removendo** os ops perigosos (o swap `ID`/`id`). Isso é o passo final do P1-3 antes de confiar 100% no autogenerate. **Não é bloqueador de dev/test** (o schema funciona).

---

## 5. Triagem dos "gaps" apontados (real vs já-feito)

Exploração inicial sugeriu vários gaps; **a maioria estava DESATUALIZADA** (docs de user-story antigos). Verificado em 1ª mão:

| Item | Veredito |
|---|---|
| Filtros de estado não passam parâmetro | ✅ **JÁ-FEITO** (`app.js:850` `getConversasFiltradas`) |
| Bulk bar sem botões | ✅ **JÁ-FEITO** (resolver/snooze/atribuir/label com listeners) |
| Snooze ainda usa `prompt()` | ✅ **JÁ-FEITO** (`abrirModalSnooze` é modal real) |
| Settings 409 quebrado | ✅ **JÁ-FEITO** (`settings.html` usa `e.status === 409`) |
| FAQ canônica de horário não lê do banco no webhook | 🔧 **GAP-REAL → CORRIGIDO** (passava sem `db`; agora `db=db`, completa P0-4) |
| `mensagens_nao_lidas` não populado p/ conversas assumidas | ⏳ **REAL, deferido** — precisa de rastreio de "última leitura" (mecanismo inexistente); maior do que parece |
| UI de editar/excluir nota | ⏳ **REAL menor, deferido** — backend tem PATCH/DELETE; falta o botão na UI (conveniência) |
| Botões "mortos" (emoji picker, favoritar) | ⏳ cosmético, deferido |
| Auto-assign no handoff / msg pós-reativação (GAP-06/08) | 🟡 **decisão de PO**, deferido |

---

## 6. Status por área

| Área | Status | Nota |
|---|---|---|
| Bot / pipeline pré-IA | 🟢 | dedup, rate-limit, lock, boas-vindas, menu, saudação, FAQ canônica — testados e verificados ao vivo |
| IA / resiliência | 🟢 | handoff em falha, circuit breaker, anti-agendamento, guard do Fred |
| Admin / SSE / auth | 🟢 | login/JWT, assumir/devolver/enviar/bulk, status, transferência, canned, labels, notas — cobertos |
| Dados / migrations | 🟡 | funciona; falta alinhamento de schema revisado à mão (§4) antes de prod |
| a11y | 🟢 | contraste AA (tema claro), focus-trap nos modais (verificado no browser) |
| Segurança / LGPD | 🟢 | consentimento, apagar dados, PII mascarada, verify-token sem fallback, /presence no body |
| Deploy | ⚪ | fora de escopo — Dockerfile/systemd/runbook prontos; falta config de prod |

---

## 7. Follow-ups (não bloqueiam dev/test)

1. **Pré-prod:** migration de alinhamento de schema revisada à mão (§4) + itens de deploy.
2. **Produto (PO):** GAP-06/08, `mensagens_nao_lidas`, UI editar/excluir nota, botões mortos.
3. **Testes (opcional):** endpoints secundários sem cobertura (search, views, mentions inbox, atendentes lifecycle, media upload).

---

## 8. Conclusão

O sistema está **completo e funcional no modo dev/test**, com o pipeline do bot e o dashboard verificados ponta-a-ponta contra o ambiente real, **119 testes verdes**, e um único item técnico real pendente (alinhamento de schema) que é **pré-prod, não runtime**. Pronto para uso, testes e melhorias; o caminho para produção está claro e documentado.
