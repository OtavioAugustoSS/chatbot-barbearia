# frontend/ — Diretório do Frontend Developer

## Convenções
- **Owner:** `frontend-agent`
- Relatórios de UI, decisões de UX, especificações de componentes
- Naming: `{slug}.md` ou `{tela}-{aspecto}.md`
- Registrar no `../index.md` ao criar nota relevante
- Código vai em `static/admin/` (NÃO neste diretório)

## Stack real
- Vanilla JavaScript ES6+ (sem React/Vue/framework)
- HTML5 + CSS3 (CSS embarcado em `<style>` no HTML)
- JWT armazenado em `localStorage`
- SSE via `EventSource` nativo
- Sem build step

## Arquivos atuais
- `static/admin/index.html` — dashboard principal
- `static/admin/login.html` — tela de login
- `static/admin/app.js` — lógica do dashboard
