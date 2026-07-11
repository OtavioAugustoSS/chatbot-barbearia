import os
import time

# TD-001: forçar TZ=UTC antes de qualquer import que use datetime.
# Garante que naive datetimes do sistema operacional sejam UTC.
# tzset() não existe no Windows — condicional para dev local.
os.environ.setdefault("TZ", "UTC")
if hasattr(time, "tzset"):
    time.tzset()

import logging
from datetime import datetime, timezone
from pathlib import Path
from fastapi import FastAPI, Depends, HTTPException
from fastapi.staticfiles import StaticFiles
from sqlalchemy import text
from sqlalchemy.orm import Session
from api import webhook
from db.database import engine, Base, get_db
from core import config
from core.config import MODO_HIBRIDO, MODO_OPERACAO

# Logging estruturado: substitui prints espalhados.
# LOG_LEVEL configurável via env (default INFO; DEBUG mostra payload IA).
logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO").upper(),
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)

_log = logging.getLogger("barbearia")
_log.info("Modo de operação: %s", MODO_OPERACAO)

# Observabilidade opcional (P1-1): ativa Sentry SOMENTE se SENTRY_DSN estiver definido.
# Sem DSN (modo de testes/dev) é no-op. Requer `pip install sentry-sdk` se for usar.
_sentry_dsn = os.getenv("SENTRY_DSN")
if _sentry_dsn:
    try:
        import sentry_sdk
        sentry_sdk.init(dsn=_sentry_dsn, traces_sample_rate=0.0, environment=os.getenv("APP_ENV", "production"))
        _log.info("Sentry ativado para captura de erros.")
    except ImportError:
        _log.warning("SENTRY_DSN definido mas 'sentry-sdk' não instalado — rode: pip install sentry-sdk")


def _exigir_meta_secret(meta_secret: str, allow_unsigned: bool | str) -> None:
    """Aborta o boot se META_APP_SECRET ausente sem opt-in de webhook não assinado.

    Em MODO_DEV o opt-in é automático (config.ALLOW_UNSIGNED_WEBHOOK=True);
    fora dele continua exigindo ALLOW_UNSIGNED_WEBHOOK=1 explícito.
    allow_unsigned aceita bool (config) ou a string crua da env var ("1" = ativo).
    """
    if isinstance(allow_unsigned, str):
        allow_unsigned = allow_unsigned == "1"
    if not meta_secret:
        if not allow_unsigned:
            raise RuntimeError(
                "META_APP_SECRET nao configurado. "
                "Em producao, defina META_APP_SECRET no .env para validar assinaturas HMAC do webhook. "
                "Para desenvolvimento local sem validacao de assinatura, defina ALLOW_UNSIGNED_WEBHOOK=1."
            )
        _log.warning(
            "META_APP_SECRET ausente — webhook aceita POST sem validacao de assinatura HMAC. "
            "NAO use em producao."
        )

_exigir_meta_secret(config.META_APP_SECRET, config.ALLOW_UNSIGNED_WEBHOOK)

# create_all (ADR-014) — MANTIDO sem condição. Papéis por contexto:
#   - Testes (conftest troca o engine por SQLite antes do import): cria o schema de teste.
#   - MySQL do zero (bootstrap): cria as tabelas a partir dos models; em seguida
#     rode `alembic stamp head` para registrar a baseline (ver runbook).
#   - MySQL já provisionado: inócuo — create_all só cria tabelas ausentes, nunca altera.
# Mudanças de schema NÃO acontecem aqui: são migrations Alembic (`alembic upgrade head`).
Base.metadata.create_all(bind=engine)

# Modo dev (sem credenciais reais): popula dados demo e loga banner com o estado
# de cada subsistema. Nunca roda com APP_ENV=production (guard duro no seed).
if config.MODO_DEV:
    from scripts.seed_dev import seed_demo

    seed_demo()
    _linhas_dev = [
        "",
        "=" * 74,
        "MODO DESENVOLVIMENTO — rodando sem credenciais reais (.env ausente/incompleto)",
        "-" * 74,
    ]
    if config.DB_SQLITE_DEV:
        _linhas_dev.append("DB:        SQLite ./dev.db            -> producao: DB_USER/DB_PASS/DB_HOST/DB_NAME")
    if config.IA_FAKE:
        _linhas_dev.append("IA:        FAKE (resposta demo)       -> producao: NVIDIA_API_KEY")
    if config.WHATSAPP_FAKE:
        _linhas_dev.append("WhatsApp:  FAKE (outbox do simulador) -> producao: WHATSAPP_TOKEN + WHATSAPP_PHONE_ID")
    if not config.META_APP_SECRET:
        _linhas_dev.append("Webhook:   sem validacao HMAC          -> producao: META_APP_SECRET")
    if config.JWT_SECRET_EFEMERO:
        _linhas_dev.append("JWT:       secret efemero (reset a cada boot) -> producao: JWT_SECRET")
    _linhas_dev.append(f"Modo:      {MODO_OPERACAO}" + (" (default de dev)" if not os.getenv("MODO_OPERACAO") else ""))
    if MODO_HIBRIDO:
        _linhas_dev.append("Dashboard: http://localhost:8000/static/admin/login.html  (admin / admin123)")
    if config.WHATSAPP_FAKE:
        _linhas_dev.append("Simulador: http://localhost:8000/dev/simulador")
    _linhas_dev.append("=" * 74)
    _log.warning("\n".join(_linhas_dev))

app = FastAPI(
    title="Barbearia Bot API",
    description="Motor de conversação de Whatsapp usando NVIDIA NIM (Llama 3.1 70B) e FastAPI"
)


@app.on_event("startup")
async def _capturar_event_loop():
    """H3: o notificador SSE precisa do event loop para receber publicações
    vindas de threads sync (background tasks) via call_soon_threadsafe."""
    import asyncio

    from services.notificador import notificador

    notificador.set_loop(asyncio.get_running_loop())

# Inclui as rotas do webhook no caminho raiz
app.include_router(webhook.router)

# Modo híbrido: registra endpoints e dashboard de atendente humano.
# Modo bot_only: nada do /admin é exposto (segurança + simplicidade).
if MODO_HIBRIDO:
    # Falha cedo se segredo do JWT estiver ausente — sem isso, dashboard inseguro.
    # Em MODO_DEV, config.JWT_SECRET já foi preenchido com secret efêmero.
    if not config.JWT_SECRET:
        raise RuntimeError(
            "MODO_OPERACAO=hibrido requer JWT_SECRET no .env. "
            "Gere com: python -c \"import secrets; print(secrets.token_hex(32))\""
        )
    from api import admin
    app.include_router(admin.router)
    static_dir = Path(__file__).parent / "static"
    if static_dir.exists():
        app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

# Simulador de chat local: montado APENAS quando o WhatsApp é fake (sem credenciais
# Meta) e fora de producao — com token real o pipeline enviaria mensagens de verdade,
# entao o simulador nunca pode coexistir com ele.
if config.WHATSAPP_FAKE and config.APP_ENV != "production":
    from api import dev_router

    app.include_router(dev_router.router)

@app.get("/health")
def health_check(db: Session = Depends(get_db)):
    """Health-check para orquestração/monitoramento (systemd/Docker/load balancer).
    Testa a conexão real com o banco: 200 = saudável, 503 = banco indisponível."""
    try:
        db.execute(text("SELECT 1"))
    except Exception as e:
        _log.error("Health check falhou (banco indisponível): %s", e)
        raise HTTPException(status_code=503, detail="database unavailable")
    return {
        "status": "healthy",
        "modo": MODO_OPERACAO,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


@app.get("/")
def read_root():
    return {"status": "Online", "mensagem": "API do Bot da Barbearia rodando perfeitamente!"}

if __name__ == "__main__":
    import uvicorn
    # Inicializa o servidor Uvicorn se for rodado diretamente (python main.py)
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=False)
