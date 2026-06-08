"""P2-1 — circuit breaker do NIM.

Unit (lógica do breaker com clock injetado) + integração (ai_service aciona
handoff e para de chamar o NIM quando o circuito abre).
"""
import pytest

from services.circuit_breaker import CircuitBreaker, CircuitOpenError


class _Clock:
    """Relógio fake e determinístico para evitar sleeps reais nos testes."""
    def __init__(self):
        self.t = 0.0

    def __call__(self):
        return self.t

    def avancar(self, dt):
        self.t += dt


def _falha():
    raise RuntimeError("boom")


def _ok():
    return "ok"


# ----------------------------- unit -----------------------------
def test_abre_apos_falhas_consecutivas():
    cb = CircuitBreaker(failure_threshold=3, reset_timeout=30, clock=_Clock())
    for _ in range(3):
        with pytest.raises(RuntimeError):
            cb.call(_falha)
    assert cb.state == "open"


def test_aberto_falha_rapido_sem_chamar_fn():
    cb = CircuitBreaker(failure_threshold=2, reset_timeout=30, clock=_Clock())
    for _ in range(2):
        with pytest.raises(RuntimeError):
            cb.call(_falha)
    chamadas = []
    with pytest.raises(CircuitOpenError):
        cb.call(lambda: chamadas.append(1))
    assert chamadas == []  # circuito aberto não invoca o recurso


def test_meio_aberto_recupera_no_sucesso():
    clk = _Clock()
    cb = CircuitBreaker(failure_threshold=2, reset_timeout=30, clock=clk)
    for _ in range(2):
        with pytest.raises(RuntimeError):
            cb.call(_falha)
    assert cb.state == "open"
    clk.avancar(31)  # expira o reset_timeout → half_open
    assert cb.call(_ok) == "ok"
    assert cb.state == "closed"


def test_meio_aberto_reabre_no_fracasso():
    clk = _Clock()
    cb = CircuitBreaker(failure_threshold=2, reset_timeout=30, clock=clk)
    for _ in range(2):
        with pytest.raises(RuntimeError):
            cb.call(_falha)
    clk.avancar(31)
    with pytest.raises(RuntimeError):
        cb.call(_falha)  # trial em half_open falha
    assert cb.state == "open"


def test_sucesso_zera_contador_de_falhas():
    cb = CircuitBreaker(failure_threshold=3, reset_timeout=30, clock=_Clock())
    with pytest.raises(RuntimeError):
        cb.call(_falha)
    with pytest.raises(RuntimeError):
        cb.call(_falha)
    assert cb.call(_ok) == "ok"          # sucesso zera o contador
    with pytest.raises(RuntimeError):
        cb.call(_falha)
    with pytest.raises(RuntimeError):
        cb.call(_falha)
    assert cb.state == "closed"          # 2 falhas pós-reset não abrem (threshold 3)


# -------------------------- integração --------------------------
def test_ai_service_handoff_e_para_de_chamar_nim_no_outage(db, monkeypatch):
    from services.ai_service import AIService

    svc = AIService()
    svc._breaker = CircuitBreaker(failure_threshold=2, reset_timeout=30)

    def _boom(messages):
        raise RuntimeError("NIM down")

    monkeypatch.setattr(svc, "_chamar_llm", _boom)

    r1 = svc.processar_intencao(db, [], "oi")
    r2 = svc.processar_intencao(db, [], "oi")
    assert r1["intencao"] == "transbordo_falha"
    assert r2["intencao"] == "transbordo_falha"
    assert svc._breaker.state == "open"

    # Com o circuito aberto, a 3ª mensagem NÃO deve chamar o NIM (fast-fail → handoff).
    chamou = {"n": 0}

    def _conta(messages):
        chamou["n"] += 1
        raise RuntimeError("não deveria ser chamado")

    monkeypatch.setattr(svc, "_chamar_llm", _conta)
    r3 = svc.processar_intencao(db, [], "oi")
    assert r3["intencao"] == "transbordo_falha"
    assert chamou["n"] == 0
