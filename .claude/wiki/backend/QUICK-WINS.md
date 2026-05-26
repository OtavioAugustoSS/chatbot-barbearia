# Quick Wins — AI Quality Improvements

Ordenados por esforço crescente. Todos são mudanças cirúrgicas sem impacto no contrato JSON.

---

## QW-1: JSON Fallback com Regex Extraction (Esforço: 15min)

**Problema:** O modelo retornou JSON sem `{` inicial ou com texto livre antes do JSON (confirmado em `erro_ia_debug.txt`). Isso dispara `transbordo_falha` e desativa o bot desnecessariamente.

**Fix:** Em `services/ai_service.py`, entre o strip de fences e o `json.loads()`, adicionar:
```python
# Fallback: extrai objeto JSON embutido em texto livre
if not response_text.startswith('{'):
    match = re.search(r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)?\}', response_text, re.DOTALL)
    if match:
        response_text = match.group(0)
```

**Impacto:** Elimina falsos transbordos causados por resposta válida com texto extra. Custo: zero tokens extras. Zero risco de regressão — o fallback só atua se o parse inicial falhar.

---

## QW-2: Sanitização de `| ref:` no Output (Esforço: 10min)

**Problema:** Se o modelo sofrer drift e copiar literalmente o campo `| ref: dura Xmin; desc: Y` para a resposta, esse texto chega ao cliente. A proteção atual é só instrucional (no prompt).

**Fix:** Em `_validar_resposta()` em `services/ai_service.py`, após sanitizar a intenção:
```python
resposta = re.sub(r'\s*\|\s*ref:[^\n<]*', '', resposta)
```

**Impacto:** Proteção técnica no output — mesmo com drift total o `| ref:` nunca vaza. Custo: 1 regex por resposta (microsegundos).

---

## QW-3: Ampliar Booking Promise Regex (Esforço: 20min)

**Problema:** 4 de 5 frases de agendamento perigosas escapam ao regex atual. "reserva confirmada", "já deixei marcado", "pode ir que já está marcado", "vou deixar reservado" passam sem bloqueio.

**Fix:** Ampliar `_REGEX_AGENDAMENTO_PROIBIDO` em `services/ai_service.py`:
```python
_REGEX_AGENDAMENTO_PROIBIDO = re.compile(
    r"\b("
    r"marquei|agendei|reservei|"
    r"confirmei seu? hor[aá]rio|"
    r"seu hor[aá]rio (est[aá]|foi) (marcado|agendado|confirmado|reservado)|"
    r"j[aá] (marquei|agendei|reservei|deixei\s+marcad[ao])|"
    r"posso (marcar|agendar|reservar) (para|pra) (voc[eê]|ti)|"
    r"vou (marcar|agendar|reservar|deixar\s+(marcad|reservad|agendad)[ao]) (para|pra)? ?(voc[eê]|ti)?|"
    r"reserva\s+confirmada|"
    r"agendamento\s+(foi\s+)?(realizado|confirmado|feito|conclu[íi]do)|"
    r"(ficou|est[aá])\s+(marcad|agendad|confirmad|reservad)[ao]|"
    r"pode\s+ir\s+que\s+j[aá]\s+est[aá]\s+(marcad|agendad|confirmad)[ao]"
    r")\b",
    re.IGNORECASE,
)
```

**Impacto:** Cobertura de praticamente todas as variações de promessa de agendamento. Último nível de defesa antes do cliente receber informação errada.

---

## QW-4: Cache de Horários do Banco (Esforço: 15min)

**Problema:** `_carregar_horarios_db()` abre `SessionLocal()` a cada chamada de IA. Sem cache, 100 msgs/min = 100 queries desnecessárias para dados que mudam raramente.

**Fix:** Adicionar cache de módulo em `services/ai_service.py`:
```python
_cache_horarios: dict = {"data": None, "expira_em": 0.0}
_HORARIOS_CACHE_TTL = 300  # 5 min

def _carregar_horarios_db() -> dict:
    agora = time.time()
    if _cache_horarios["data"] is not None and agora < _cache_horarios["expira_em"]:
        return _cache_horarios["data"]
    # ... query original ...
    _cache_horarios.update({"data": resultado, "expira_em": agora + _HORARIOS_CACHE_TTL})
    return resultado
```

**Impacto:** Elimina query de horários em ~99% das chamadas de IA. Dado que horários mudam raríssimamente (setup inicial), 5min TTL é conservador o suficiente.

---

## QW-5: Canonical Gaps — Deficiente, Nubank, Fred (Esforço: 30min)

**Problema:** Três classes de queries comuns chegam à IA desnecessariamente:
- "tem acesso pra deficiente?" → IA chama 1 query completa por uma info já na `RESPOSTA_FAQ_ESTRUTURA`
- "aceitam nubank?" → IA responde (corretamente, mas com custo) quando resposta canônica de pagamento bastaria
- "quero falar com o dono/proprietário" → IA trata bem mas usa tokens

**Fix:** Três patches em `core/respostas_canonicas.py`:

1. Adicionar `deficiente(s)?|pcd|pessoa\s+(com\s+)?defici[eê]ncia` ao padrão de estrutura (linha ~207).

2. Adicionar `nubank|picpay|mercado\s+pago|inter\b|pagbank` ao padrão de pagamento (linha ~175).

3. Adicionar novo padrão antes de RESPOSTA_FAQ_ESTRUTURA:
```python
RESPOSTA_CONTATO_FRED = (
    "O contato direto do Fred (proprietário) é: *(38) 99897-0661*<br><br>"
    f"{_FECHAMENTO}"
)
# padrão:
re.compile(
    r"\b(falar\s+com\s+(o\s+)?(dono|propriet[aá]rio)|contato\s+do\s+(dono|fred|propriet[aá]rio))\b",
    re.IGNORECASE,
)
```

**Impacto:** Reduz chamadas à IA para perguntas rotineiras. Melhora consistência (canônica nunca alucina).

---

## Priorização Executiva

| Rank | Quick Win | Severidade Original | Esforço | ROI |
|---|---|---|---|---|
| 1 | QW-1: JSON Fallback | CRÍTICO | 15min | Elimina falsos transbordos confirmados em produção |
| 2 | QW-3: Booking Regex | ALTO | 20min | Fecha 4/5 lacunas de booking promise |
| 3 | QW-2: Sanitização `\| ref:` | MÉDIO | 10min | Proteção técnica vs. drift (menor esforço do lote) |
| 4 | QW-4: Cache Horários | BAIXO | 15min | Reduz queries DB em alta carga |
| 5 | QW-5: Canonical Gaps | BAIXO | 30min | Reduz tokens e melhora consistência |
