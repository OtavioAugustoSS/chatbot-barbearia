# business-rules/ — Diretório do Product Owner

## Convenções
- **Owner:** `product-owner-agent`
- Cada decisão de produto vira arquivo `.md` com slug descritivo
- Naming: `BR-{NNN}-{slug}.md` (ex: `BR-001-anti-agendamento.md`)
- Registrar no `../index.md` ao criar
- Formato de cada nota:
  ```
  # BR-NNN: {título}
  Data: YYYY-MM-DD
  Stakeholders: {quem pediu/decidiu}

  ## Contexto
  ## Regra
  ## Impacto em código
  ## Exceções
  ```

## Regras canônicas pré-existentes (do `core/prompts.py` e `CLAUDE.md`)
- Bot **NUNCA** agenda consultas — sempre redirecionar para AppBarber
- Serviços: 💈 barbearia (barbeiros) vs 💆‍♀️ estética (Isabella apenas)
- Bot não processa mídia (áudio, imagem, documento)
- Tom: português profissional, sem gírias
- Contato Fred (38) 99897-0661 só se cliente perguntar explicitamente
- Mensagens da IA usam `<br>` para quebra de linha
- Mensagens de operador usam `\n` literal
