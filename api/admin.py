"""
Endpoints do dashboard de atendente humano (modo híbrido).

Autenticação: JWT Bearer em todas as rotas exceto /admin/login.
Concorrência: assumir/devolver usa UPDATE condicional para evitar duas pessoas pegarem
              o mesmo cliente.
SSE: /admin/eventos/stream entrega eventos publicados por services.notificador.
"""
import re
import logging
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from sqlalchemy import func

from db.database import get_db
from db.models import Atendente, Usuario, HistoricoConversa
from services.whatsapp import WhatsAppSender
from services.notificador import notificador
from api.auth import (
    atendente_atual,
    verificar_senha,
    criar_token,
    login_rate_limited,
)

log = logging.getLogger("barbearia.admin")

router = APIRouter(prefix="/admin", tags=["admin"])
whatsapp = WhatsAppSender()


class LoginIn(BaseModel):
    usuario_login: str
    senha: str


class LoginOut(BaseModel):
    token: str
    nome: str
    atendente_id: int


class EnviarMensagemIn(BaseModel):
    texto: str = Field(..., min_length=1, max_length=4096)


def _normalizar_resposta_humana(texto: str) -> str:
    """Atendente digita texto natural (\\n). WhatsApp aceita \\n direto, então só limpamos."""
    return re.sub(r"\n{3,}", "\n\n", texto).strip()


@router.post("/login", response_model=LoginOut)
def login(payload: LoginIn, request: Request, db: Session = Depends(get_db)):
    # Bloqueia login com JWT_SECRET ausente: sem isso, criar_token assinaria com
    # string vazia e qualquer um conseguiria forjar tokens válidos.
    from api.auth import JWT_SECRET
    if not JWT_SECRET:
        log.error("Tentativa de login com JWT_SECRET ausente — bloqueado.")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Servidor não configurado: JWT_SECRET ausente.",
        )
    ip = request.client.host if request.client else "unknown"
    if login_rate_limited(ip):
        log.warning("Rate limit de login excedido para IP %s", ip)
        raise HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail="Muitas tentativas. Tente novamente em 1 minuto.")

    atendente = db.query(Atendente).filter(Atendente.usuario_login == payload.usuario_login.lower()).first()
    if not atendente or not atendente.ativo or not verificar_senha(payload.senha, atendente.senha_hash):
        log.warning("Login inválido para usuario_login=%r de IP %s", payload.usuario_login, ip)
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Credenciais inválidas")

    token = criar_token(atendente)
    log.info("Login OK: atendente_id=%s nome=%s", atendente.id, atendente.nome)
    return LoginOut(token=token, nome=atendente.nome, atendente_id=atendente.id)


@router.get("/conversas")
def listar_conversas(
    db: Session = Depends(get_db),
    me: Atendente = Depends(atendente_atual),
):
    """
    Lista conversas ordenadas por:
    1) aguardando_humano DESC (fila vermelha primeiro)
    2) última mensagem DESC

    Retorna metadados (não o histórico completo) para a sidebar.
    """
    sub_ultima = (
        db.query(
            HistoricoConversa.telefone_usuario.label("telefone"),
            func.max(HistoricoConversa.criado_em).label("ultima"),
        )
        .group_by(HistoricoConversa.telefone_usuario)
        .subquery()
    )

    rows = (
        db.query(Usuario, sub_ultima.c.ultima)
        .outerjoin(sub_ultima, sub_ultima.c.telefone == Usuario.telefone)
        .order_by(
            Usuario.aguardando_humano.desc(),
            sub_ultima.c.ultima.desc().nullslast(),
        )
        .limit(200)
        .all()
    )

    return [
        {
            "telefone": u.telefone,
            "nome": u.nome_cliente,
            "bot_ativo": bool(u.bot_ativo),
            "aguardando_humano": bool(u.aguardando_humano),
            "atendente_id": u.atendente_id,
            "assumida_por_mim": u.atendente_id == me.id,
            "transbordo_em": u.transbordo_em.isoformat() if u.transbordo_em else None,
            "ultima_mensagem_em": ultima.isoformat() if ultima else None,
        }
        for u, ultima in rows
    ]


@router.get("/conversa/{telefone}")
def ver_conversa(
    telefone: str,
    db: Session = Depends(get_db),
    _me: Atendente = Depends(atendente_atual),
):
    user = db.query(Usuario).filter(Usuario.telefone == telefone).first()
    if not user:
        raise HTTPException(status_code=404, detail="Cliente não encontrado")

    msgs = (
        db.query(HistoricoConversa)
        .filter(HistoricoConversa.telefone_usuario == telefone)
        .order_by(HistoricoConversa.criado_em.asc())
        .limit(500)
        .all()
    )

    return {
        "usuario": {
            "telefone": user.telefone,
            "nome": user.nome_cliente,
            "bot_ativo": bool(user.bot_ativo),
            "aguardando_humano": bool(user.aguardando_humano),
            "atendente_id": user.atendente_id,
        },
        "mensagens": [
            {
                "id": m.id,
                "cliente": m.mensagem_cliente,
                "resposta": m.resposta_bot,
                "origem": m.origem or "bot",
                "atendente_id": m.atendente_id,
                "criado_em": m.criado_em.isoformat() if m.criado_em else None,
            }
            for m in msgs
        ],
    }


@router.post("/assumir/{telefone}")
def assumir(
    telefone: str,
    db: Session = Depends(get_db),
    me: Atendente = Depends(atendente_atual),
):
    """
    Atendente assume a conversa. UPDATE condicional impede que dois atendentes
    peguem o mesmo cliente simultaneamente.
    """
    user = db.query(Usuario).filter(Usuario.telefone == telefone).first()
    if not user:
        raise HTTPException(status_code=404, detail="Cliente não encontrado")
    if user.atendente_id and user.atendente_id != me.id:
        raise HTTPException(status_code=409, detail=f"Conversa já assumida por outro atendente (id={user.atendente_id})")

    afetadas = (
        db.query(Usuario)
        .filter(Usuario.telefone == telefone, Usuario.atendente_id.is_(None))
        .update(
            {
                "atendente_id": me.id,
                "bot_ativo": False,
                "bot_desativado_em": datetime.now(timezone.utc),
                "aguardando_humano": False,
            },
            synchronize_session=False,
        )
    )
    db.commit()

    if afetadas == 0 and user.atendente_id != me.id:
        raise HTTPException(status_code=409, detail="Outro atendente assumiu essa conversa antes de você.")

    aviso = f"👋 Olá! Sou {me.nome}, do atendimento da Barbearia Bolshoi. Vou te ajudar a partir de agora."
    whatsapp.enviar_mensagem_texto(telefone, aviso)
    db.add(HistoricoConversa(
        telefone_usuario=telefone,
        mensagem_cliente=None,
        resposta_bot=aviso,
        origem="humano",
        atendente_id=me.id,
    ))
    db.commit()

    notificador.publicar({
        "tipo": "atendente_assumiu",
        "telefone": telefone,
        "atendente_id": me.id,
        "atendente_nome": me.nome,
    })
    return {"status": "ok", "atendente_id": me.id}


@router.post("/enviar/{telefone}")
def enviar(
    telefone: str,
    payload: EnviarMensagemIn,
    db: Session = Depends(get_db),
    me: Atendente = Depends(atendente_atual),
):
    user = db.query(Usuario).filter(Usuario.telefone == telefone).first()
    if not user:
        raise HTTPException(status_code=404, detail="Cliente não encontrado")
    if user.atendente_id != me.id:
        raise HTTPException(status_code=403, detail="Você não assumiu essa conversa.")

    texto = _normalizar_resposta_humana(payload.texto)
    whatsapp.enviar_mensagem_texto(telefone, texto)

    db.add(HistoricoConversa(
        telefone_usuario=telefone,
        mensagem_cliente=None,
        resposta_bot=texto,
        origem="humano",
        atendente_id=me.id,
    ))
    db.commit()

    notificador.publicar({
        "tipo": "nova_mensagem",
        "telefone": telefone,
        "nome": user.nome_cliente,
        "texto": texto,
        "origem": "humano",
        "atendente_id": me.id,
    })
    return {"status": "ok"}


@router.post("/devolver/{telefone}")
def devolver(
    telefone: str,
    db: Session = Depends(get_db),
    me: Atendente = Depends(atendente_atual),
):
    """Atendente libera a conversa: bot volta a responder."""
    user = db.query(Usuario).filter(Usuario.telefone == telefone).first()
    if not user:
        raise HTTPException(status_code=404, detail="Cliente não encontrado")
    if user.atendente_id != me.id:
        raise HTTPException(status_code=403, detail="Você não é o atendente dessa conversa.")

    # ORDEM CRÍTICA: avisa o cliente PRIMEIRO, com bot ainda inativo.
    # Se reativássemos o bot antes, uma mensagem do cliente entre o commit e o envio
    # do WhatsApp poderia disparar a IA antes do aviso de "humano saiu" chegar.
    aviso = "Atendimento humano encerrado. A IA está de volta e pronta pra te ajudar! 🤖"
    whatsapp.enviar_mensagem_texto(telefone, aviso)
    db.add(HistoricoConversa(
        telefone_usuario=telefone,
        mensagem_cliente=None,
        resposta_bot=aviso,
        origem="humano",
        atendente_id=me.id,
    ))
    db.commit()

    # Agora sim libera o bot.
    user.atendente_id = None
    user.bot_ativo = True
    user.bot_desativado_em = None
    user.aguardando_humano = False
    user.transbordo_em = None
    db.commit()

    notificador.publicar({
        "tipo": "bot_devolveu",
        "telefone": telefone,
    })
    return {"status": "ok"}


@router.get("/eventos/stream")
def stream_eventos(_me: Atendente = Depends(atendente_atual)):
    """Server-Sent Events. Cliente conecta com EventSource()."""
    fila = notificador.assinar()
    return StreamingResponse(
        notificador.stream(fila),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
            "Connection": "keep-alive",
        },
    )
