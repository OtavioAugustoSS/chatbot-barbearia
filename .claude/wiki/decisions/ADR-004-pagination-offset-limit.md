# ADR-004: Estratégia de Paginação — Offset/Limit
Status: aceito
Data: 2026-05-21
Decisor: architect-agent
Stakeholders consultados: backend-agent (código existente como fonte de verdade)

## Contexto

O endpoint `GET /admin/conversas` e `GET /admin/notas/{telefone}` implementam paginação com `offset/limit`. A escolha não foi documentada. Cursor-based pagination (keyset) é frequentemente recomendada como alternativa. Esta ADR registra a decisão e o contexto que a justifica.

## Decisão

Usar **offset/limit** com envelope padronizado:

```json
{
  "items": [...],
  "page": 1,
  "per_page": 50,
  "total": 234,
  "has_more": true
}
```

Parâmetros de entrada: `page` (começa em 1, ge=1) e `per_page` (default 50, máx 200 para conversas; default 20, máx 100 para notas).

### Por que offset/limit e não cursor

1. **Volume de dados**: barbearia local — esperado <5.000 usuários e <50.000 mensagens no histórico operacional. Degradação de performance do offset (O(n) scan) só ocorre em milhões de linhas.

2. **Navegação aleatória de páginas**: o dashboard admin precisa mostrar cards de métricas (`totais_por_estado`) que requerem `COUNT(*)` independente da página. Cursor pagination não facilita isso.

3. **Ordenação por múltiplas colunas com NULLs**: conversas são ordenadas por `aguardando_humano DESC, data_ultima_interacao DESC`. Cursor pagination com múltiplas colunas e NULLs em MySQL requer SQL complexo e propenso a erros.

4. **Simplicidade de implementação**: equipe pequena; offset/limit é idiomático no SQLAlchemy e no frontend.

### Limites definidos

| Endpoint | Default | Máximo | Justificativa |
|---|---|---|---|
| `/admin/conversas` | 50 | 200 | Dashboard de lista — 50 é visível sem scroll; 200 como teto de segurança |
| `/admin/notas/{telefone}` | 20 | 100 | Painel lateral — notas são acessórias, 20 é suficiente para maioria |

### Trade-offs aceitos

- **Phantom reads**: se registros forem adicionados entre páginas, offset pode pular ou duplicar itens. Risco baixo: conversas não são deletadas, e inserções entre páginas são raras em barbearia local.
- **Performance de grandes offsets**: se a tabela `usuarios` crescer para >100k linhas, `OFFSET 50000 LIMIT 50` ficará lento. Aceitável no horizonte MVP.

## Consequências

- Positivo: implementação simples, validada, compatível com todos os cenários de UI atual
- Positivo: permite navegação por número de página (UI de paginação convencional)
- Negativo: performance degrada linearmente com offset alto em tabelas grandes
- Negativo: possíveis phantom reads em listas com alta taxa de inserção (irrelevante para o volume atual)

## Alternativas consideradas

- **Cursor pagination (keyset)**: mais eficiente em escala, mas complexo com múltiplas colunas de ordenação e NULLs. Rejeitado — não justificado pelo volume atual.
- **Infinit scroll / "load more"**: frontend já implementa `has_more` e poderia fazer isso, mas a UI do dashboard é tabela, não feed.

## Revisão recomendada

Se `usuarios` crescer para >20.000 linhas, avaliar migração para cursor pagination no endpoint `/admin/conversas`. O envelope já tem `has_more` que suporta ambos os padrões de UI.
