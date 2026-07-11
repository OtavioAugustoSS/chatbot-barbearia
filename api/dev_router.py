"""
Rotas do simulador de chat local — SOMENTE modo dev (sem credenciais Meta).

Montadas por main.py apenas quando config.WHATSAPP_FAKE e APP_ENV != production.
O simulador injeta mensagens no pipeline REAL do webhook (processar_evento_webhook)
como se viessem da Meta, e lê as respostas capturadas pelo DevWhatsAppSender no
outbox em memória. Nada aqui toca a rede.
"""
import time
from pathlib import Path
from typing import Literal
from uuid import uuid4

from fastapi import APIRouter, BackgroundTasks, Depends
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from api.webhook import processar_evento_webhook
from core import config
from db.database import get_db
from services.dev_sender import outbox_dev

router = APIRouter(prefix="/dev", tags=["dev"])

_SIMULADOR_HTML = Path(__file__).parent.parent / "static" / "dev" / "simulador.html"


class MensagemSimulada(BaseModel):
    telefone: str = Field(default="5538999990000", max_length=20)
    nome: str = Field(default="Cliente Demo", max_length=100)
    texto: str = Field(min_length=1, max_length=4096)


def _montar_payload_meta(telefone: str, nome: str, texto: str, message_id: str) -> dict:
    """Payload no formato Meta Cloud API (mesmo shape usado nos testes de pipeline)."""
    return {
        "object": "whatsapp_business_account",
        "entry": [{
            "id": "dev-entry",
            "changes": [{
                "field": "messages",
                "value": {
                    "messaging_product": "whatsapp",
                    "metadata": {"display_phone_number": "0000000000", "phone_number_id": "dev"},
                    "contacts": [{"profile": {"name": nome}, "wa_id": telefone}],
                    "messages": [{
                        "from": telefone,
                        "id": message_id,
                        "timestamp": str(int(time.time())),
                        "type": "text",
                        "text": {"body": texto},
                    }],
                },
            }],
        }],
    }


def _montar_payload_status(wamid: str, status: str, telefone: str) -> dict:
    """Payload de status update no formato Meta (value.statuses[])."""
    return {
        "object": "whatsapp_business_account",
        "entry": [{
            "id": "dev-entry",
            "changes": [{
                "field": "messages",
                "value": {
                    "messaging_product": "whatsapp",
                    "metadata": {"phone_number_id": "dev"},
                    "statuses": [{
                        "id": wamid,
                        "status": status,
                        "timestamp": str(int(time.time())),
                        "recipient_id": telefone,
                    }],
                },
            }],
        }],
    }


@router.post("/api/mensagem")
async def enviar_mensagem_simulada(
    msg: MensagemSimulada,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    """Injeta uma mensagem do 'cliente' no pipeline real do webhook.

    IDs de menu (MENU_*, SUB_*) enviados como texto reproduzem o clique em
    lista/botão — o extractor do webhook converte list_reply/button_reply para
    o mesmo id-string, então o despacho é idêntico.
    """
    message_id = f"wamid.devsim.{uuid4().hex}"
    body = _montar_payload_meta(msg.telefone, msg.nome, msg.texto, message_id)
    resultado = await processar_evento_webhook(body, background_tasks, db)
    # wamid devolvido: o simulador ancora a bolha do cliente para o read receipt.
    return {"status": resultado.get("status", "ok"), "telefone": msg.telefone, "wamid": message_id}


class StatusSimulado(BaseModel):
    wamid: str = Field(min_length=1, max_length=255)
    status: Literal["delivered", "read", "failed"]
    telefone: str = Field(default="5538999990000", max_length=20)


@router.post("/api/status")
async def simular_status(
    st: StatusSimulado,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    """Simula o status update que a Meta enviaria (delivered/read/failed) para
    uma mensagem do bot — percorre o MESMO pipeline do webhook de produção."""
    body = _montar_payload_status(st.wamid, st.status, st.telefone)
    resultado = await processar_evento_webhook(body, background_tasks, db)
    return {"status": resultado.get("status", "ok"), "wamid": st.wamid, "aplicado": st.status}


@router.get("/api/respostas")
def listar_respostas(telefone: str, desde_seq: int = 0):
    """Polling incremental do outbox: tudo que o bot 'enviou' para este telefone."""
    eventos = outbox_dev.listar(telefone=telefone, desde_seq=desde_seq)
    ultimo_seq = eventos[-1]["seq"] if eventos else desde_seq
    return {"eventos": eventos, "ultimo_seq": ultimo_seq}


@router.get("/api/estado")
def estado_dev():
    """Estado do modo dev — consumido pelo banner do simulador."""
    return {
        "modo_dev": config.MODO_DEV,
        "modo_operacao": config.MODO_OPERACAO,
        "db_sqlite": config.DB_SQLITE_DEV,
        "ia_fake": config.IA_FAKE,
        "whatsapp_fake": config.WHATSAPP_FAKE,
        "jwt_efemero": config.JWT_SECRET_EFEMERO,
        "dashboard_url": "/static/admin/login.html" if config.MODO_HIBRIDO else None,
    }


@router.get("/simulador")
def pagina_simulador():
    return FileResponse(str(_SIMULADOR_HTML), media_type="text/html")
