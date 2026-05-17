## Handoff: dev-agent → qa-agent

**Tarefa**: Correções pós-QA — avatar DiceBear + fixes de design no painel híbrido

**O que foi feito**:
- Substituída a lógica de busca de foto Meta API (sempre retornava None) por geração determinística via DiceBear API no método `gerar_url_avatar` em `services/whatsapp.py`. O método `buscar_foto_perfil` foi mantido para não quebrar interface.
- Em `api/admin.py`, endpoint `GET /admin/cliente/{telefone}/info`: removidas toda lógica de TTL cache e chamada à Meta API, substituída por `whatsapp.gerar_url_avatar(user.nome_cliente, telefone)`. Zero escritas em banco, zero chamadas externas em runtime.
- `static/admin/app.js`: `abrirConversa` agora chama `abrirInfoPanel()` em desktop (>=1024px) em vez de apenas remover `hidden` — resolve bug onde painel ficava invisível (classe `colapsado` não era removida).
- `static/admin/app.js`: conversas com `aguardando_humano=true` ganham `font-bold text-white` no nome em vez de `font-semibold text-[#e0e0e0]`.
- `static/admin/index.html`: empty state substituído — ícone reduzido, nome "Barbearia Bolshoi" em destaque, tagline contextualizada.
- `static/admin/index.html`: footer de composição unificado em container `bg-[#2b2b2b] border border-[#3a3a3a] rounded-xl` englobando tanto o botão de respostas rápidas quanto a textarea+botão de envio.
- `static/admin/index.html`: sidebar header ganhou `border-b-2 border-b-[#2481cc]/20` para diferenciar visualmente do footer.
- `static/admin/index.html`: botões Assumir (`min-w-[90px]`) e Devolver (`min-w-[110px]`) com largura mínima para evitar layout shift.
- `static/admin/atendentes.html`: campo login corrigido — placeholder `maria_silva`, `pattern="^[a-z0-9_]+$"`, `title` correto, hint "Letras minúsculas, números e underscore (_)".
- `static/admin/atendentes.html`: `<tr>` do thead ganhou `sticky top-0 z-10` para cabeçalho fixo em listas longas.
- `static/admin/login.html`: logo substituída de ícone de chat genérico por iniciais "BB" estilizadas em quadrado azul 16x16 com `shadow-lg`.

**Arquivos modificados**:
- `services/whatsapp.py`
- `api/admin.py`
- `static/admin/app.js`
- `static/admin/index.html`
- `static/admin/atendentes.html`
- `static/admin/login.html`

**Dependências de schema**: nenhuma — colunas `foto_url` e `foto_atualizada_em` permanecem no modelo sem uso ativo (sem risco de regressão, `create_all` não altera tabelas existentes).

**Edge cases tratados**:
- `gerar_url_avatar` com `nome=None` → usa `telefone` como seed; com ambos None → usa "?" como seed
- `abrirInfoPanel()` já remove `hidden` E `colapsado` — a chamada direta era o que faltava
- `btn-enviar` mantido com `textContent` dinâmico no JS (não usa `innerHTML`) — sem regressão no optimistic UI
- Footer unificado mantém o mesmo `id="form-enviar"`, `id="texto-msg"`, `id="btn-enviar"`, `id="popover-rapidas"`, `id="lista-rapidas"` — todos os listeners JS existentes continuam funcionando sem alteração

**O que QA deve focar**:
1. Abrir conversa em desktop (>=1024px) — painel de info deve aparecer expandido imediatamente
2. Abrir conversa em mobile (<1024px) — painel NÃO deve abrir automaticamente
3. Verificar avatar DiceBear no painel de info (deve exibir iniciais coloridas em SVG azul)
4. Frontend `img.onerror` já existe — testar com nome vazio (avatar exibe iniciais do telefone)
5. Criar atendente com login contendo ponto (ex: `maria.silva`) — HTML5 `pattern` deve bloquear no browser antes de chegar no backend
6. Verificar thead fixo ao rolar lista longa de atendentes
7. Verificar que footer de composição não tem elementos soltos (botão "Respostas rápidas" dentro do container)
8. Verificar que conversas aguardando aparecem em `font-bold text-white` na sidebar

**Bloqueios**: nenhum
