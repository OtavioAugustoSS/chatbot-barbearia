"""
Notificador in-memory para o dashboard de atendentes (modo híbrido).

H3: reescrito sobre asyncio.Queue. A versão anterior usava queue.Queue com
`get(timeout=1)` num endpoint sync — cada conexão SSE prendia UMA thread do
threadpool anyio (default ~40) em loop infinito, esgotando o pool com poucos
atendentes/abas e travando todos os endpoints sync do app. Agora o stream é um
async generator que aguarda no event loop (zero threads presas por conexão).

Publicadores continuam sendo THREADS SYNC (background tasks do webhook,
endpoints sync do admin) — a ponte thread→loop é loop.call_soon_threadsafe,
com o loop capturado no evento de startup do FastAPI (main.py).

Eventos perdidos não são reentregues (o dashboard recarrega o estado completo
via GET /admin/conversas no reconnect). Em modo bot_only o notificador é
instanciado mas nunca recebe `publicar()`.
"""
import asyncio
import json
import logging
import threading
from typing import AsyncIterator

log = logging.getLogger("barbearia.notificador")

_FILA_TAMANHO_MAX = 100  # eventos por assinante; se encher, evento mais antigo é descartado
_HEARTBEAT_SEGUNDOS = 25  # comentário SSE periódico para evitar timeout de proxy


class Notificador:
    def __init__(self):
        self._assinantes: list[asyncio.Queue] = []
        self._lock = threading.Lock()
        self._loop: asyncio.AbstractEventLoop | None = None

    def set_loop(self, loop: asyncio.AbstractEventLoop) -> None:
        """Captura o event loop do servidor — chamado no startup do FastAPI."""
        self._loop = loop

    def assinar(self) -> asyncio.Queue:
        """Registra um novo consumidor SSE e devolve sua fila exclusiva.
        Deve ser chamado de dentro do event loop (endpoint async)."""
        q: asyncio.Queue = asyncio.Queue(maxsize=_FILA_TAMANHO_MAX)
        with self._lock:
            self._assinantes.append(q)
            log.info("Novo assinante SSE. Total: %d", len(self._assinantes))
        return q

    def desassinar(self, q: asyncio.Queue) -> None:
        """Remove o consumidor da lista de entrega."""
        with self._lock:
            try:
                self._assinantes.remove(q)
                log.info("Assinante SSE removido. Restantes: %d", len(self._assinantes))
            except ValueError:
                pass

    def publicar(self, evento: dict) -> None:
        """
        Entrega o evento a todos os assinantes ativos. Thread-safe: pode ser
        chamado de threads sync (background tasks) — a entrega é agendada no
        event loop via call_soon_threadsafe.
        Sem loop capturado (testes unitários, boot) o evento é no-op logado.
        """
        loop = self._loop
        if loop is None or loop.is_closed():
            log.debug("Notificador sem event loop ativo — evento descartado: %s", evento.get("tipo"))
            return
        try:
            loop.call_soon_threadsafe(self._entregar, evento)
        except RuntimeError:
            # Loop encerrando (shutdown) — descarte silencioso é o comportamento correto.
            log.debug("Notificador: loop fechado durante publicar().")

    def _entregar(self, evento: dict) -> None:
        """Roda NO event loop: put_nowait com drop-oldest em fila saturada."""
        with self._lock:
            assinantes = list(self._assinantes)
        for q in assinantes:
            try:
                q.put_nowait(evento)
            except asyncio.QueueFull:
                try:
                    q.get_nowait()  # descarta antigo
                    q.put_nowait(evento)
                except (asyncio.QueueEmpty, asyncio.QueueFull) as e:
                    # Fila com 100 eventos é sinal de cliente SSE travado.
                    log.warning("Notificador: evento descartado para assinante (fila saturada): %s", e)

    async def stream(self, q: asyncio.Queue) -> AsyncIterator[str]:
        """Gera linhas SSE `data: <json>\\n\\n` + heartbeat periódico, sem prender thread."""
        try:
            while True:
                try:
                    evento = await asyncio.wait_for(q.get(), timeout=_HEARTBEAT_SEGUNDOS)
                except asyncio.TimeoutError:
                    yield ": keepalive\n\n"
                    continue
                yield f"data: {json.dumps(evento, ensure_ascii=False)}\n\n"
        finally:
            self.desassinar(q)


notificador = Notificador()
