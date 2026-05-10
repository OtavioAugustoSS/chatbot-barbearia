"""
Notificador in-memory para o dashboard de atendentes (modo híbrido).

Usa filas thread-safe por assinante. Cada cliente SSE conectado recebe sua própria
fila e consome eventos sem bloquear publicadores. Eventos perdidos não são reentregues
(o dashboard recarrega o estado completo via GET /admin/conversas no reconnect).

Em modo bot_only o notificador é instanciado mas nunca recebe `publicar()` (webhook só
chama dentro de blocos `if MODO_HIBRIDO`), então fica inerte sem custo perceptível.
"""
import json
import queue
import threading
import time
import logging
from typing import Iterator

log = logging.getLogger("barbearia.notificador")

_FILA_TAMANHO_MAX = 100  # eventos por assinante; se encher, evento mais antigo é descartado
_HEARTBEAT_SEGUNDOS = 25  # comentário SSE periódico para evitar timeout de proxy


class Notificador:
    def __init__(self):
        self._assinantes: list[queue.Queue] = []
        self._lock = threading.Lock()

    def assinar(self) -> queue.Queue:
        """Registra um novo consumidor SSE e devolve sua fila exclusiva."""
        q: queue.Queue = queue.Queue(maxsize=_FILA_TAMANHO_MAX)
        with self._lock:
            self._assinantes.append(q)
            log.info("Novo assinante SSE. Total: %d", len(self._assinantes))
        return q

    def desassinar(self, q: queue.Queue) -> None:
        """Remove o consumidor da lista de entrega."""
        with self._lock:
            try:
                self._assinantes.remove(q)
                log.info("Assinante SSE removido. Restantes: %d", len(self._assinantes))
            except ValueError:
                pass

    def publicar(self, evento: dict) -> None:
        """
        Entrega o evento a todos os assinantes ativos. Evento que não cabe na fila
        descarta o mais antigo (drop-oldest) — perda preferível a bloquear webhook.
        """
        with self._lock:
            for q in list(self._assinantes):
                try:
                    q.put_nowait(evento)
                except queue.Full:
                    try:
                        q.get_nowait()  # descarta antigo
                        q.put_nowait(evento)
                    except (queue.Empty, queue.Full) as e:
                        # Fila com 100 eventos é sinal de cliente SSE travado.
                        # Logamos para diagnóstico em vez de perder evento em silêncio.
                        log.warning("Notificador: evento descartado para assinante (fila saturada): %s", e)

    def stream(self, q: queue.Queue) -> Iterator[str]:
        """Gera linhas SSE no formato `data: <json>\\n\\n` + heartbeat periódico."""
        ultimo_heartbeat = time.time()
        try:
            while True:
                try:
                    evento = q.get(timeout=1.0)
                    yield f"data: {json.dumps(evento, ensure_ascii=False)}\n\n"
                except queue.Empty:
                    pass
                if time.time() - ultimo_heartbeat > _HEARTBEAT_SEGUNDOS:
                    ultimo_heartbeat = time.time()
                    yield ": keepalive\n\n"
        finally:
            self.desassinar(q)


notificador = Notificador()
