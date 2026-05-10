import logging
import os
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

logging.getLogger("barbearia").info("Modo de operação: %s", MODO_OPERACAO)

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
