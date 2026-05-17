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


def _iso_utc(dt) -> str | None:
    """
    Serializa datetime como ISO 8601 COM sufixo Z (timezone UTC explícito).
    Os timestamps no DB são gravados com datetime.now(timezone.utc) mas MySQL
    armazena DateTime como naive (sem tz info). Sem sufixo Z, JavaScript
    interpreta como horário LOCAL ao parsear, dando defasagem de 3h em BR.
    """
    if dt is None:
        return None
    # Se já tem tzinfo, usa direto; senão assume UTC (default das colunas).
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.isoformat()
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field, field_validator
from sqlalchemy.orm import Session
from sqlalchemy import func, text

from db.database import get_db
from db.models import Atendente, Usuario, HistoricoConversa, NotaInterna
from services.whatsapp import WhatsAppSender
from services.notificador import notificador
from api.auth import (
    atendente_atual,
    verificar_senha,
    criar_token,
    hash_senha,
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
    ultimo_login: str | None = None


class EnviarMensagemIn(BaseModel):
    texto: str = Field(..., min_length=1, max_length=4096)


class TagIn(BaseModel):
    tag: str | None = None


class NotaIn(BaseModel):
    texto: str = Field(..., min_length=1, max_length=4096)

    @field_validator("texto")
    @classmethod
    def texto_nao_vazio(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("Texto não pode conter apenas espaços")
        return v


class CriarAtendenteIn(BaseModel):
    nome: str = Field(..., min_length=1, max_length=100)
    usuario_login: str = Field(..., min_length=3, max_length=50, pattern=r'^[a-z0-9_]+$')
    senha: str = Field(..., min_length=8, max_length=128)


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

    ultimo_login_anterior = _iso_utc(atendente.ultimo_login)
    atendente.ultimo_login = datetime.now(timezone.utc)
    db.commit()
    token = criar_token(atendente)
    log.info("Login OK: atendente_id=%s nome=%s", atendente.id, atendente.nome)
    return LoginOut(token=token, nome=atendente.nome, atendente_id=atendente.id, ultimo_login=ultimo_login_anterior)


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

    # Ordena via text() literal pra evitar renderização "NULLS LAST" do SQLAlchemy 2.x
    # (sintaxe Postgres incompatível com MySQL). MySQL DESC já põe NULLs no fim.
    rows = (
        db.query(Usuario, sub_ultima.c.ultima)
        .outerjoin(sub_ultima, sub_ultima.c.telefone == Usuario.telefone)
        .order_by(text("usuarios.aguardando_humano DESC"), text("usuarios.data_ultima_interacao DESC"))
        .limit(200)
        .all()
    )

    # Preview da última mensagem por conversa: 1 query batch, melhor que N+1.
    telefones = [u.telefone for u, _ in rows]
    previews: dict[str, str] = {}
    if telefones:
        # Busca a última msg de cada telefone (joina com max criado_em por telefone).
        sub_max = (
            db.query(
                HistoricoConversa.telefone_usuario.label("tel"),
                func.max(HistoricoConversa.criado_em).label("max_em"),
            )
            .filter(HistoricoConversa.telefone_usuario.in_(telefones))
            .group_by(HistoricoConversa.telefone_usuario)
            .subquery()
        )
        msgs = (
            db.query(HistoricoConversa)
            .join(
                sub_max,
                (HistoricoConversa.telefone_usuario == sub_max.c.tel)
                & (HistoricoConversa.criado_em == sub_max.c.max_em),
            )
            .all()
        )
        for m in msgs:
            texto = m.mensagem_cliente or m.resposta_bot or ""
            # Remove tags <br> e quebras pra preview de uma linha.
            texto = re.sub(r"<\s*br\s*/?\s*>", " ", texto, flags=re.IGNORECASE)
            texto = re.sub(r"\s+", " ", texto).strip()
            if len(texto) > 60:
                texto = texto[:57] + "…"
            previews[m.telefone_usuario] = texto

    return [
        {
            "telefone": u.telefone,
            "nome": u.nome_cliente,
            "bot_ativo": bool(u.bot_ativo),
            "aguardando_humano": bool(u.aguardando_humano),
            "atendente_id": u.atendente_id,
            "assumida_por_mim": u.atendente_id == me.id,
            "transbordo_em": _iso_utc(u.transbordo_em),
            "ultima_mensagem_em": _iso_utc(ultima),
            "preview": previews.get(u.telefone, ""),
            "tag": u.tag,
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
            "tag": user.tag,
        },
        "mensagens": [
            {
                "id": m.id,
                "cliente": m.mensagem_cliente,
                "resposta": m.resposta_bot,
                "origem": m.origem or "bot",
                "atendente_id": m.atendente_id,
                "entregue": m.entregue,
                "criado_em": _iso_utc(m.criado_em),
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
        raise HTTPException(status_code=409, detail="Conversa já assumida por outro atendente.")

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
    ok = whatsapp.enviar_mensagem_texto(telefone, aviso)
    db.add(HistoricoConversa(
        telefone_usuario=telefone,
        mensagem_cliente=None,
        resposta_bot=aviso,
        origem="humano",
        atendente_id=me.id,
        entregue=bool(ok),
    ))
    db.commit()

    notificador.publicar({
        "tipo": "atendente_assumiu",
        "telefone": telefone,
        "atendente_id": me.id,
        "atendente_nome": me.nome,
    })
    notificador.publicar({
        "tipo": "nova_mensagem",
        "telefone": telefone,
        "nome": user.nome_cliente,
        "texto": aviso,
        "origem": "humano",
        "atendente_id": me.id,
        "entregue": bool(ok),
    })
    return {"status": "ok", "atendente_id": me.id, "entregue": bool(ok)}


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
    ok = whatsapp.enviar_mensagem_texto(telefone, texto)

    db.add(HistoricoConversa(
        telefone_usuario=telefone,
        mensagem_cliente=None,
        resposta_bot=texto,
        origem="humano",
        atendente_id=me.id,
        entregue=bool(ok),
    ))
    db.commit()

    notificador.publicar({
        "tipo": "nova_mensagem",
        "telefone": telefone,
        "nome": user.nome_cliente,
        "texto": texto,
        "origem": "humano",
        "atendente_id": me.id,
        "entregue": bool(ok),
    })
    return {"status": "ok", "entregue": bool(ok)}


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

    # UPDATE condicional PRIMEIRO: garante que só um request vence a corrida.
    # Se dois requests simultâneos chegarem, apenas um terá afetadas=1.
    # Só enviamos o aviso WhatsApp após confirmar que somos o vencedor,
    # eliminando o double-send do aviso de despedida.
    # Trade-off aceito: bot fica ativo antes do aviso chegar (~<1s HTTP Meta API).
    # Esse janela é menor que o risco de dois avisos confundir o cliente.
    afetadas = (
        db.query(Usuario)
        .filter(Usuario.telefone == telefone, Usuario.atendente_id == me.id)
        .update(
            {
                "atendente_id": None,
                "bot_ativo": True,
                "bot_desativado_em": None,
                "aguardando_humano": False,
                "transbordo_em": None,
            },
            synchronize_session=False,
        )
    )
    db.commit()
    if afetadas == 0:
        raise HTTPException(status_code=409, detail="Conversa não está sob seu atendimento.")

    aviso = "Atendimento humano encerrado. O assistente virtual está de volta e pronto para te ajudar."
    ok = whatsapp.enviar_mensagem_texto(telefone, aviso)
    db.add(HistoricoConversa(
        telefone_usuario=telefone,
        mensagem_cliente=None,
        resposta_bot=aviso,
        origem="humano",
        atendente_id=me.id,
        entregue=bool(ok),
    ))
    db.commit()
    notificador.publicar({
        "tipo": "nova_mensagem",
        "telefone": telefone,
        "nome": user.nome_cliente,
        "texto": aviso,
        "origem": "humano",
        "atendente_id": me.id,
        "entregue": bool(ok),
    })
    notificador.publicar({
        "tipo": "bot_devolveu",
        "telefone": telefone,
    })
    return {"status": "ok"}


@router.get("/cliente/{telefone}/info")
def info_cliente(
    telefone: str,
    db: Session = Depends(get_db),
    _me: Atendente = Depends(atendente_atual),
):
    """
    Retorna metadados do cliente para o painel lateral de informações do dashboard.

    Inclui stats agregadas (total de mensagens, atendimentos humanos) e uma URL
    de avatar DiceBear gerada deterministicamente via nome/telefone — sem chamadas
    externas em runtime, sem TTL, sem escrita em banco.
    """
    user = db.query(Usuario).filter(Usuario.telefone == telefone).first()
    if not user:
        raise HTTPException(status_code=404, detail="Cliente não encontrado")

    # Contagens — duas queries simples, índice composto já existe em historico_conversas.
    total_mensagens = (
        db.query(func.count(HistoricoConversa.id))
        .filter(HistoricoConversa.telefone_usuario == telefone)
        .scalar()
        or 0
    )
    total_atendimentos_humanos = (
        db.query(func.count(HistoricoConversa.id))
        .filter(
            HistoricoConversa.telefone_usuario == telefone,
            HistoricoConversa.origem == "humano",
        )
        .scalar()
        or 0
    )

    foto_url = whatsapp.gerar_url_avatar(user.nome_cliente, telefone)

    return {
        "telefone": user.telefone,
        "nome_cliente": user.nome_cliente,
        "criado_em": _iso_utc(user.criado_em),
        "data_ultima_interacao": _iso_utc(user.data_ultima_interacao),
        "tag": user.tag,
        "bot_ativo": bool(user.bot_ativo),
        "aguardando_humano": bool(user.aguardando_humano),
        "atendente_id": user.atendente_id,
        "total_mensagens": int(total_mensagens),
        "total_atendimentos_humanos": int(total_atendimentos_humanos),
        "foto_url": foto_url,
    }


@router.patch("/conversa/{telefone}/tag")
def atualizar_tag(
    telefone: str,
    body: TagIn,
    db: Session = Depends(get_db),
    atendente: Atendente = Depends(atendente_atual),
):
    """Define ou remove a tag de uma conversa ('resolvido', 'follow_up' ou None)."""
    tag = body.tag
    if tag not in ("resolvido", "follow_up", None):
        raise HTTPException(400, "Tag inválida")
    user = db.query(Usuario).filter(Usuario.telefone == telefone).first()
    if not user:
        raise HTTPException(404, "Usuário não encontrado")
    user.tag = tag
    db.commit()
    return {"ok": True, "tag": tag}


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


# ---------------------------------------------------------------------------
# TASK-020: Gerenciamento de atendentes
# ---------------------------------------------------------------------------

@router.get("/atendentes")
async def listar_atendentes(db: Session = Depends(get_db), _: Atendente = Depends(atendente_atual)):
    """Lista todos os atendentes ordenados pelo nome."""
    atendentes = db.query(Atendente).order_by(Atendente.nome).all()
    return [
        {
            "id": a.id,
            "nome": a.nome,
            "usuario_login": a.usuario_login,
            "ativo": a.ativo,
            "criado_em": _iso_utc(a.criado_em),
            "ultimo_login": _iso_utc(a.ultimo_login),
        }
        for a in atendentes
    ]


@router.post("/atendentes", status_code=201)
async def criar_atendente(body: CriarAtendenteIn, db: Session = Depends(get_db), _: Atendente = Depends(atendente_atual)):
    """Cria um novo atendente. Requer nome, usuario_login e senha (mín. 8 chars)."""
    if db.query(Atendente).filter(Atendente.usuario_login == body.usuario_login).first():
        raise HTTPException(409, "Login já existe")
    novo = Atendente(nome=body.nome.strip(), usuario_login=body.usuario_login, senha_hash=hash_senha(body.senha), ativo=True)
    db.add(novo)
    db.commit()
    db.refresh(novo)
    return {"id": novo.id, "nome": novo.nome, "usuario_login": novo.usuario_login}


@router.patch("/atendentes/{atendente_id}/desativar")
async def desativar_atendente(atendente_id: int, db: Session = Depends(get_db), atual: Atendente = Depends(atendente_atual)):
    """Desativa um atendente. Não é permitido desativar a própria conta."""
    if atual.id == atendente_id:
        raise HTTPException(400, "Não é possível desativar sua própria conta")
    a = db.query(Atendente).filter(Atendente.id == atendente_id).first()
    if not a:
        raise HTTPException(404, "Atendente não encontrado")
    a.ativo = False
    # Libera conversas abertas do atendente desativado para evitar que clientes
    # fiquem em limbo (bot_ativo=False sem atendente ativo).
    db.query(Usuario).filter(
        Usuario.atendente_id == atendente_id,
        Usuario.bot_ativo == False,
    ).update(
        {
            "atendente_id": None,
            "bot_ativo": True,
            "aguardando_humano": False,
        },
        synchronize_session=False,
    )
    db.commit()
    return {"ok": True}


# ---------------------------------------------------------------------------
# TASK-015: Notas internas por cliente
# ---------------------------------------------------------------------------

@router.get("/notas/{telefone}")
async def listar_notas(telefone: str, db: Session = Depends(get_db), _: Atendente = Depends(atendente_atual)):
    """Lista as notas internas de um cliente em ordem decrescente de criação."""
    notas = (
        db.query(NotaInterna)
        .filter(NotaInterna.telefone_usuario == telefone)
        .order_by(NotaInterna.criado_em.desc())
        .all()
    )
    return [
        {
            "id": n.id,
            "texto": n.texto,
            "atendente_id": n.atendente_id,
            "criado_em": _iso_utc(n.criado_em),
        }
        for n in notas
    ]


@router.post("/notas/{telefone}", status_code=201)
async def criar_nota(telefone: str, body: NotaIn, db: Session = Depends(get_db), atual: Atendente = Depends(atendente_atual)):
    """Registra uma nova nota interna para o cliente identificado pelo telefone."""
    nota = NotaInterna(telefone_usuario=telefone, atendente_id=atual.id, texto=body.texto.strip())
    db.add(nota)
    db.commit()
    return {"ok": True}
