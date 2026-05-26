# ADR-008: Padrão Promise-based para Modais de Confirmação e Input
Status: proposto
Data: 2026-05-21
Decisor: architect-agent
Stakeholders consultados: frontend-agent (FASE3), product-owner-agent (UX-BUG documentado)

## Contexto

A auditoria FASE 1 identificou 3 ocorrências de `window.prompt()` em `app.js` (linhas 845, 1172, 1279). A FASE 3 incluía SP-1 (modal datepicker para snooze) como item de sprint justamente para eliminar esses `prompt()`. A validação FASE 3 confirmou que os `prompt()` ainda existem — SP-1 não foi entregue.

Antes de implementar, é necessário documentar o padrão arquitetural correto para modais em vanilla JS, evitando que a solução use abordagem incompatível com ADR-007 (sem frameworks, sem bundler).

As três ocorrências de `window.prompt()` são:

1. `alterarStatus('snoozed')` — linha 845: pede número de horas para adiar conversa individual
2. `salvarViewAtual()` — linha 1172: pede nome da view (texto livre)
3. `bulkSnooze()` — linha 1279: pede número de horas para adiar conversas em bulk

`window.prompt()` é bloqueante (bloqueia o event loop JS), não estilizável, e em alguns contextos de segurança (iframes, cross-origin) é suprimido silenciosamente — retornando `null` sem o usuário ver nada.

## Decisão

### Padrão: Promise-based Modal em vanilla JS

Modais de input/confirmação devem ser implementados como funções assíncronas que retornam `Promise`, seguindo o padrão abaixo. O modal é injetado dinamicamente no DOM e removido após resolução.

```javascript
/**
 * Exibe modal de input numérico e retorna Promise<number|null>.
 * null = usuário cancelou.
 */
function modalNumeroHoras(titulo, defaultValue = '24') {
  return new Promise((resolve) => {
    const overlay = document.createElement('div');
    overlay.className = 'modal-overlay';
    overlay.innerHTML = `
      <div class="modal-box">
        <h3 class="modal-titulo">${escapeHtml(titulo)}</h3>
        <input id="modal-input-horas" type="number" class="modal-input"
               value="${defaultValue}" min="1" max="720" step="1">
        <div class="modal-actions">
          <button id="modal-cancelar" class="btn-secondary">Cancelar</button>
          <button id="modal-confirmar" class="btn-primary">Confirmar</button>
        </div>
      </div>
    `;
    document.body.appendChild(overlay);
    const input = overlay.querySelector('#modal-input-horas');
    input.focus(); input.select();

    const cleanup = (val) => { overlay.remove(); resolve(val); };

    overlay.querySelector('#modal-confirmar').addEventListener('click', () => {
      const h = parseInt(input.value);
      cleanup(isNaN(h) || h <= 0 || h > 720 ? null : h);
    });
    overlay.querySelector('#modal-cancelar').addEventListener('click', () => cleanup(null));
    overlay.addEventListener('click', (e) => { if (e.target === overlay) cleanup(null); });
    overlay.addEventListener('keydown', (e) => {
      if (e.key === 'Enter') overlay.querySelector('#modal-confirmar').click();
      if (e.key === 'Escape') cleanup(null);
    });
  });
}
```

Chamada de uso (substitui `window.prompt()`):
```javascript
// ANTES (bloqueante):
const horas = prompt('Adiar por quantas horas?', '24');
if (isNaN(parseInt(horas))) return;

// DEPOIS (não-bloqueante, estilizável):
const horas = await modalNumeroHoras('Adiar conversa por quantas horas?');
if (horas === null) return;  // usuário cancelou
```

### Catálogo de modais a implementar (substitutos dos prompt())

| Local | Tipo | Substituição |
|---|---|---|
| `alterarStatus('snoozed')` — linha 845 | Input numérico (horas) | `modalNumeroHoras()` |
| `bulkSnooze()` — linha 1279 | Input numérico (horas) + contagem de conversas | `modalNumeroHoras()` com título dinâmico |
| `salvarViewAtual()` — linha 1172 | Input texto (nome da view) | `modalTextoLivre()` — padrão análogo |

### Regras de implementação

1. **Injeção dinâmica no `<body>`**: o overlay é criado em JS puro, sem HTML pré-existente no template — simplifica manutenção e evita conflitos de estado
2. **Cleanup obrigatório**: sempre chamar `overlay.remove()` antes de `resolve()` — sem exceção
3. **ESC e click-fora fecham e resolvem com `null`**: comportamento padrão de UX; nunca deixar overlay preso
4. **Foco automático**: `input.focus()` + `input.select()` imediatamente após append — acessibilidade mínima
5. **Enter confirma**: listener `keydown` no overlay inteiro, não apenas no botão
6. **Sem bibliotecas externas**: implementado em vanilla JS puro — aderente ao ADR-007

### CSS mínimo necessário (a adicionar em `<style>` do `index.html`)

```css
.modal-overlay {
  position: fixed; inset: 0; z-index: 9999;
  background: rgba(0,0,0,0.6);
  display: flex; align-items: center; justify-content: center;
}
.modal-box {
  background: var(--bg-card); border: 1px solid var(--border);
  border-radius: 12px; padding: 24px; min-width: 320px; max-width: 480px;
  display: flex; flex-direction: column; gap: 16px;
}
.modal-titulo { color: var(--text-primary); font-size: 0.95rem; font-weight: 600; }
.modal-input {
  background: var(--bg-base); border: 1px solid var(--border);
  color: var(--text-primary); border-radius: 8px;
  padding: 8px 12px; font-size: 0.9rem; width: 100%;
}
.modal-actions { display: flex; gap: 8px; justify-content: flex-end; }
```

### Padrão para `confirm()` nativo

`window.confirm()` é aceitável para confirmações destrutivas simples (ex.: "Devolver ao bot?", "Excluir nota?") onde a UX bloqueante é tolerável. A substituição por modal só é obrigatória para casos de **input de dado** (número, texto). Manter `confirm()` para confirmações booleanas é uma decisão pragmática aceita nesta ADR.

## Consequências

- Positivo: elimina `window.prompt()` (bloqueante, não estilizável, sujeito a supressão de browser)
- Positivo: modais ficam consistentes com o design system do dashboard (CSS variables)
- Positivo: padrão Promise permite composição assíncrona natural com `await`
- Negativo: adiciona ~40 linhas de código JS por tipo de modal — aceitável dado que são 2 tipos distintos
- Negativo: CSS adicional necessário no `index.html` — sem arquivo `.css` separado (aderente ao ADR-007)

## Alternativas consideradas

- `<dialog>` nativo HTML: suporte cross-browser adequado (Chrome 37+, Firefox 98+), mas API `showModal()` é síncrona e não retorna Promise nativa — requereria wrapper de qualquer forma; descartado por não simplificar
- `sweetalert2` via CDN: biblioteca polida, mas introduz dependência externa e CSS global que pode conflitar com o design system atual; rejeitado (ADR-007 requer justificativa para bibliotecas CDN)
- Manter `window.prompt()`: rejeitado — experiência de UX inferior, não estilizável, e documentado como UX-BUG em hot.md

## Status de implementação

SP-1 **ENTREGUE** (re-validação architect-agent 2026-05-21, 2ª passagem).

`#modal-snooze` e `#modal-input-text` presentes em `index.html`. Funções `abrirModalSnooze()` e `abrirModalInputTexto()` implementadas como Promise-based em `app.js`. Os 3 `window.prompt()` anteriores (linhas 845, 1172, 1279 da versão anterior) foram removidos e substituídos por chamadas `await` às funções de modal.
