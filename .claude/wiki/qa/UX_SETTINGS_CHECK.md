# QA: Settings Page Endpoint Verification
**Date:** 2026-05-27  
**Auditor:** qa-agent  
**Server:** http://127.0.0.1:8000 (modo híbrido)  
**Credentials:** qa_sweep / qasweep12345 (atendente_id=4)

---

## Endpoint Results

| # | Method | Path | HTTP Status | Result |
|---|--------|------|-------------|--------|
| 1 | POST | /admin/login | 200 | OK — JWT emitido |
| 2 | GET | /admin/atendentes | 200 | OK — retornou 3 atendentes |
| 3 | POST | /admin/atendentes | 201 | OK — criou qa_temp_settings (id=5) |
| 4 | PATCH | /admin/atendentes/5/desativar | 200 | OK — `{"ok": true}` |
| 5 | PATCH | /admin/atendentes/5/ativar | 200 | OK — `{"ok": true, "id": 5, "ativo": true}` |
| 6 | PATCH | /admin/atendentes/5/desativar | 200 | OK — cleanup (desativado) |
| 7 | GET | /admin/labels?incluir_inativas=true | 200 | OK — 5 labels existentes |
| 8 | POST | /admin/labels | 201 | OK — criou qa-label-teste (id=11) |
| 9 | PATCH | /admin/labels/11 | 200 | OK — retornou label atualizada |
| 10 | DELETE | /admin/labels/11 | 204 | OK — deletada |
| 11 | GET | /admin/canned | 200 | OK — 8 respostas rápidas |
| 12 | POST | /admin/canned | 201 | OK — criou /qa_teste (id=17, atendente_id=4) |
| 13 | PATCH | /admin/canned/17 | 200 | OK — retornou canned atualizado |
| 14 | DELETE | /admin/canned/17 | 204 | OK — deletado |
| 15 | Aparência | (nenhum endpoint) | — | Client-only: localStorage. Confirmado: sem chamada de API |

**Veredito geral: TODOS os 14 endpoints funcionam corretamente. Backend sólido.**

---

## Cleanup

- `qa_temp_settings` (id=5): desativado (sem endpoint de delete para operadores — comportamento esperado)
- `qa-label-teste` (id=11): deletado (DELETE 204)
- `/qa_teste` canned (id=17): deletado (DELETE 204)

---

## Confirmação dos 3 Gaps Suspeitos

### GAP-A: Fallback de canned em settings.html:646 mascara erro real
**PROCEDE.**  
`settings.html:645-649` — o `catch(e)` de `carregarCanned()` silencia qualquer erro e exibe "Funcionalidade em implementação" no tbody. O endpoint `/admin/canned` existe e retorna 200. Se houver um erro real (ex: 500, timeout, auth expirado), o usuário vê uma mensagem enganosa que sugere que a feature está incompleta, não que houve falha. O erro real é descartado sem log.

```js
// settings.html:645
} catch(e) {
  // Endpoint pode não existir ainda em fases iniciais   <-- comentário desatualizado
  const tbody = document.getElementById('tbody-canned');
  if (tbody) tbody.innerHTML = '<tr>...<td>Funcionalidade em implementação</td>...';
}
```

**Fix sugerido (frontend-agent):** remover o catch silencioso ou substituir por `showMsg('Erro ao carregar respostas rápidas', 'error')` + re-throw, igual ao padrão usado em `carregarAtendentes()` e `carregarLabels()`.

---

### GAP-B: Match de 409 por string em lines 766/796/827
**PROCEDE — e é mais grave do que suspeitado.**  
O padrão `e.message?.includes('409')` nunca ativa porque `req()` lança `new Error(await res.text())` — o `e.message` contém o **body JSON da resposta** (ex: `{"detail":"Login já existe"}`), não o código HTTP.

Provas coletadas dos bodies reais de 409:
- Atendente duplicado: `{"detail":"Login já existe"}`
- Label duplicada: `{"detail":"Já existe label com nome 'qa-dup-test'"}`
- Canned duplicado: `{"detail":"Atalho '/qa_dup' já existe nesse escopo"}`

A string `"409"` **nunca aparece** no body. Resultado: o usuário sempre vê a mensagem genérica de erro ("Erro ao criar atendente", "Erro ao salvar") ao duplicar, mesmo que o backend retorne mensagem clara.

**Fix sugerido (frontend-agent):** checar `e.message?.includes('detail')` e parsear o JSON, ou mudar `req()` para lançar um objeto `{status, body}` em vez de `new Error(text)`.  
Alternativa mínima: `e.message?.includes('já existe') || e.message?.includes('já existe')` — mas frágil. Melhor: estruturar o erro.

---

### GAP-C: Input de cor hex sem validação real no submit (settings.html:301)
**PROCEDE.**  
`label-cor-hex` (line 301) tem `pattern="#[0-9a-fA-F]{6}"` mas **não tem `required`**. O form usa `e.preventDefault()` (line 774), o que desativa a validação nativa do browser para campos não-`required`. O handler de submit (line 778) lê `label-cor-hex` e envia o valor diretamente ao backend sem validar o padrão:

```js
// settings.html:778
const cor = document.getElementById('label-cor-hex').value;
// enviado direto sem checar /^#[0-9a-fA-F]{6}$/.test(cor)
```

Um usuário pode enviar string vazia ou hex malformado. O backend pode aceitar ou rejeitar com 422 — que o catch genérico mostraria como "Erro ao salvar" sem indicar o campo problemático.

**Fix sugerido (frontend-agent):** adicionar validação JS antes do `await req(...)`:
```js
if (!/^#[0-9a-fA-F]{6}$/.test(cor)) {
  erroEl.textContent = 'Cor inválida (use formato #RRGGBB)';
  erroEl.classList.remove('hidden');
  return;
}
```

---

## Resumo de Severidade

| ID | Sev | Arquivo:Linha | Problema | Dono |
|----|-----|--------------|----------|------|
| GAP-A | P1 | settings.html:645-649 | catch silencioso em carregarCanned() mascara erros reais com mensagem enganosa | frontend-agent |
| GAP-B | P1 | settings.html:766,796,827 | `e.message?.includes('409')` nunca ativa — body não contém o status code; usuário sempre vê erro genérico em conflito 409 | frontend-agent |
| GAP-C | P2 | settings.html:301,778 | hex input sem `required` + submit bypassa validação nativa; valor malformado enviado ao backend | frontend-agent |
