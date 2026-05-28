import os
import time

# TD-001: forçar TZ=UTC antes de qualquer import que use datetime.
# Garante que naive datetimes do sistema operacional sejam UTC.
# tzset() não existe no Windows — condicional para dev local.
os.environ.setdefault("TZ", "UTC")
if hasattr(time, "tzset"):
    time.tzset()

import logging
from pathlib import Path
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from api import webhook
from db.database import engine, Base
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

def _exigir_meta_secret(meta_secret: str, allow_unsigned: str) -> None:
    """Aborta o boot se META_APP_SECRET ausente em producao."""
    if not meta_secret:
        if allow_unsigned != "1":
            raise RuntimeError(
                "META_APP_SECRET nao configurado. "
                "Em producao, defina META_APP_SECRET no .env para validar assinaturas HMAC do webhook. "
                "Para desenvolvimento local sem validacao de assinatura, defina ALLOW_UNSIGNED_WEBHOOK=1."
            )
        _log.warning(
            "META_APP_SECRET ausente — ALLOW_UNSIGNED_WEBHOOK=1 ativo. "
            "Webhook aceita POST sem validacao de assinatura HMAC. NAO use em producao."
        )

_exigir_meta_secret(
    os.getenv("META_APP_SECRET", ""),
    os.getenv("ALLOW_UNSIGNED_WEBHOOK", ""),
)

# SQLAlchemy cria tabelas que ainda não existem no MySQL (porta 3306).
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="Barbearia Bot API",
    description="Motor de conversação de Whatsapp usando NVIDIA NIM (Llama 3.1 70B) e FastAPI"
)

# Inclui as rotas do webhook no caminho raiz
app.include_router(webhook.router)

# Modo híbrido: registra endpoints e dashboard de atendente humano.
# Modo bot_only: nada do /admin é exposto (segurança + simplicidade).
if MODO_HIBRIDO:
    # Falha cedo se segredo do JWT estiver ausente — sem isso, dashboard inseguro.
    if not os.getenv("JWT_SECRET"):
        raise RuntimeError(
            "MODO_OPERACAO=hibrido requer JWT_SECRET no .env. "
            "Gere com: python -c \"import secrets; print(secrets.token_hex(32))\""
        )
    from api import admin
    app.include_router(admin.router)
    static_dir = Path(__file__).parent / "static"
    if static_dir.exists():
        app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

@app.get("/")
def read_root():
    return {"status": "Online", "mensagem": "API do Bot da Barbearia rodando perfeitamente!"}

if __name__ == "__main__":
    import uvicorn
    # Inicializa o servidor Uvicorn se for rodado diretamente (python main.py)
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=False)
