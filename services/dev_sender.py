"""
Sender fake para o modo dev (sem WHATSAPP_TOKEN/WHATSAPP_PHONE_ID).

Em vez de POSTar na Meta Cloud API, cada envio é registrado num outbox em memória
que o simulador local (/dev/simulador) consome via polling. Apenas o transporte
(_post_com_retry) é substituído: toda a validação de limites da Meta (tamanhos,
nº de botões/seções, IDs duplicados) do WhatsAppSender continua rodando, então o
comportamento observado no simulador é fiel ao de produção.
"""
import logging
import threading
import time
from collections import deque
from itertools import count
from uuid import uuid4

from services.whatsapp import WhatsAppSender

log = logging.getLogger("barbearia.dev_sender")


class OutboxDev:
    """Buffer thread-safe das mensagens 'enviadas' em modo dev.

    Cada evento: {seq, ts, telefone, tipo_log, payload, wamid}.
    maxlen limita memória; o simulador usa `seq` para polling incremental.
    """

    def __init__(self, maxlen: int = 300):
        self._eventos: deque = deque(maxlen=maxlen)
        self._lock = threading.Lock()
        self._seq = count(1)

    def registrar(self, telefone: str, payload: dict, wamid: str, tipo_log: str) -> None:
        evento = {
            "seq": next(self._seq),
            "ts": time.time(),
            "telefone": telefone,
            "tipo_log": tipo_log,
            "payload": payload,
            "wamid": wamid,
        }
        with self._lock:
            self._eventos.append(evento)

    def listar(self, telefone: str | None = None, desde_seq: int = 0) -> list[dict]:
        with self._lock:
            eventos = list(self._eventos)
        return [
            e
            for e in eventos
            if e["seq"] > desde_seq and (telefone is None or e["telefone"] == telefone)
        ]


outbox_dev = OutboxDev()


class DevWhatsAppSender(WhatsAppSender):
    """WhatsAppSender com transporte substituído pelo outbox local."""

    def _post_com_retry(self, payload: dict, numero: str, tipo_log: str) -> tuple[bool, str | None]:
        wamid = f"wamid.dev.{uuid4().hex}"
        outbox_dev.registrar(numero, payload, wamid, tipo_log)
        log.info("[DEV] Envio %s capturado no outbox para %s (wamid=%s)", tipo_log, numero, wamid)
        return True, wamid

    def upload_midia_whatsapp(self, file_bytes: bytes, mime_type: str, filename: str) -> tuple[bool, str | None]:
        media_id = f"media.dev.{uuid4().hex}"
        log.info("[DEV] Upload de mídia simulado: %s (%s, %d bytes) -> %s",
                 filename, mime_type, len(file_bytes), media_id)
        return True, media_id
