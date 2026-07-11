"""
Autenticação para o dashboard admin (modo híbrido).

Esquema simples: login (usuario_login + senha) → JWT assinado com JWT_SECRET, TTL curto.
JWT vai no header `Authorization: Bearer <token>` em todas as rotas /admin/*.

Senha:  bcrypt via passlib.
Token:  HS256 via python-jose.
"""
import os
import time
import logging
import bcrypt
from datetime import datetime, timedelta, timezone
from fastapi import Depends, HTTPException, status, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from jose import JWTError, jwt

from db.database import get_db
from db.models import Atendente
from core import config

log = logging.getLogger("barbearia.auth")

JWT_SECRET = config.JWT_SECRET
JWT_ALG = "HS256"
JWT_TTL_MIN = config.JWT_TTL_MIN

if not JWT_SECRET:
    log.warning("JWT_SECRET não configurado — autenticação admin desabilitada (modo dev).")

bearer_scheme = HTTPBearer(auto_error=False)

# Rate limit por IP nos endpoints sensíveis (login).
_LOGIN_LIMITE = 5  # tentativas por janela
_LOGIN_JANELA = 60  # segundos
_login_tentativas: dict[str, list[float]] = {}

# Bcrypt limita a 72 bytes. Senhas maiores são truncadas no input — comportamento
# documentado e idêntico ao usado pela maioria dos sistemas web.
_BCRYPT_MAX_BYTES = 72


def _normalizar_senha(senha_plana: str) -> bytes:
    return senha_plana.encode("utf-8")[:_BCRYPT_MAX_BYTES]


def hash_senha(senha_plana: str) -> str:
    return bcrypt.hashpw(_normalizar_senha(senha_plana), bcrypt.gensalt()).decode("utf-8")


def verificar_senha(senha_plana: str, senha_hash: str) -> bool:
    try:
        return bcrypt.checkpw(_normalizar_senha(senha_plana), senha_hash.encode("utf-8"))
    except Exception:
        return False


def criar_token(atendente: Atendente) -> str:
    if not JWT_SECRET:
        raise RuntimeError("JWT_SECRET não configurado.")
    payload = {
        "sub": str(atendente.id),
        "login": atendente.usuario_login,
        "nome": atendente.nome,
        "exp": datetime.now(timezone.utc) + timedelta(minutes=JWT_TTL_MIN),
        "iat": datetime.now(timezone.utc),
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALG)


def _decodificar(token: str) -> dict:
    try:
        return jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALG])
    except JWTError as e:
        log.warning("JWT inválido: %s", e)
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token inválido ou expirado")


def login_rate_limited(ip: str) -> bool:
    """True se o IP excedeu o limite de tentativas de login na janela atual."""
    agora = time.time()
    janela = _login_tentativas.setdefault(ip, [])
    janela[:] = [t for t in janela if agora - t < _LOGIN_JANELA]
    if len(janela) >= _LOGIN_LIMITE:
        return True
    janela.append(agora)
    return False


def atendente_atual(
    request: Request,
    creds: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    db: Session = Depends(get_db),
) -> Atendente:
    """
    Dependency: extrai JWT do header Authorization, valida e devolve o Atendente.
    Falha 401 se token ausente, inválido, expirado ou se atendente foi desativado.
    """
    if not JWT_SECRET:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="JWT_SECRET não configurado no servidor.")
    if not creds or creds.scheme.lower() != "bearer":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token Bearer ausente")
    payload = _decodificar(creds.credentials)
    atendente_id = payload.get("sub")
    if not atendente_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token sem sub")
    atendente = db.query(Atendente).filter(Atendente.id == int(atendente_id)).first()
    if not atendente or not atendente.ativo:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Atendente inválido ou desativado")
    return atendente
