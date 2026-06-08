"""
Circuit breaker in-memory e thread-safe (P2-1).

Objetivo: num outage do NIM (ou outro recurso externo), evitar que cada mensagem
gaste o ciclo completo de retries (~24s) e sature as threads de background. Depois
de N falhas consecutivas o circuito abre e as chamadas falham rápido
(CircuitOpenError), o que no ai_service aciona o handoff imediato em vez de pendurar.
"""
import time
import logging
import threading

log = logging.getLogger("barbearia.circuit")


class CircuitOpenError(Exception):
    """Levantada quando o circuito está aberto — falha rápida, sem chamar o recurso."""

    def __init__(self, name: str, retry_em: float):
        super().__init__(f"Circuito '{name}' aberto — retry em ~{retry_em:.0f}s")
        self.name = name
        self.retry_em = retry_em


class CircuitBreaker:
    """
    Estados:
      - closed:    chamadas passam. >= failure_threshold falhas consecutivas → open.
      - open:      chamadas falham rápido (CircuitOpenError) até reset_timeout expirar.
      - half_open: 1 chamada de teste passa; sucesso → closed, falha → open de novo.

    Uso:
        cb = CircuitBreaker(failure_threshold=3, reset_timeout=30)
        resultado = cb.call(funcao, *args, **kwargs)

    `clock` é injetável para testes (default time.monotonic).
    """

    def __init__(self, failure_threshold: int = 3, reset_timeout: float = 30.0,
                 name: str = "cb", clock=time.monotonic):
        self._failure_threshold = failure_threshold
        self._reset_timeout = reset_timeout
        self._name = name
        self._clock = clock
        self._lock = threading.Lock()
        self._failures = 0
        self._state = "closed"
        self._opened_at = 0.0

    @property
    def state(self) -> str:
        with self._lock:
            return self._state

    def call(self, fn, *args, **kwargs):
        with self._lock:
            if self._state == "open":
                decorrido = self._clock() - self._opened_at
                if decorrido >= self._reset_timeout:
                    self._state = "half_open"
                    log.warning("[CIRCUIT %s] half-open — tentando recuperação.", self._name)
                else:
                    raise CircuitOpenError(self._name, self._reset_timeout - decorrido)
        try:
            resultado = fn(*args, **kwargs)
        except Exception:
            self._registrar_falha()
            raise
        else:
            self._registrar_sucesso()
            return resultado

    def _registrar_sucesso(self) -> None:
        with self._lock:
            if self._state != "closed":
                log.info("[CIRCUIT %s] recuperado — circuito fechado.", self._name)
            self._failures = 0
            self._state = "closed"

    def _registrar_falha(self) -> None:
        with self._lock:
            self._failures += 1
            if self._failures >= self._failure_threshold and self._state != "open":
                self._state = "open"
                self._opened_at = self._clock()
                log.error(
                    "[CIRCUIT %s] ABERTO após %d falha(s) consecutiva(s) — "
                    "falha rápida por %.0fs (evita saturar threads em outage).",
                    self._name, self._failures, self._reset_timeout,
                )

    def reset(self) -> None:
        """Volta ao estado inicial (usado em testes)."""
        with self._lock:
            self._failures = 0
            self._state = "closed"
            self._opened_at = 0.0
