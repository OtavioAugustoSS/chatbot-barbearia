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
from typing import Optional, Literal
from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, Request, UploadFile, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field, field_validator
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func, text


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

from db.database import get_db
from db.models import Atendente, Usuario, HistoricoConversa, NotaInterna, Label, usuario_labels, CannedResponse, MentionNotificacao, FiltroSalvo, Horario
import json as _json_lib
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


class LabelIn(BaseModel):
    nome: str = Field(..., min_length=1, max_length=50, pattern=r'^[a-z0-9_\-]+$')
    cor: str = Field(..., pattern=r'^#[0-9a-fA-F]{6}$')
    descricao: str | None = Field(None, max_length=200)


class LabelPatchIn(BaseModel):
    nome: str | None = Field(None, min_length=1, max_length=50, pattern=r'^[a-z0-9_\-]+$')
    cor: str | None = Field(None, pattern=r'^#[0-9a-fA-F]{6}$')
    descricao: str | None = Field(None, max_length=200)
    ativo: bool | None = None


class AssignLabelIn(BaseModel):
    label_id: int


class StatusConversaIn(BaseModel):
    status: Literal["open", "pending", "resolved", "snoozed"]
    snoozed_until: str | None = None  # ISO 8601 — obrigatório se status == "snoozed"


class CannedIn(BaseModel):
    atalho: str = Field(..., min_length=2, max_length=30, pattern=r'^/[a-z0-9_\-]+$')
    texto: str = Field(..., min_length=1, max_length=4096)
    escopo: Literal["global", "pessoal"] = "pessoal"


class CannedPatchIn(BaseModel):
    atalho: str | None = Field(None, min_length=2, max_length=30, pattern=r'^/[a-z0-9_\-]+$')
    texto: str | None = Field(None, min_length=1, max_length=4096)
    escopo: Literal["global", "pessoal"] | None = None


class AtribuirIn(BaseModel):
    atendente_id: int


class PresenceIn(BaseModel):
    status: Literal["online", "away", "offline"]
    # P2-7b: JWT no body (e não em query) como fallback p/ navigator.sendBeacon,
    # que não envia headers. Body não vaza em access log; query param vazava.
    token: str | None = None


class BulkIn(BaseModel):
    telefones: list[str] = Field(..., min_length=1, max_length=200)
    acao: Literal["resolver", "atribuir", "label_add", "label_remove", "snooze"]
    parametros: dict = Field(default_factory=dict)


class ViewIn(BaseModel):
    nome: str = Field(..., min_length=1, max_length=50)
    criterios: dict
    ordem: int = 0


class ViewPatchIn(BaseModel):
    nome: str | None = Field(None, min_length=1, max_length=50)
    criterios: dict | None = None
    ordem: int | None = None


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
    # Dummy bcrypt quando o usuário não existe — evita timing side-channel por enumeração.
    # Custo idêntico ao de verificar_senha() real, tornando ambos os paths iguais em tempo.
    if not atendente:
        verificar_senha(payload.senha, "$2b$12$dummyhashfortimingequalityxxxxxxxxxxxxxxxxxxxxxxxx")
        log.warning("Login inválido para usuario_login=%r de IP %s", payload.usuario_login, ip)
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Credenciais inválidas")
    if not atendente.ativo or not verificar_senha(payload.senha, atendente.senha_hash):
        log.warning("Login inválido para usuario_login=%r de IP %s", payload.usuario_login, ip)
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Credenciais inválidas")

    ultimo_login_anterior = _iso_utc(atendente.ultimo_login)
    atendente.ultimo_login = datetime.now(timezone.utc)
    db.commit()
    token = criar_token(atendente)
    log.info("Login OK: atendente_id=%s nome=%s", atendente.id, atendente.nome)
    return LoginOut(token=token, nome=atendente.nome, atendente_id=atendente.id, ultimo_login=ultimo_login_anterior)


def _auto_unsnooze(db: Session) -> None:
    """Conversas com snoozed_until vencido voltam para status open automaticamente."""
    agora = datetime.now(timezone.utc)
    db.query(Usuario).filter(
        Usuario.status_conversa == "snoozed",
        Usuario.snoozed_until.isnot(None),
        Usuario.snoozed_until <= agora,
    ).update(
        {"status_conversa": "open", "snoozed_until": None},
        synchronize_session=False,
    )
    db.commit()


@router.get("/conversas")
def listar_conversas(
    db: Session = Depends(get_db),
    me: Atendente = Depends(atendente_atual),
    estado: Optional[Literal["aguardando", "meus", "bot", "outros", "todas"]] = Query(
        None,
        description=(
            "Filtra conversas: aguardando=fila humana, meus=minhas, bot=só bot, "
            "outros=outro atendente, todas/None=sem filtro"
        ),
    ),
    status_filter: Optional[Literal["open", "pending", "resolved", "snoozed", "todas"]] = Query(
        "open",
        alias="status",
        description=(
            "Filtra por status_conversa: open (default), pending, resolved, snoozed ou 'todas' (sem filtro)"
        ),
    ),
    page: int = Query(1, ge=1, description="Página (começa em 1)"),
    per_page: int = Query(50, ge=1, le=200, description="Resultados por página (máx 200)"),
):
    """
    Lista conversas ordenadas por:
    1) aguardando_humano DESC (fila vermelha primeiro)
    2) última mensagem DESC

    GAP-02: Filtro opcional por estado (aguardando, meus, bot, outros, todas).
    GAP-03: Paginação com envelope — retorna {items, page, per_page, total,
            has_more, totais_por_estado}.
    """
    # GAP-02: validação explícita — valor inválido já é barrado pelo Literal do FastAPI,
    # mas garantimos 400 claro para qualquer bypass (ex.: via test client sem Pydantic).
    _estados_validos = {"aguardando", "meus", "bot", "outros", "todas", None}
    if estado not in _estados_validos:
        raise HTTPException(status_code=400, detail=f"Estado inválido: {estado!r}. Use: aguardando, meus, bot, outros, todas")

    # Auto-unsnooze: rebatas conversas snoozed cujo prazo expirou.
    _auto_unsnooze(db)

    sub_ultima = (
        db.query(
            HistoricoConversa.telefone_usuario.label("telefone"),
            func.max(HistoricoConversa.criado_em).label("ultima"),
        )
        .group_by(HistoricoConversa.telefone_usuario)
        .subquery()
    )

    # Query base — filtros de estado aplicados antes de paginar.
    # Ordena via text() literal pra evitar renderização "NULLS LAST" do SQLAlchemy 2.x
    # (sintaxe Postgres incompatível com MySQL). MySQL DESC já põe NULLs no fim.
    base_q = (
        db.query(Usuario, sub_ultima.c.ultima)
        .outerjoin(sub_ultima, sub_ultima.c.telefone == Usuario.telefone)
    )

    # GAP-02: aplica filtro por estado
    if estado == "aguardando":
        base_q = base_q.filter(Usuario.aguardando_humano == True)
    elif estado == "meus":
        base_q = base_q.filter(Usuario.atendente_id == me.id)
    elif estado == "bot":
        base_q = base_q.filter(
            Usuario.bot_ativo == True,
            Usuario.aguardando_humano == False,
            Usuario.atendente_id.is_(None),
        )
    elif estado == "outros":
        base_q = base_q.filter(
            Usuario.atendente_id.isnot(None),
            Usuario.atendente_id != me.id,
        )
    # "todas" e None: sem filtro adicional

    # Filtro por status_conversa (ortogonal ao filtro de estado).
    # Default: "open" (esconde resolved/snoozed do dashboard normal).
    if status_filter and status_filter != "todas":
        base_q = base_q.filter(Usuario.status_conversa == status_filter)

    base_q = base_q.order_by(
        text("usuarios.aguardando_humano DESC"),
        text("usuarios.data_ultima_interacao DESC"),
    )

    # GAP-03: total antes de paginar (conta apenas usuários, não tuplas com ultima)
    total = base_q.count()

    # GAP-03: totais por estado (4 queries simples para cards de métricas)
    def _contar_estado(filtros) -> int:
        q = db.query(func.count(Usuario.telefone))
        for f in filtros:
            q = q.filter(f)
        return q.scalar() or 0

    totais_por_estado = {
        "aguardando": _contar_estado([Usuario.aguardando_humano == True]),
        "meus": _contar_estado([Usuario.atendente_id == me.id]),
        "bot": _contar_estado([
            Usuario.bot_ativo == True,
            Usuario.aguardando_humano == False,
            Usuario.atendente_id.is_(None),
        ]),
        "outros": _contar_estado([
            Usuario.atendente_id.isnot(None),
            Usuario.atendente_id != me.id,
        ]),
    }

    # GAP-03: paginação
    offset = (page - 1) * per_page
    rows = base_q.offset(offset).limit(per_page).all()

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

    # Carrega labels em batch para todas as conversas da página (evita N+1).
    labels_por_telefone: dict[str, list[dict]] = {}
    if telefones:
        from sqlalchemy import select
        join_q = (
            db.query(usuario_labels.c.telefone_usuario, Label)
            .join(Label, Label.id == usuario_labels.c.label_id)
            .filter(usuario_labels.c.telefone_usuario.in_(telefones))
            .filter(Label.ativo == True)
        )
        for tel, lab in join_q.all():
            labels_por_telefone.setdefault(tel, []).append({
                "id": lab.id, "nome": lab.nome, "cor": lab.cor
            })

    items = [
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
            "labels": labels_por_telefone.get(u.telefone, []),
            "status_conversa": u.status_conversa or "open",
            "snoozed_until": _iso_utc(u.snoozed_until),
        }
        for u, ultima in rows
    ]

    return {
        "items": items,
        "page": page,
        "per_page": per_page,
        "total": total,
        "has_more": (offset + len(items)) < total,
        "totais_por_estado": totais_por_estado,
    }


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
        .options(joinedload(HistoricoConversa.atendente))
        .filter(HistoricoConversa.telefone_usuario == telefone)
        .order_by(HistoricoConversa.criado_em.asc())
        .limit(500)
        .all()
    )

    labels_user = [
        {"id": l.id, "nome": l.nome, "cor": l.cor}
        for l in (user.labels or []) if l.ativo
    ]

    return {
        "usuario": {
            "telefone": user.telefone,
            "nome": user.nome_cliente,
            "bot_ativo": bool(user.bot_ativo),
            "aguardando_humano": bool(user.aguardando_humano),
            "atendente_id": user.atendente_id,
            "tag": user.tag,
            "labels": labels_user,
            "status_conversa": user.status_conversa or "open",
            "snoozed_until": _iso_utc(user.snoozed_until),
        },
        "mensagens": [
            {
                "id": m.id,
                "cliente": m.mensagem_cliente,
                "resposta": m.resposta_bot,
                "origem": m.origem or "bot",
                "atendente_id": m.atendente_id,
                "atendente_nome": m.atendente.nome if m.atendente else None,
                "entregue": m.entregue,
                "wamid": m.wamid,
                "lida": m.lida,
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
    if user.atendente_id == me.id:
        raise HTTPException(status_code=400, detail="Você já é o atendente desta conversa.")
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
                "status_conversa": "open",
                "snoozed_until": None,
                "data_ultima_interacao": datetime.now(timezone.utc),
            },
            synchronize_session=False,
        )
    )
    db.commit()

    if afetadas == 0 and user.atendente_id != me.id:
        raise HTTPException(status_code=409, detail="Outro atendente assumiu essa conversa antes de você.")

    aviso = f"👋 Olá! Sou {me.nome}, do atendimento da Barbearia Bolshoi. Vou te ajudar a partir de agora."
    ok, wamid = whatsapp.enviar_mensagem_texto(telefone, aviso)
    db.add(HistoricoConversa(
        telefone_usuario=telefone,
        mensagem_cliente=None,
        resposta_bot=aviso,
        origem="humano",
        atendente_id=me.id,
        entregue=bool(ok),
        wamid=wamid,
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
    # Garante que o dashboard recoloque a conversa no filtro "open" em tempo real,
    # mesmo se ela estava resolved/snoozed antes do atendente assumir (PO).
    notificador.publicar({
        "tipo": "status_alterado",
        "telefone": telefone,
        "status": "open",
        "snoozed_until": None,
        "por_atendente_id": me.id,
    })
    return {"status": "ok", "atendente_id": me.id, "entregue": bool(ok)}


# ============================================================
# SAVED VIEWS — filtros personalizados por atendente
# ============================================================

@router.get("/views")
def listar_views(
    db: Session = Depends(get_db),
    me: Atendente = Depends(atendente_atual),
):
    """Lista views salvas do atendente, ordenadas."""
    views = (
        db.query(FiltroSalvo)
        .filter(FiltroSalvo.atendente_id == me.id)
        .order_by(FiltroSalvo.ordem, FiltroSalvo.criado_em)
        .all()
    )
    return [
        {
            "id": v.id,
            "nome": v.nome,
            "criterios": _json_lib.loads(v.criterios),
            "ordem": v.ordem,
            "criado_em": _iso_utc(v.criado_em),
        }
        for v in views
    ]


@router.post("/views", status_code=201)
def criar_view(
    payload: ViewIn,
    db: Session = Depends(get_db),
    me: Atendente = Depends(atendente_atual),
):
    """Cria nova view. Nome único por atendente."""
    existe = db.query(FiltroSalvo).filter(
        FiltroSalvo.atendente_id == me.id,
        FiltroSalvo.nome == payload.nome,
    ).first()
    if existe:
        raise HTTPException(409, f"Já existe view com nome '{payload.nome}'")
    v = FiltroSalvo(
        atendente_id=me.id,
        nome=payload.nome,
        criterios=_json_lib.dumps(payload.criterios),
        ordem=payload.ordem,
    )
    db.add(v)
    db.commit()
    db.refresh(v)
    return {"id": v.id, "nome": v.nome, "criterios": payload.criterios, "ordem": v.ordem}


@router.patch("/views/{view_id}")
def editar_view(
    view_id: int,
    payload: ViewPatchIn,
    db: Session = Depends(get_db),
    me: Atendente = Depends(atendente_atual),
):
    """Edita view do atendente logado."""
    v = db.query(FiltroSalvo).filter(
        FiltroSalvo.id == view_id,
        FiltroSalvo.atendente_id == me.id,
    ).first()
    if not v:
        raise HTTPException(404, "View não encontrada")
    if payload.nome and payload.nome != v.nome:
        existe = db.query(FiltroSalvo).filter(
            FiltroSalvo.atendente_id == me.id,
            FiltroSalvo.nome == payload.nome,
            FiltroSalvo.id != view_id,
        ).first()
        if existe:
            raise HTTPException(409, f"Já existe view com nome '{payload.nome}'")
        v.nome = payload.nome
    if payload.criterios is not None:
        v.criterios = _json_lib.dumps(payload.criterios)
    if payload.ordem is not None:
        v.ordem = payload.ordem
    db.commit()
    return {"id": v.id, "nome": v.nome, "criterios": _json_lib.loads(v.criterios), "ordem": v.ordem}


@router.delete("/views/{view_id}", status_code=204)
def deletar_view(
    view_id: int,
    db: Session = Depends(get_db),
    me: Atendente = Depends(atendente_atual),
):
    v = db.query(FiltroSalvo).filter(
        FiltroSalvo.id == view_id,
        FiltroSalvo.atendente_id == me.id,
    ).first()
    if not v:
        raise HTTPException(404, "View não encontrada")
    db.delete(v)
    db.commit()
    return None


# ============================================================
# SEARCH GLOBAL — busca em mensagens (HistoricoConversa)
# ============================================================

@router.get("/search")
def search_mensagens(
    q: str = Query(..., min_length=2, max_length=100),
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
    _me: Atendente = Depends(atendente_atual),
):
    """
    Busca em mensagens (mensagem_cliente + resposta_bot) usando LIKE.
    Agrupa por telefone, retorna snippet com trecho destacado.
    MVP: LIKE simples. Se ficar lento (>5s em 50k+ mensagens), migrar para FULLTEXT.
    """
    from sqlalchemy import or_
    q_escaped = q.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
    termo = f"%{q_escaped}%"
    msgs = (
        db.query(HistoricoConversa, Usuario.nome_cliente)
        .outerjoin(Usuario, Usuario.telefone == HistoricoConversa.telefone_usuario)
        .filter(or_(
            HistoricoConversa.mensagem_cliente.like(termo, escape="\\"),
            HistoricoConversa.resposta_bot.like(termo, escape="\\"),
        ))
        .order_by(HistoricoConversa.criado_em.desc())
        .limit(limit)
        .all()
    )

    # Agrupa por telefone, mantendo a msg mais recente como representante
    resultados: dict[str, dict] = {}
    for m, nome in msgs:
        if m.telefone_usuario in resultados:
            continue  # já tem snippet desse telefone
        texto = m.mensagem_cliente or m.resposta_bot or ""
        # Snippet centrado no match
        idx = texto.lower().find(q.lower())
        if idx >= 0:
            inicio = max(0, idx - 40)
            fim = min(len(texto), idx + len(q) + 40)
            snippet = ("…" if inicio > 0 else "") + texto[inicio:fim] + ("…" if fim < len(texto) else "")
        else:
            snippet = texto[:100]

        resultados[m.telefone_usuario] = {
            "telefone": m.telefone_usuario,
            "nome": nome or m.telefone_usuario,
            "snippet": snippet,
            "mensagem_id": m.id,
            "criado_em": _iso_utc(m.criado_em),
            "origem": m.origem or "bot",
        }

    return list(resultados.values())


# ============================================================
# PRESENCE — status online/away/offline em memória
# ============================================================
# Dict in-memory: {atendente_id: (status, last_seen_iso)}.
# Aceita perder estado em restart (não é dado crítico).
# Auto-marca offline após 90s sem heartbeat.
_presence_store: dict[int, tuple[str, datetime]] = {}
_PRESENCE_TIMEOUT_SECS = 90


def _limpar_presence_stale() -> None:
    """Marca como offline atendentes sem heartbeat recente."""
    agora = datetime.now(timezone.utc)
    for aid, (status, last_seen) in list(_presence_store.items()):
        if status != "offline" and (agora - last_seen).total_seconds() > _PRESENCE_TIMEOUT_SECS:
            _presence_store[aid] = ("offline", last_seen)
            notificador.publicar({
                "tipo": "presence_changed",
                "atendente_id": aid,
                "status": "offline",
            })


@router.post("/presence")
def atualizar_presence(
    payload: PresenceIn,
    request: Request,
    db: Session = Depends(get_db),
):
    """
    Heartbeat de presença do atendente. Chamar a cada 30s ou em visibility change.
    Aceita auth via header Authorization (default) ou via `token` no body (P2-7b),
    fallback para navigator.sendBeacon, que não suporta headers customizados em
    beforeunload. O token no body não vaza em access log (a query param vazava).
    """
    from api.auth import _decodificar, JWT_SECRET
    if not JWT_SECRET:
        raise HTTPException(status_code=503, detail="JWT_SECRET não configurado")

    # Tenta header Authorization primeiro; senão, token no body (sendBeacon).
    raw_token = None
    auth_header = request.headers.get("authorization", "")
    if auth_header.lower().startswith("bearer "):
        raw_token = auth_header[7:].strip()
    elif payload.token:
        raw_token = payload.token

    if not raw_token:
        raise HTTPException(status_code=401, detail="Token ausente")

    try:
        jwt_payload = _decodificar(raw_token)
    except HTTPException:
        raise
    sub = jwt_payload.get("sub")
    if not sub:
        raise HTTPException(status_code=401, detail="Token sem sub")
    try:
        atendente_id = int(sub)
    except (TypeError, ValueError):
        raise HTTPException(status_code=401, detail="Token com sub inválido")

    # Valida que o atendente ainda está ativo (paridade com `atendente_atual`).
    # Sem esse check, atendente desativado com JWT válido (até TTL) atualizaria
    # presence e apareceria "online" para os demais.
    atendente = db.query(Atendente).filter(
        Atendente.id == atendente_id,
        Atendente.ativo == True,
    ).first()
    if not atendente:
        raise HTTPException(status_code=401, detail="Atendente inativo ou inexistente")

    agora = datetime.now(timezone.utc)
    anterior = _presence_store.get(atendente_id)
    _presence_store[atendente_id] = (payload.status, agora)

    if not anterior or anterior[0] != payload.status:
        notificador.publicar({
            "tipo": "presence_changed",
            "atendente_id": atendente_id,
            "status": payload.status,
        })
    return {"ok": True}


@router.get("/presence")
def listar_presence(_me: Atendente = Depends(atendente_atual)):
    """Retorna mapa {atendente_id: {status, last_seen}} de todos os atendentes."""
    _limpar_presence_stale()
    return {
        str(aid): {
            "status": status,
            "last_seen": _iso_utc(last_seen),
        }
        for aid, (status, last_seen) in _presence_store.items()
    }


@router.post("/conversas/bulk")
def bulk_acao(
    payload: BulkIn,
    db: Session = Depends(get_db),
    me: Atendente = Depends(atendente_atual),
):
    """
    Aplica ação em lote em múltiplas conversas. Retorna resultado por telefone.
    Ações suportadas:
      - resolver: muda status_conversa para 'resolved'
      - atribuir: parametros.atendente_id (transfere para outro atendente)
      - label_add / label_remove: parametros.label_id
      - snooze: parametros.snoozed_until (ISO 8601)
    """
    resultados = {"sucesso": [], "falha": []}
    agora = datetime.now(timezone.utc)

    for tel in payload.telefones:
        try:
            user = db.query(Usuario).filter(Usuario.telefone == tel).first()
            if not user:
                resultados["falha"].append({"telefone": tel, "erro": "não encontrado"})
                continue

            if payload.acao == "resolver":
                user.status_conversa = "resolved"
                user.resolved_em = agora
                user.resolved_por = me.id

            elif payload.acao == "snooze":
                snooze_iso = payload.parametros.get("snoozed_until")
                if not snooze_iso:
                    resultados["falha"].append({"telefone": tel, "erro": "snoozed_until obrigatório"})
                    continue
                try:
                    dt = datetime.fromisoformat(snooze_iso.replace("Z", "+00:00"))
                    if dt.tzinfo is None:
                        dt = dt.replace(tzinfo=timezone.utc)
                except ValueError:
                    resultados["falha"].append({"telefone": tel, "erro": "snoozed_until inválido"})
                    continue
                user.status_conversa = "snoozed"
                user.snoozed_until = dt

            elif payload.acao == "atribuir":
                dest_id = payload.parametros.get("atendente_id")
                if not dest_id:
                    resultados["falha"].append({"telefone": tel, "erro": "atendente_id obrigatório"})
                    continue
                # Aqui é admin-level: pode reatribuir mesmo sem ser dono.
                user.atendente_id = dest_id
                user.bot_ativo = False
                user.aguardando_humano = False

            elif payload.acao == "label_add":
                lid = payload.parametros.get("label_id")
                if not lid:
                    resultados["falha"].append({"telefone": tel, "erro": "label_id obrigatório"})
                    continue
                # Idempotente: ignora se já existe
                ja = db.execute(
                    usuario_labels.select().where(
                        usuario_labels.c.telefone_usuario == tel,
                        usuario_labels.c.label_id == lid,
                    )
                ).first()
                if not ja:
                    db.execute(usuario_labels.insert().values(
                        telefone_usuario=tel, label_id=lid,
                        atribuido_em=agora, atribuido_por=me.id,
                    ))

            elif payload.acao == "label_remove":
                lid = payload.parametros.get("label_id")
                if not lid:
                    resultados["falha"].append({"telefone": tel, "erro": "label_id obrigatório"})
                    continue
                db.execute(
                    usuario_labels.delete().where(
                        usuario_labels.c.telefone_usuario == tel,
                        usuario_labels.c.label_id == lid,
                    )
                )

            user.data_ultima_interacao = agora
            # BE-03: flush por item mantém as mudanças no buffer da sessão sem
            # commitar. Exceção de DB aqui é capturada abaixo e faz rollback.
            db.flush()
            resultados["sucesso"].append(tel)
        except Exception as exc:
            # BE-03: rollback desfaz o item corrente sem contaminar os anteriores
            # que já foram flushed — a sessão volta ao estado do último flush bem-sucedido.
            db.rollback()
            log.exception("Bulk acao=%s telefone=%s falhou", payload.acao, tel)
            resultados["falha"].append({"telefone": tel, "erro": str(exc)})

    db.commit()

    notificador.publicar({
        "tipo": "bulk_aplicado",
        "acao": payload.acao,
        "afetadas": len(resultados["sucesso"]),
        "por_atendente_id": me.id,
    })

    return resultados


@router.post("/conversa/{telefone}/atribuir")
def atribuir_conversa(
    telefone: str,
    payload: AtribuirIn,
    db: Session = Depends(get_db),
    me: Atendente = Depends(atendente_atual),
):
    """
    Transfere conversa para outro atendente. UPDATE condicional: só quem é dono
    pode transferir. Dispara SSE conversa_atribuida para origem e destino.
    """
    user = db.query(Usuario).filter(Usuario.telefone == telefone).first()
    if not user:
        raise HTTPException(404, "Conversa não encontrada")
    if user.atendente_id != me.id:
        raise HTTPException(403, "Você precisa ser o dono atual para transferir")

    destino = db.query(Atendente).filter(
        Atendente.id == payload.atendente_id,
        Atendente.ativo == True,
    ).first()
    if not destino:
        raise HTTPException(404, "Atendente destino não encontrado ou inativo")
    if destino.id == me.id:
        raise HTTPException(400, "Você já é o dono desta conversa")

    afetadas = (
        db.query(Usuario)
        .filter(Usuario.telefone == telefone, Usuario.atendente_id == me.id)
        .update({"atendente_id": destino.id}, synchronize_session=False)
    )
    db.commit()
    if afetadas == 0:
        raise HTTPException(409, "Conversa não pertence mais a você")

    # Registra evento no histórico (sem mensagem ao cliente)
    db.add(HistoricoConversa(
        telefone_usuario=telefone,
        mensagem_cliente=None,
        resposta_bot=f"[Sistema] Conversa transferida de {me.nome} para {destino.nome}",
        origem="humano",
        intencao="transferencia",
        atendente_id=destino.id,
        entregue=None,
    ))
    db.commit()

    notificador.publicar({
        "tipo": "conversa_atribuida",
        "telefone": telefone,
        "de_atendente_id": me.id,
        "para_atendente_id": destino.id,
        "para_atendente_nome": destino.nome,
    })

    return {"ok": True, "atendente_id": destino.id, "atendente_nome": destino.nome}


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
    # Substitui placeholders ({nome_cliente}, {primeiro_nome}, {atendente}, {barbearia})
    # antes de enviar — atendente pode usar canned responses dinâmicas naturalmente.
    texto = _substituir_placeholders(texto, user, me)
    ok, wamid = whatsapp.enviar_mensagem_texto(telefone, texto)

    db.add(HistoricoConversa(
        telefone_usuario=telefone,
        mensagem_cliente=None,
        resposta_bot=texto,
        origem="humano",
        atendente_id=me.id,
        entregue=bool(ok),
        wamid=wamid,
    ))
    db.commit()

    notificador.publicar({
        "tipo": "nova_mensagem",
        "telefone": telefone,
        "nome": user.nome_cliente,
        "texto": texto,
        "origem": "humano",
        "atendente_id": me.id,
        # C3: atendente_nome necessário para o frontend exibir remetente no separador.
        "atendente_nome": me.nome,
        "entregue": bool(ok),
    })
    return {"status": "ok", "entregue": bool(ok)}


_MIME_PARA_TIPO: dict[str, str] = {
    "image/jpeg": "image", "image/png": "image", "image/webp": "image", "image/gif": "image",
    "application/pdf": "document",
    "audio/ogg": "audio", "audio/mpeg": "audio", "audio/aac": "audio",
    "video/mp4": "video",
}
# C1: extensão → MIME canônico para fallback quando Content-Type é genérico/ausente.
_EXT_PARA_MIME: dict[str, str] = {
    "jpg": "image/jpeg", "jpeg": "image/jpeg", "png": "image/png",
    "webp": "image/webp", "gif": "image/gif", "pdf": "application/pdf",
    "ogg": "audio/ogg", "mp3": "audio/mpeg", "aac": "audio/aac",
    "m4a": "audio/aac", "mp4": "video/mp4",
}
_MAX_MIDIA_BYTES = 16 * 1024 * 1024  # 16 MB


@router.post("/enviar-midia/{telefone}")
def enviar_midia(
    telefone: str,
    file: UploadFile = File(...),
    caption: str = Form(""),
    db: Session = Depends(get_db),
    me: Atendente = Depends(atendente_atual),
):
    """Atendente envia arquivo de mídia para um cliente. Faz upload para Meta e envia via WhatsApp."""
    conteudo = file.file.read()
    if len(conteudo) > _MAX_MIDIA_BYTES:
        raise HTTPException(400, "Arquivo muito grande (máx 16 MB)")
    mime = file.content_type or ""
    # C1: Content-Type genérico/ausente em iPhones e browsers móveis → fallback por extensão.
    if not mime or mime in ("application/octet-stream", "binary/octet-stream"):
        ext = (file.filename or "").rsplit(".", 1)[-1].lower()
        mime = _EXT_PARA_MIME.get(ext, mime)
        if mime not in ("application/octet-stream", "binary/octet-stream", ""):
            log.warning("Content-Type genérico — MIME inferido por extensão '%s': %s", ext, mime)
    media_type = _MIME_PARA_TIPO.get(mime)
    if not media_type:
        raise HTTPException(400, f"Tipo não suportado: {mime or 'desconhecido'}. Use: jpg, png, pdf, mp3, mp4.")

    usuario = db.query(Usuario).filter(Usuario.telefone == telefone).first()
    if not usuario:
        raise HTTPException(404, "Usuário não encontrado")
    if usuario.atendente_id and usuario.atendente_id != me.id:
        raise HTTPException(403, "Conversa pertence a outro atendente")
    auto_assumiu = False
    aguardando_humano_original = usuario.aguardando_humano
    if not usuario.atendente_id:
        usuario.bot_ativo = False
        usuario.aguardando_humano = False
        usuario.atendente_id = me.id
        usuario.status_conversa = "open"
        db.commit()
        auto_assumiu = True
        aviso = f"👋 Olá! Sou {me.nome}, do atendimento da Barbearia Bolshoi. Vou te ajudar a partir de agora."
        ok_aviso, wamid_aviso = whatsapp.enviar_mensagem_texto(telefone, aviso)
        db.add(HistoricoConversa(
            telefone_usuario=telefone,
            mensagem_cliente=None,
            resposta_bot=aviso,
            origem="humano",
            atendente_id=me.id,
            entregue=bool(ok_aviso),
            wamid=wamid_aviso,
        ))
        db.commit()
        notificador.publicar({"tipo": "atendente_assumiu", "telefone": telefone, "atendente_id": me.id, "atendente_nome": me.nome})
        notificador.publicar({"tipo": "status_alterado", "telefone": telefone, "status": "open", "snoozed_until": None, "por_atendente_id": me.id})
        notificador.publicar({"tipo": "nova_mensagem", "telefone": telefone, "nome": usuario.nome_cliente, "texto": aviso, "origem": "humano", "atendente_id": me.id, "entregue": bool(ok_aviso)})

    try:
        media_id = whatsapp.upload_midia_whatsapp(conteudo, mime, file.filename or "arquivo")
        ok, wamid_midia = whatsapp.enviar_mensagem_midia(telefone, media_id, media_type, caption)
    except Exception as e:
        # C2: se auto-assumiu mas o upload/envio falhou, desfaz a atribuição para não
        # deixar a conversa travada com atendente sem mídia entregue.
        if auto_assumiu:
            try:
                db.query(Usuario).filter(Usuario.telefone == telefone).update(
                    {"atendente_id": None, "bot_ativo": True, "aguardando_humano": aguardando_humano_original},
                    synchronize_session=False,
                )
                db.commit()
                notificador.publicar({"tipo": "bot_devolveu", "telefone": telefone, "por_timeout": False})
            except Exception:
                db.rollback()
        # B7: não vazar detalhes internos da exceção para o cliente.
        log.error("enviar_midia falhou para %s: %s", telefone, e)
        raise HTTPException(502, "Falha ao enviar arquivo. Tente novamente.")

    descricao = f"[Mídia: {file.filename or mime}]" + (f" — {caption}" if caption else "")
    db.add(HistoricoConversa(
        telefone_usuario=telefone,
        mensagem_cliente=None,
        resposta_bot=descricao,
        origem="humano",
        atendente_id=me.id,
        entregue=bool(ok),
        wamid=wamid_midia,
    ))
    db.commit()

    notificador.publicar({
        "tipo": "nova_mensagem",
        "telefone": telefone,
        "nome": usuario.nome_cliente,
        "texto": descricao,
        "origem": "humano",
        "atendente_id": me.id,
        # C3: incluir atendente_nome para o frontend exibir o remetente corretamente.
        "atendente_nome": me.nome,
        "entregue": bool(ok),
    })
    return {"ok": True, "media_id": media_id, "entregue": bool(ok)}


@router.post("/devolver/{telefone}")
def devolver(
    telefone: str,
    db: Session = Depends(get_db),
    me: Atendente = Depends(atendente_atual),
    silent: bool = Query(
        False,
        description=(
            "Se True: não envia WhatsApp nem SSE nova_mensagem — "
            "apenas atualiza DB e publica bot_devolveu."
        ),
    ),
):
    """
    Atendente libera a conversa: bot volta a responder.

    GAP-06: ?silent=true omite o aviso WhatsApp e o SSE nova_mensagem.
    DB sempre é atualizado e SSE bot_devolveu sempre é publicado.
    """
    user = db.query(Usuario).filter(Usuario.telefone == telefone).first()
    if not user:
        raise HTTPException(status_code=404, detail="Cliente não encontrado")

    # G9: ao devolver ao bot, garantir que status não fique como "resolved"
    # (atendente pode ter resolvido a conversa e depois devolvido — cliente veria como fechado)
    if user.status_conversa == "resolved":
        user.status_conversa = "open"

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
                "status_conversa": "open",
                "snoozed_until": None,
                "data_ultima_interacao": datetime.now(timezone.utc),
            },
            synchronize_session=False,
        )
    )
    db.commit()
    if afetadas == 0:
        raise HTTPException(status_code=409, detail="Conversa não está sob seu atendimento.")

    if silent:
        # GAP-06: devolução silenciosa — sem WhatsApp, sem SSE nova_mensagem.
        log.info("[SILENT_DEVOLVER] atendente_id=%s telefone=%s", me.id, telefone)
        db.add(HistoricoConversa(
            telefone_usuario=telefone,
            mensagem_cliente=None,
            resposta_bot=None,
            origem="humano",
            intencao="devolucao_silenciosa",
            atendente_id=me.id,
            entregue=None,
        ))
        db.commit()
        notificador.publicar({
            "tipo": "bot_devolveu",
            "telefone": telefone,
        })
        # Garante que o dashboard recoloque a conversa no filtro "open" em tempo real (PO).
        notificador.publicar({
            "tipo": "status_alterado",
            "telefone": telefone,
            "status": "open",
            "snoozed_until": None,
            "por_atendente_id": me.id,
        })
        return {"status": "ok", "silent": True}

    aviso = "Atendimento humano encerrado. O assistente virtual está de volta e pronto para te ajudar."
    ok, wamid = whatsapp.enviar_mensagem_texto(telefone, aviso)
    db.add(HistoricoConversa(
        telefone_usuario=telefone,
        mensagem_cliente=None,
        resposta_bot=aviso,
        origem="humano",
        atendente_id=me.id,
        entregue=bool(ok),
        wamid=wamid,
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
    # Garante que o dashboard recoloque a conversa no filtro "open" em tempo real (PO).
    notificador.publicar({
        "tipo": "status_alterado",
        "telefone": telefone,
        "status": "open",
        "snoozed_until": None,
        "por_atendente_id": me.id,
    })
    return {"status": "ok", "silent": False}


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
    """Define ou remove a tag de uma conversa ('resolvido', 'follow_up' ou None).

    LEGACY: usado pelo cliente antigo. Novo cliente usa /conversa/{telefone}/labels.
    Mantido por compatibilidade durante transição.
    """
    tag = body.tag
    if tag not in ("resolvido", "follow_up", None):
        raise HTTPException(400, "Tag inválida")
    user = db.query(Usuario).filter(Usuario.telefone == telefone).first()
    if not user:
        raise HTTPException(404, "Usuário não encontrado")
    user.tag = tag
    db.commit()
    return {"ok": True, "tag": tag}


# ============================================================
# LABELS — sistema novo de etiquetas múltiplas coloridas
# ============================================================

@router.get("/labels")
def listar_labels(
    incluir_inativas: bool = Query(False),
    db: Session = Depends(get_db),
    _me: Atendente = Depends(atendente_atual),
):
    """Lista todas as labels disponíveis. Default: apenas ativas."""
    q = db.query(Label)
    if not incluir_inativas:
        q = q.filter(Label.ativo == True)
    labels = q.order_by(Label.nome).all()
    return [
        {
            "id": l.id, "nome": l.nome, "cor": l.cor,
            "descricao": l.descricao, "ativo": bool(l.ativo),
            "criado_em": _iso_utc(l.criado_em),
        }
        for l in labels
    ]


@router.post("/labels", status_code=201)
def criar_label(
    payload: LabelIn,
    db: Session = Depends(get_db),
    _me: Atendente = Depends(atendente_atual),
):
    """Cria nova label. Nome deve ser único (case-insensitive já que MySQL é CI por default)."""
    existe = db.query(Label).filter(Label.nome == payload.nome).first()
    if existe:
        raise HTTPException(409, f"Já existe label com nome '{payload.nome}'")
    label = Label(nome=payload.nome, cor=payload.cor, descricao=payload.descricao)
    db.add(label)
    db.commit()
    db.refresh(label)
    return {
        "id": label.id, "nome": label.nome, "cor": label.cor,
        "descricao": label.descricao, "ativo": bool(label.ativo),
    }


@router.patch("/labels/{label_id}")
def editar_label(
    label_id: int,
    payload: LabelPatchIn,
    db: Session = Depends(get_db),
    _me: Atendente = Depends(atendente_atual),
):
    """Edita campos da label. Se mudar nome, valida unicidade."""
    label = db.query(Label).filter(Label.id == label_id).first()
    if not label:
        raise HTTPException(404, "Label não encontrada")
    if payload.nome and payload.nome != label.nome:
        existe = db.query(Label).filter(Label.nome == payload.nome, Label.id != label_id).first()
        if existe:
            raise HTTPException(409, f"Já existe label com nome '{payload.nome}'")
        label.nome = payload.nome
    if payload.cor is not None:
        label.cor = payload.cor
    if payload.descricao is not None:
        label.descricao = payload.descricao
    if payload.ativo is not None:
        label.ativo = payload.ativo
    db.commit()
    return {
        "id": label.id, "nome": label.nome, "cor": label.cor,
        "descricao": label.descricao, "ativo": bool(label.ativo),
    }


@router.delete("/labels/{label_id}", status_code=204)
def deletar_label(
    label_id: int,
    db: Session = Depends(get_db),
    _me: Atendente = Depends(atendente_atual),
):
    """Soft delete: marca ativo=False. Preserva associações em usuario_labels."""
    label = db.query(Label).filter(Label.id == label_id).first()
    if not label:
        raise HTTPException(404, "Label não encontrada")
    label.ativo = False
    db.commit()
    return None


# ============================================================
# Horários de funcionamento (fonte única editável — P0-4)
# ============================================================
_DIAS_SEMANA = ["Segunda", "Terça", "Quarta", "Quinta", "Sexta", "Sábado", "Domingo"]


class HorarioPatchIn(BaseModel):
    abertura: Optional[str] = Field(None, pattern=r"^\d{2}:\d{2}$", description="HH:MM")
    fechamento: Optional[str] = Field(None, pattern=r"^\d{2}:\d{2}$", description="HH:MM")
    fechado: Optional[bool] = None


@router.get("/horarios")
def listar_horarios(
    db: Session = Depends(get_db),
    _me: Atendente = Depends(atendente_atual),
):
    """Lista o horário de funcionamento dos 7 dias (0=segunda ... 6=domingo)."""
    regs = {r.dia_semana: r for r in db.query(Horario).all()}
    return [
        {
            "dia_semana": d,
            "dia_nome": _DIAS_SEMANA[d],
            "abertura": regs[d].abertura if d in regs else None,
            "fechamento": regs[d].fechamento if d in regs else None,
            "fechado": bool(regs[d].fechado) if d in regs else None,
        }
        for d in range(7)
    ]


@router.patch("/horarios/{dia_semana}")
def editar_horario(
    dia_semana: int,
    payload: HorarioPatchIn,
    db: Session = Depends(get_db),
    _me: Atendente = Depends(atendente_atual),
):
    """Edita o horário de um dia (0=segunda ... 6=domingo). Cria o registro se não existir.
    Invalida o cache de horários da IA pra refletir a mudança imediatamente (P0-4)."""
    if dia_semana < 0 or dia_semana > 6:
        raise HTTPException(400, "dia_semana deve estar entre 0 (segunda) e 6 (domingo)")
    h = db.query(Horario).filter(Horario.dia_semana == dia_semana).first()
    if not h:
        h = Horario(dia_semana=dia_semana, fechado=False)
        db.add(h)
    if payload.abertura is not None:
        h.abertura = payload.abertura
    if payload.fechamento is not None:
        h.fechamento = payload.fechamento
    if payload.fechado is not None:
        h.fechado = payload.fechado
    db.commit()
    # Reflete na IA na hora (a canônica já lê fresco; aqui invalidamos o cache do contexto temporal).
    try:
        from services.ai_service import invalidar_cache_horarios
        invalidar_cache_horarios()
    except Exception:
        pass
    notificador.publicar({"tipo": "horarios_atualizados", "dia_semana": dia_semana})
    return {
        "dia_semana": h.dia_semana, "dia_nome": _DIAS_SEMANA[dia_semana],
        "abertura": h.abertura, "fechamento": h.fechamento, "fechado": bool(h.fechado),
    }


# ============================================================
# LGPD: exclusão de dados de um cliente (P0-1)
# ============================================================
@router.delete("/cliente/{telefone}", status_code=204)
def apagar_cliente(
    telefone: str,
    db: Session = Depends(get_db),
    me: Atendente = Depends(atendente_atual),
):
    """LGPD: apaga o cliente e TODOS os seus dados pessoais (histórico, labels, notas,
    menções). Deleção explícita das dependências — robusta mesmo sem FK cascade no SQLite.
    Ação de staff; registra quem apagou."""
    user = db.query(Usuario).filter(Usuario.telefone == telefone).first()
    if not user:
        raise HTTPException(404, "Cliente não encontrado")
    db.query(MentionNotificacao).filter(MentionNotificacao.telefone_usuario == telefone).delete(synchronize_session=False)
    db.query(NotaInterna).filter(NotaInterna.telefone_usuario == telefone).delete(synchronize_session=False)
    db.execute(usuario_labels.delete().where(usuario_labels.c.telefone_usuario == telefone))
    db.query(HistoricoConversa).filter(HistoricoConversa.telefone_usuario == telefone).delete(synchronize_session=False)
    db.delete(user)
    db.commit()
    log.info("[LGPD] Cliente apagado por atendente_id=%s telefone=%s", me.id, telefone)
    notificador.publicar({"tipo": "cliente_apagado", "telefone": telefone})
    return None


@router.post("/conversa/{telefone}/labels", status_code=201)
def atribuir_label(
    telefone: str,
    payload: AssignLabelIn,
    db: Session = Depends(get_db),
    me: Atendente = Depends(atendente_atual),
):
    """Atribui uma label a uma conversa. Idempotente (já atribuído = no-op)."""
    from sqlalchemy.exc import IntegrityError
    user = db.query(Usuario).filter(Usuario.telefone == telefone).first()
    if not user:
        raise HTTPException(404, "Usuário não encontrado")
    label = db.query(Label).filter(Label.id == payload.label_id, Label.ativo == True).first()
    if not label:
        raise HTTPException(404, "Label não encontrada ou inativa")

    # Tenta INSERT direto; se PK composta colide (requisições simultâneas
    # passando ambas pelo guard SELECT), tratamos como idempotente.
    try:
        db.execute(usuario_labels.insert().values(
            telefone_usuario=telefone,
            label_id=payload.label_id,
            atribuido_em=datetime.now(timezone.utc),
            atribuido_por=me.id,
        ))
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        # Loga se não for duplicidade de PK (ex.: FK violation por dado corrompido)
        # — tratamos como "ja_atribuida" mas avisamos para investigação.
        if "Duplicate entry" not in str(getattr(exc, "orig", exc)):
            log.warning("atribuir_label IntegrityError inesperado tel=%s label_id=%s: %s",
                        telefone, payload.label_id, getattr(exc, "orig", exc))
        return {"ok": True, "ja_atribuida": True}
    return {"ok": True, "label": {"id": label.id, "nome": label.nome, "cor": label.cor}}


@router.delete("/conversa/{telefone}/labels/{label_id}", status_code=204)
def remover_label(
    telefone: str,
    label_id: int,
    db: Session = Depends(get_db),
    _me: Atendente = Depends(atendente_atual),
):
    """Remove a associação entre conversa e label."""
    result = db.execute(
        usuario_labels.delete().where(
            usuario_labels.c.telefone_usuario == telefone,
            usuario_labels.c.label_id == label_id,
        )
    )
    db.commit()
    if result.rowcount == 0:
        raise HTTPException(404, "Associação não encontrada")
    return None


# ============================================================
# STATUS DE CONVERSA — máquina de estados (open/pending/resolved/snoozed)
# ============================================================

@router.patch("/conversa/{telefone}/status")
def alterar_status_conversa(
    telefone: str,
    payload: StatusConversaIn,
    db: Session = Depends(get_db),
    me: Atendente = Depends(atendente_atual),
):
    """Altera status_conversa. Se snoozed, exige snoozed_until válido futuro."""
    user = db.query(Usuario).filter(Usuario.telefone == telefone).first()
    if not user:
        raise HTTPException(404, "Conversa não encontrada")

    novo = payload.status
    snoozed_until_dt = None

    if novo == "snoozed":
        if not payload.snoozed_until:
            raise HTTPException(400, "snoozed_until obrigatório para status=snoozed")
        try:
            snoozed_until_dt = datetime.fromisoformat(payload.snoozed_until.replace("Z", "+00:00"))
            if snoozed_until_dt.tzinfo is None:
                snoozed_until_dt = snoozed_until_dt.replace(tzinfo=timezone.utc)
        except ValueError:
            raise HTTPException(400, "snoozed_until com formato inválido (use ISO 8601)")
        if snoozed_until_dt <= datetime.now(timezone.utc):
            raise HTTPException(400, "snoozed_until deve ser futuro")

    status_anterior = user.status_conversa
    user.status_conversa = novo
    user.snoozed_until = snoozed_until_dt if novo == "snoozed" else None

    # Resolved → Resolved: no-op nos marcadores (preserva timestamp e autor originais).
    # Evita sobrescrever histórico de quem resolveu primeiro.
    if novo == "resolved" and status_anterior != "resolved":
        user.resolved_em = datetime.now(timezone.utc)
        user.resolved_por = me.id
    elif novo != "resolved" and status_anterior == "resolved":
        # Re-abrindo conversa resolvida: limpa marcadores de resolução.
        # Em transições não-resolved → não-resolved, preserva resolved_em/por
        # (histórico de quem resolveu antes — útil para analytics).
        user.resolved_em = None
        user.resolved_por = None

    db.commit()

    notificador.publicar({
        "tipo": "status_alterado",
        "telefone": telefone,
        "status": novo,
        "snoozed_until": _iso_utc(snoozed_until_dt) if snoozed_until_dt else None,
        "por_atendente_id": me.id,
    })

    return {
        "ok": True,
        "status": novo,
        "snoozed_until": _iso_utc(snoozed_until_dt) if snoozed_until_dt else None,
    }


# ============================================================
# CANNED RESPONSES — respostas rápidas com placeholders
# ============================================================

def _substituir_placeholders(texto: str, usuario: Usuario, atendente: Atendente) -> str:
    """
    Substitui placeholders {chave} no texto da resposta canned com dados reais.
    Suportados: {nome_cliente}, {primeiro_nome}, {atendente}, {barbearia}.
    Placeholders desconhecidos são mantidos como literais (para o atendente revisar).
    """
    if not texto or "{" not in texto:
        return texto
    nome_cliente = (usuario.nome_cliente or "").strip()
    primeiro_nome = nome_cliente.split(" ")[0] if nome_cliente else "cliente"
    return (
        texto
        .replace("{nome_cliente}", nome_cliente or "cliente")
        .replace("{primeiro_nome}", primeiro_nome)
        .replace("{atendente}", atendente.nome)
        .replace("{barbearia}", "Barbearia Bolshoi")
    )


@router.get("/canned")
def listar_canned(
    db: Session = Depends(get_db),
    me: Atendente = Depends(atendente_atual),
):
    """Lista canned responses globais + pessoais do atendente logado."""
    from sqlalchemy import or_
    canned = (
        db.query(CannedResponse)
        .filter(or_(CannedResponse.atendente_id.is_(None), CannedResponse.atendente_id == me.id))
        .order_by(CannedResponse.atalho)
        .all()
    )
    return [
        {
            "id": c.id,
            "atalho": c.atalho,
            "texto": c.texto,
            "atendente_id": c.atendente_id,
            "criado_em": _iso_utc(c.criado_em),
            "atualizado_em": _iso_utc(c.atualizado_em),
        }
        for c in canned
    ]


@router.post("/canned", status_code=201)
def criar_canned(
    payload: CannedIn,
    db: Session = Depends(get_db),
    me: Atendente = Depends(atendente_atual),
):
    """Cria nova canned response. Escopo 'global' = atendente_id=NULL, 'pessoal' = me.id."""
    aid = None if payload.escopo == "global" else me.id

    # Verifica unicidade do atalho dentro do escopo
    existe = db.query(CannedResponse).filter(
        CannedResponse.atalho == payload.atalho,
        CannedResponse.atendente_id.is_(None) if aid is None else CannedResponse.atendente_id == aid,
    ).first()
    if existe:
        raise HTTPException(409, f"Atalho '{payload.atalho}' já existe nesse escopo")

    c = CannedResponse(atalho=payload.atalho, texto=payload.texto, atendente_id=aid)
    db.add(c)
    db.commit()
    db.refresh(c)
    return {
        "id": c.id, "atalho": c.atalho, "texto": c.texto,
        "atendente_id": c.atendente_id,
    }


@router.patch("/canned/{canned_id}")
def editar_canned(
    canned_id: int,
    payload: CannedPatchIn,
    db: Session = Depends(get_db),
    me: Atendente = Depends(atendente_atual),
):
    """Edita canned. Globais editáveis por qualquer atendente; pessoais só pelo dono."""
    c = db.query(CannedResponse).filter(CannedResponse.id == canned_id).first()
    if not c:
        raise HTTPException(404, "Canned response não encontrada")
    if c.atendente_id is not None and c.atendente_id != me.id:
        raise HTTPException(403, "Você não pode editar canned response de outro atendente")

    if payload.atalho and payload.atalho != c.atalho:
        # Valida unicidade no novo atalho
        existe = db.query(CannedResponse).filter(
            CannedResponse.atalho == payload.atalho,
            CannedResponse.id != canned_id,
            CannedResponse.atendente_id.is_(None) if c.atendente_id is None else CannedResponse.atendente_id == c.atendente_id,
        ).first()
        if existe:
            raise HTTPException(409, f"Atalho '{payload.atalho}' já existe")
        c.atalho = payload.atalho
    if payload.texto is not None:
        c.texto = payload.texto
    if payload.escopo is not None:
        novo_aid = None if payload.escopo == "global" else me.id
        c.atendente_id = novo_aid
    c.atualizado_em = datetime.now(timezone.utc)
    db.commit()
    return {
        "id": c.id, "atalho": c.atalho, "texto": c.texto,
        "atendente_id": c.atendente_id,
    }


@router.delete("/canned/{canned_id}", status_code=204)
def deletar_canned(
    canned_id: int,
    db: Session = Depends(get_db),
    me: Atendente = Depends(atendente_atual),
):
    """Deleta canned. Globais deletáveis por qualquer atendente; pessoais só pelo dono."""
    c = db.query(CannedResponse).filter(CannedResponse.id == canned_id).first()
    if not c:
        raise HTTPException(404, "Canned response não encontrada")
    if c.atendente_id is not None and c.atendente_id != me.id:
        raise HTTPException(403, "Você não pode deletar canned response de outro atendente")
    db.delete(c)
    db.commit()
    return None


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
    # US-AD-010: busca telefones afetados antes do UPDATE para publicar SSE depois.
    telefones_afetados = [
        row.telefone
        for row in db.query(Usuario.telefone).filter(
            Usuario.atendente_id == atendente_id,
            Usuario.bot_ativo == False,
        ).all()
    ]
    db.query(Usuario).filter(
        Usuario.atendente_id == atendente_id,
        Usuario.bot_ativo == False,
    ).update(
        {
            "atendente_id": None,
            "bot_ativo": True,
            "aguardando_humano": False,
            "status_conversa": "open",
            "snoozed_until": None,
            "data_ultima_interacao": datetime.now(timezone.utc),
        },
        synchronize_session=False,
    )
    db.commit()
    # US-AD-010: notifica dashboard para cada conversa liberada.
    for tel in telefones_afetados:
        notificador.publicar({"tipo": "bot_devolveu", "telefone": tel})
        notificador.publicar({
            "tipo": "status_alterado",
            "telefone": tel,
            "status": "open",
            "snoozed_until": None,
            "por_atendente_id": None,
        })
    return {"ok": True}


@router.patch("/atendentes/{atendente_id}/ativar")
async def ativar_atendente(
    atendente_id: int,
    db: Session = Depends(get_db),
    _: Atendente = Depends(atendente_atual),
):
    """
    GAP-01 / SP-2: Ativa um atendente previamente desativado.

    Idempotente: se já estiver ativo, retorna {"ok": true, "ja_ativo": true} com 200.
    Publica SSE presence_changed ao ativar para atualização imediata no dashboard.
    """
    a = db.query(Atendente).filter(Atendente.id == atendente_id).first()
    if not a:
        raise HTTPException(status_code=404, detail="Atendente não encontrado")

    if a.ativo:
        return {"ok": True, "id": a.id, "nome": a.nome, "ja_ativo": True}

    a.ativo = True
    db.commit()

    notificador.publicar({
        "tipo": "presence_changed",
        "atendente_id": a.id,
        "atendente_nome": a.nome,
        "status": "online",  # "reativado" era inválido segundo ADR-005 — TD-016 corrigido
    })

    log.info("[ATIVAR] atendente_id=%s nome=%s ativado", a.id, a.nome)
    return {"ok": True, "id": a.id, "nome": a.nome, "ativo": True}


# ---------------------------------------------------------------------------
# TASK-015: Notas internas por cliente
# ---------------------------------------------------------------------------

@router.get("/notas/{telefone}")
async def listar_notas(
    telefone: str,
    db: Session = Depends(get_db),
    _: Atendente = Depends(atendente_atual),
    page: int = Query(1, ge=1, description="Página (começa em 1)"),
    per_page: int = Query(20, ge=1, le=100, description="Resultados por página (máx 100)"),
):
    """
    Lista as notas internas de um cliente em ordem decrescente de criação.

    GAP-04: Paginação com envelope — retorna {items, page, per_page, total, has_more}.
    Telefone sem notas retorna items=[], total=0 (não 404).
    """
    base_q = (
        db.query(NotaInterna)
        .filter(NotaInterna.telefone_usuario == telefone)
        .order_by(NotaInterna.criado_em.desc())
    )
    total = base_q.count()
    offset = (page - 1) * per_page
    notas = base_q.offset(offset).limit(per_page).all()

    items = [
        {
            "id": n.id,
            "texto": n.texto,
            "atendente_id": n.atendente_id,
            "criado_em": _iso_utc(n.criado_em),
            "editado_em": _iso_utc(n.editado_em),
            "editado_por": n.editado_por,
        }
        for n in notas
    ]

    return {
        "items": items,
        "page": page,
        "per_page": per_page,
        "total": total,
        "has_more": (offset + len(items)) < total,
    }


_REGEX_MENTION = re.compile(r'@([a-z0-9_]{3,50})')


def _processar_mentions(db: Session, nota: NotaInterna, autor: Atendente) -> list[int]:
    """
    Extrai @user_login do texto da nota e cria MentionNotificacao para cada
    atendente ATIVO encontrado (ignora self-mentions e logins inexistentes).
    Retorna lista de atendente_ids notificados.
    """
    logins = set(_REGEX_MENTION.findall(nota.texto.lower()))
    if not logins:
        return []
    # Busca atendentes válidos em batch
    atendentes = (
        db.query(Atendente)
        .filter(
            Atendente.usuario_login.in_(logins),
            Atendente.ativo == True,
            Atendente.id != autor.id,  # ignora self-mention
        )
        .all()
    )
    if not atendentes:
        return []
    notificados = []
    for a in atendentes:
        m = MentionNotificacao(
            atendente_id=a.id,
            nota_id=nota.id,
            telefone_usuario=nota.telefone_usuario,
            mencionado_por=autor.id,
        )
        db.add(m)
        notificados.append(a.id)
    # BE-06: flush sem commit — o caller (criar_nota) faz o commit único que
    # persiste nota + mentions atomicamente.
    db.flush()
    # Dispatch SSE para cada mencionado
    for aid in notificados:
        notificador.publicar({
            "tipo": "nova_mention",
            "atendente_id": aid,
            "telefone": nota.telefone_usuario,
            "mencionado_por": autor.id,
            "mencionado_por_nome": autor.nome,
            "nota_id": nota.id,
            "preview": nota.texto[:120],
        })
    return notificados


@router.post("/notas/{telefone}", status_code=201)
async def criar_nota(telefone: str, body: NotaIn, db: Session = Depends(get_db), atual: Atendente = Depends(atendente_atual)):
    """Registra uma nova nota interna. Processa @mentions e dispara notificações."""
    nota = NotaInterna(telefone_usuario=telefone, atendente_id=atual.id, texto=body.texto.strip())
    db.add(nota)
    # BE-06: flush para obter nota.id sem commitar — se _processar_mentions falhar,
    # o rollback desfaz tanto a nota quanto as mentions (transação única).
    db.flush()

    # Processa @mentions e gera notificações
    mentions = _processar_mentions(db, nota, atual)

    # Commit único: nota + mentions persistem juntos ou nenhum persiste.
    db.commit()
    db.refresh(nota)

    return {"ok": True, "id": nota.id, "mencionados": mentions}


# ============================================================
# MENTIONS INBOX
# ============================================================

@router.get("/mentions/inbox")
def listar_mentions(
    apenas_nao_lidas: bool = Query(True),
    db: Session = Depends(get_db),
    me: Atendente = Depends(atendente_atual),
):
    """Lista notificações de @mention para o atendente logado."""
    q = (
        db.query(MentionNotificacao, NotaInterna, Atendente, Usuario)
        .join(NotaInterna, NotaInterna.id == MentionNotificacao.nota_id)
        .outerjoin(Atendente, Atendente.id == MentionNotificacao.mencionado_por)
        .outerjoin(Usuario, Usuario.telefone == MentionNotificacao.telefone_usuario)
        .filter(MentionNotificacao.atendente_id == me.id)
    )
    if apenas_nao_lidas:
        q = q.filter(MentionNotificacao.lida == False)
    q = q.order_by(MentionNotificacao.criado_em.desc()).limit(100)

    return [
        {
            "id": mn.id,
            "lida": bool(mn.lida),
            "criado_em": _iso_utc(mn.criado_em),
            "lida_em": _iso_utc(mn.lida_em),
            "telefone": mn.telefone_usuario,
            "nome_cliente": (u.nome_cliente if u else None) or mn.telefone_usuario,
            "mencionado_por_nome": a.nome if a else "—",
            "nota_texto": nota.texto,
            "nota_id": nota.id,
        }
        for mn, nota, a, u in q.all()
    ]


@router.patch("/mentions/{mention_id}/marcar-lida")
def marcar_mention_lida(
    mention_id: int,
    db: Session = Depends(get_db),
    me: Atendente = Depends(atendente_atual),
):
    """Marca uma mention como lida. Só o dono pode marcar."""
    mn = db.query(MentionNotificacao).filter(MentionNotificacao.id == mention_id).first()
    if not mn:
        raise HTTPException(404, "Notificação não encontrada")
    if mn.atendente_id != me.id:
        raise HTTPException(403, "Notificação não pertence a você")
    if mn.lida:
        return {"ok": True, "ja_lida": True}
    mn.lida = True
    mn.lida_em = datetime.now(timezone.utc)
    db.commit()
    return {"ok": True}


# ---------------------------------------------------------------------------
# GAP-05: Edição e remoção de notas internas
# ---------------------------------------------------------------------------

class NotaEditIn(BaseModel):
    texto: str = Field(..., min_length=1, max_length=4096)

    @field_validator("texto")
    @classmethod
    def texto_strip_nao_vazio(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("Texto não pode conter apenas espaços")
        return v


@router.patch("/notas/{nota_id}")
async def editar_nota(
    nota_id: int,
    body: NotaEditIn,
    db: Session = Depends(get_db),
    me: Atendente = Depends(atendente_atual),
):
    """
    GAP-05: Edita o texto de uma nota interna.

    Ownership: apenas o criador pode editar.
    Exceção: se atendente_id IS NULL (criador desativado/deletado), somente
             o DELETE é permitido — nenhum atendente pode editar nota órfã.
    Atualiza editado_em e editado_por; preserva criado_em e atendente_id original.
    """
    nota = db.query(NotaInterna).filter(NotaInterna.id == nota_id).first()
    if not nota:
        raise HTTPException(status_code=404, detail="Nota não encontrada")

    # Nota órfã (criador deletado): ninguém pode editar
    if nota.atendente_id is None:
        raise HTTPException(
            status_code=403,
            detail="Nota órfã (criador removido): edição não permitida. Use DELETE se necessário.",
        )

    if nota.atendente_id != me.id:
        raise HTTPException(status_code=403, detail="Você não é o criador desta nota")

    # Busca telefone para logging auditável
    usuario = db.query(Usuario).filter(Usuario.telefone == nota.telefone_usuario).first()
    telefone_log = usuario.telefone if usuario else nota.telefone_usuario

    nota.texto = body.texto
    nota.editado_em = datetime.now(timezone.utc)
    nota.editado_por = me.id
    db.commit()

    log.info("[NOTAS] atendente_id=%s editou nota_id=%s telefone=%s", me.id, nota.id, telefone_log)

    return {
        "id": nota.id,
        "texto": nota.texto,
        "atendente_id": nota.atendente_id,
        "criado_em": _iso_utc(nota.criado_em),
        "editado_em": _iso_utc(nota.editado_em),
        "editado_por": nota.editado_por,
    }


@router.delete("/notas/{nota_id}", status_code=204)
async def deletar_nota(
    nota_id: int,
    db: Session = Depends(get_db),
    me: Atendente = Depends(atendente_atual),
):
    """
    GAP-05: Remove uma nota interna.

    Ownership: apenas o criador pode deletar.
    Exceção: se atendente_id IS NULL (criador deletado/desativado), qualquer
             atendente autenticado pode deletar.
    Response 204 (sem corpo).
    """
    nota = db.query(NotaInterna).filter(NotaInterna.id == nota_id).first()
    if not nota:
        raise HTTPException(status_code=404, detail="Nota não encontrada")

    # Nota órfã: qualquer atendente pode deletar
    if nota.atendente_id is not None and nota.atendente_id != me.id:
        raise HTTPException(status_code=403, detail="Você não é o criador desta nota")

    telefone_log = nota.telefone_usuario
    db.delete(nota)
    db.commit()

    log.info("[NOTAS] atendente_id=%s deletou nota_id=%s telefone=%s", me.id, nota_id, telefone_log)
